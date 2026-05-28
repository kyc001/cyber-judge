"""Cyber Judge (赛博判官) API Server.

Endpoints:
  POST /api/upload          — Upload WeFlow JSON, start analysis
  GET  /api/report/:id      — Get generated report (polls with 202 while processing)
  GET  /api/report/:id/progress — SSE stream of LLM sub-call progress
  POST /api/share/:id       — Create a share link
  GET  /api/share/:slug     — Load a shared report
  POST /api/export          — Export report as json/csv/txt/html
  GET  /api/health          — Health check

Architecture: Upload -> Parser -> Stats -> LLM (multi-call) -> Merge -> Store
                                                        ↓ (on failure)
                                                 Rule-based Fallback
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from database import get_report, get_share, init_db, insert_report, insert_share, update_report_error, update_report_payload
from fallback import generate_group_fallback, generate_relationship_fallback
from llm_service import build_llm_input, call_llm, call_llm_multi, USE_MULTI_CALL
from models import (
    AnalyzeRequest, AnalyzeResponse, ExportRequest, ExportResponse,
    ReportPayload, ReportSection, QuoteItem, HeroBlock, ShareBlock, Prediction,
    SharePayload, new_id, now_iso,
)
from prompts import build_group_roast_prompt, build_relationship_prompt, validate_llm_output
from stats import compute_stats

load_dotenv()

# ── App ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield

app = FastAPI(title="Cyber Judge API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Progress store ───────────────────────────────────────────────

_progress_store: dict[str, dict] = {}
_progress_events: dict[str, asyncio.Event] = {}

def _set_progress(report_id: str, step: str, status: str, error: str = ""):
    """Record a progress step and notify SSE listeners."""
    if report_id not in _progress_store:
        _progress_store[report_id] = {"steps": [], "overall": "processing"}
    _progress_store[report_id]["steps"].append({
        "step": step, "status": status, "error": error, "ts": now_iso(),
    })
    if report_id in _progress_events:
        _progress_events[report_id].set()
        _progress_events[report_id].clear()

def _finish_progress(report_id: str, success: bool):
    """Mark a report's progress as done or errored and notify listeners."""
    if report_id in _progress_store:
        _progress_store[report_id]["overall"] = "done" if success else "error"
    if report_id in _progress_events:
        _progress_events[report_id].set()

# ── Health ───────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": now_iso()}

# ── SSE Progress ─────────────────────────────────────────────────

@app.get("/api/report/{report_id}/progress")
async def report_progress(report_id: str):
    if report_id not in _progress_events:
        _progress_events[report_id] = asyncio.Event()

    async def event_stream():
        store = _progress_store.get(report_id, {})
        for step in store.get("steps", []):
            yield f"data: {json.dumps({'type': 'progress', **step})}\n\n"

        sent_steps = len(store.get("steps", []))
        overall = store.get("overall", "processing")
        if overall in ("done", "error"):
            yield f"data: {json.dumps({'type': overall})}\n\n"
            _progress_events.pop(report_id, None)
            _progress_store.pop(report_id, None)
            return

        while True:
            try:
                await asyncio.wait_for(_progress_events[report_id].wait(), timeout=30.0)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                continue

            store = _progress_store.get(report_id, {})
            steps = store.get("steps", [])
            overall = store.get("overall", "processing")

            while sent_steps < len(steps):
                step = steps[sent_steps]
                yield f"data: {json.dumps({'type': 'progress', **step})}\n\n"
                sent_steps += 1

            if overall in ("done", "error"):
                yield f"data: {json.dumps({'type': overall})}\n\n"
                break

        _progress_events.pop(report_id, None)
        _progress_store.pop(report_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

# ── Analyze ──────────────────────────────────────────────────────

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    """Submit pre-parsed messages for analysis. Returns immediately with report_id;
    processing continues in background."""
    messages = req.messages
    if not messages:
        raise HTTPException(400, "消息列表不能为空")

    max_msgs = int(os.environ.get("MAX_MESSAGES_PER_REQUEST", "50000"))
    if len(messages) > max_msgs:
        raise HTTPException(400, f"消息数量超过上限 ({max_msgs})")

    report_id = new_id()
    insert_report(report_id, req.report_type, now_iso(), "processing")

    if report_id not in _progress_events:
        _progress_events[report_id] = asyncio.Event()
    _progress_store[report_id] = {"steps": [], "overall": "processing"}

    asyncio.create_task(_process_report(report_id, req.report_type, messages))

    return AnalyzeResponse(
        report_id=report_id,
        status="processing",
        estimated_seconds=_estimate_time(len(messages)),
    )

def _estimate_time(msg_count: int) -> int:
    if msg_count < 500: return 5
    if msg_count < 2000: return 8
    if msg_count < 10000: return 15
    return 25

def _stat_dict(item: object, *, by_alias: bool = False) -> dict:
    if hasattr(item, "model_dump"):
        return item.model_dump(by_alias=by_alias)
    if isinstance(item, dict):
        return item
    raise TypeError(f"Unsupported stat item type: {type(item).__name__}")

# ── Report processing ────────────────────────────────────────────

async def _process_report(report_id: str, report_type: str, messages: list) -> None:
    """Background task: compute stats, run multi-call LLM pipeline, store result.
    Falls back to rule-based generation if all LLM calls fail."""
    try:
        _set_progress(report_id, "stats", "started")
        stats = compute_stats(messages, report_type)
        _set_progress(report_id, "stats", "done")

        participants_dicts = [p.model_dump() for p in stats.participants]
        keywords_dicts = [k.model_dump() for k in stats.keywords[:20]]
        emojis_dicts = [e.model_dump() for e in stats.emojis[:8]]
        timeline_dicts = [t.model_dump() for t in stats.timeline[:7]]
        chat_dna_dict = stats.chat_dna.model_dump() if stats.chat_dna else None
        chronotypes_dicts = [c.model_dump() for c in stats.chronotypes]
        sentiment_dict = stats.sentiment_overview.model_dump() if stats.sentiment_overview else None
        monthly_dicts = [m.model_dump() for m in stats.monthly_activity]
        initiative_dicts = [i.model_dump() for i in stats.initiative_scores]
        msg_type_dicts = [mt.model_dump() for mt in stats.message_type_breakdown]
        specificity_dicts = [ws.model_dump() for ws in stats.word_specificity]
        commonality_dicts = [wc.model_dump() for wc in stats.word_commonality]
        link_dicts = [l.model_dump() for l in stats.link_stats]
        badge_dicts = [b.model_dump() for b in stats.personality_badges]
        hourly_dicts = [h.model_dump() for h in stats.hourly_distribution]
        weekday_dicts = [w.model_dump() for w in stats.weekday_distribution]
        yearly_dicts = [y.model_dump() for y in stats.yearly_monthly]
        interaction_dicts = [_stat_dict(i, by_alias=True) for i in stats.interaction_matrix]
        mentions_dicts = [_stat_dict(a) for a in stats.at_mention_stats]
        famous_quote_dicts = [q for q in stats.famous_quotes[:10]]
        peak_day_dict = stats.peak_day.model_dump() if stats.peak_day else None
        annual_dict = stats.annual_summary.model_dump() if stats.annual_summary else None
        recall_dict = stats.recall_stats if stats.recall_stats else None
        red_packet_dict = stats.red_packet_overview if stats.red_packet_overview else None

        text_msgs = [m for m in messages if m.type == "text" and 3 <= len(m.content) <= 200]
        sender_counts = Counter(m.sender for m in text_msgs)
        top_senders = [s for s, _ in sender_counts.most_common(10)]
        top_messages: list[dict] = []
        seen_count: dict[str, int] = defaultdict(int)
        for m in text_msgs:
            if m.sender in top_senders and seen_count.get(m.sender, 0) < 15:
                top_messages.append({"sender": m.sender, "ts": m.ts, "content": m.content})
                seen_count[m.sender] = seen_count.get(m.sender, 0) + 1
            if len(top_messages) >= 200:
                break
        for m in text_msgs:
            if m.sender not in top_senders and seen_count.get(m.sender, 0) < 3:
                top_messages.append({"sender": m.sender, "ts": m.ts, "content": m.content})
                seen_count[m.sender] = seen_count.get(m.sender, 0) + 1
            if len(top_messages) >= 250:
                break

        active_days: set[str] = set()
        for m in messages:
            try:
                dt = datetime.fromisoformat(m.ts)
                active_days.add(dt.strftime("%Y-%m-%d"))
            except (ValueError, TypeError):
                pass

        llm_input = build_llm_input(
            report_type=report_type, participants=participants_dicts,
            keywords=keywords_dicts, emojis=emojis_dicts, timeline=timeline_dicts,
            total_messages=len(messages), active_days=len(active_days),
            top_messages=top_messages, chat_dna=chat_dna_dict,
            chronotypes=chronotypes_dicts, sentiment=sentiment_dict,
            monthly_activity=monthly_dicts, initiative_scores=initiative_dicts,
            message_type_breakdown=msg_type_dicts, word_specificity=specificity_dicts,
            word_commonality=commonality_dicts, link_stats=link_dicts,
            personality_badges=badge_dicts, hourly_distribution=hourly_dicts,
            weekday_distribution=weekday_dicts, yearly_monthly=yearly_dicts,
            interaction_matrix=interaction_dicts, at_mentions=mentions_dicts,
            famous_quotes=famous_quote_dicts, peak_day=peak_day_dict,
            annual_summary=annual_dict, recall_stats=recall_dict,
            red_packet_overview=red_packet_dict,
        )

        llm_success = False
        try:
            if USE_MULTI_CALL:
                async def _progress_cb(event: dict):
                    _set_progress(report_id, event["step"], event["status"], event.get("error", ""))

                llm_json = await call_llm_multi(
                    system_prompt="", user_message=llm_input,
                    participants=participants_dicts, message_samples=top_messages,
                    stats_input=llm_input, report_type=report_type,
                    progress_callback=_progress_cb,
                )
            else:
                _set_progress(report_id, "llm_single", "started")
                if report_type == "group_roast":
                    system, user = build_group_roast_prompt(llm_input)
                else:
                    system, user = build_relationship_prompt(llm_input)
                llm_json = await call_llm(system, user)
                _set_progress(report_id, "llm_single", "done")

            errors = validate_llm_output(llm_json, report_type)
            if errors:
                print(f"[LLM] Validation warnings: {errors}")
                if any("Missing required field" in e for e in errors):
                    raise ValueError(f"LLM output missing critical fields: {errors}")

            report = _merge_llm_with_stats(llm_json, stats, report_id, report_type)
            llm_success = True

        except Exception as e:
            print(f"[LLM] LLM generation failed: {e}")
            print(f"[LLM] Falling back to rule-based report generation.")

        if not llm_success:
            top_names = [p.name for p in stats.participants]
            if report_type == "group_roast":
                report = generate_group_fallback(stats, stats.participants, top_names)
            else:
                report = generate_relationship_fallback(stats, stats.participants, top_names)
            report.report_id = report_id

        payload = report.model_dump(by_alias=True)
        update_report_payload(report_id, payload, "done")
        _finish_progress(report_id, success=True)
        print(f"[Report] Report {report_id} generated successfully.")

    except Exception as e:
        traceback.print_exc()
        update_report_error(report_id, str(e))
        _finish_progress(report_id, success=False)
        print(f"[Report] Report {report_id} failed: {e}")

# ── Merge logic ──────────────────────────────────────────────────

SECTION_TYPE_MAP: dict[str, dict] = {
    "summary":               {"type": "summary",            "chart_ref": None},
    "dragon":                {"type": "dragon_rank",        "chart_ref": "participants"},
    "heatmap":               {"type": "heatmap",            "chart_ref": "heatmap"},
    "keywords":              {"type": "keywords",           "chart_ref": "keywords"},
    "msg-types":             {"type": "message_types",      "chart_ref": "message_type_breakdown"},
    "specificity":           {"type": "word_specificity",   "chart_ref": "word_specificity"},
    "chronotype":            {"type": "chronotype",         "chart_ref": "chronotypes"},
    "sentiment":             {"type": "sentiment",          "chart_ref": "sentiment_overview"},
    "radar":                 {"type": "radar",              "chart_ref": "radar"},
    "emoji":                 {"type": "emoji",              "chart_ref": "emojis"},
    "monthly":               {"type": "monthly",            "chart_ref": "monthly_activity"},
    "annual":                {"type": "annual",             "chart_ref": "annual_summary"},
    "time-profile":          {"type": "monthly",            "chart_ref": "hourly_distribution"},
    "initiative":            {"type": "initiative",         "chart_ref": "initiative_scores"},
    "interaction":           {"type": "relationship",       "chart_ref": "interaction_matrix"},
    "links":                 {"type": "links",              "chart_ref": "link_stats"},
    "timeline":              {"type": "timeline",           "chart_ref": "timeline"},
    "famous-quotes":         {"type": "timeline",           "chart_ref": "famous_quotes"},
    "chat-dna":              {"type": "chat_dna",           "chart_ref": None},
    "badges":                {"type": "personality_badges", "chart_ref": "personality_badges"},
    "predictions":           {"type": "predictions",        "chart_ref": "predictions"},
    "relationship-summary":  {"type": "summary",            "chart_ref": None},
    "relationship-map":      {"type": "relationship",       "chart_ref": "relationship_edges"},
    "relationship-keywords": {"type": "keywords",           "chart_ref": "keywords"},
    "relationship-msg-types":{"type": "message_types",      "chart_ref": "message_type_breakdown"},
    "relationship-time":     {"type": "monthly",            "chart_ref": "hourly_distribution"},
    "relationship-interaction":{"type": "relationship",     "chart_ref": "interaction_matrix"},
    "commonality":           {"type": "word_commonality",   "chart_ref": "word_commonality"},
    "relationship-emoji":    {"type": "emoji",              "chart_ref": "emojis"},
    "relationship-timeline": {"type": "timeline",           "chart_ref": "timeline"},
    "relationship-radar":    {"type": "radar",              "chart_ref": "radar"},
    "relationship-famous-quotes":{"type": "timeline",       "chart_ref": "famous_quotes"},
}

def _merge_llm_with_stats(llm_json: dict, stats: object, report_id: str, report_type: str) -> ReportPayload:
    """Merge LLM-generated content (roasts, quotes, sections, hero, predictions)
    with computed statistics into a complete ReportPayload."""
    participant_roasts = llm_json.get("participant_roasts", [])
    roast_map: dict[str, str] = {pr.get("name", ""): pr.get("roast", "") for pr in participant_roasts}
    for p in stats.participants:
        if p.name in roast_map:
            p.roast = roast_map[p.name]

    allowed_section_ids = {
        "summary", "dragon", "heatmap", "keywords", "msg-types", "specificity",
        "chronotype", "sentiment", "radar", "emoji", "monthly", "initiative",
        "links", "timeline", "chat-dna", "badges", "predictions",
    } if report_type == "group_roast" else {
        "relationship-summary", "relationship-map", "relationship-keywords",
        "commonality", "relationship-timeline", "relationship-radar",
        "sentiment", "chat-dna", "predictions",
    }

    sections = []
    for sec in llm_json.get("sections", []):
        sec_id = sec.get("id", "")
        if sec_id not in allowed_section_ids:
            continue
        mapping = SECTION_TYPE_MAP.get(sec_id, {"type": "summary", "chart_ref": None})
        sections.append(ReportSection(
            id=sec_id, type=mapping["type"],
            heading=sec.get("heading", ""), body=sec.get("body", ""),
            chart_ref=sec.get("chart_ref") or mapping["chart_ref"],
        ))

    quotes = []
    for q in llm_json.get("quotes", []):
        quotes.append(QuoteItem(
            id=q.get("id", f"q{len(quotes)}"), speaker=q.get("speaker", ""),
            text=q.get("text", ""), comment=q.get("comment", ""),
            icon=q.get("icon", "sparkles"),
        ))

    hero_data = llm_json.get("hero", {})
    hero = HeroBlock(
        kicker=hero_data.get("kicker", "群聊人格样本"),
        quote=hero_data.get("quote", ""),
        visual=hero_data.get("visual", "判"),
    )

    share_data = llm_json.get("share", {})
    share = ShareBlock(
        hook=share_data.get("hook", "来测测你的群聊画像"),
        watermark=share_data.get("watermark", "赛博判官生成"),
    )

    predictions_content = llm_json.get("predictions_content", [])
    if predictions_content:
        stats.predictions = [
            Prediction(id=p.get("id", f"p{i}"), title=p.get("title", ""),
                       body=p.get("body", ""), probability=p.get("probability", "中"))
            for i, p in enumerate(predictions_content)
        ]
        if not any(s.id == "predictions" for s in sections):
            sections.append(ReportSection(
                id="predictions", type="predictions", heading="赛博占卜",
                body="AI 基于数据趋势对群聊未来的预测。", chart_ref="predictions",
            ))

    chat_dna_text = llm_json.get("chat_dna_text", "")
    if chat_dna_text:
        found = False
        for sec in sections:
            if sec.id == "chat-dna":
                sec.body = chat_dna_text
                found = True
                break
        if not found:
            sections.append(ReportSection(
                id="chat-dna", type="chat_dna", heading="群聊基因报告",
                body=chat_dna_text, chart_ref=None,
            ))

    return ReportPayload(
        report_id=report_id, report_type=report_type, created_at=now_iso(),
        title=llm_json.get("title", "赛博判官报告"), tagline=llm_json.get("tagline", ""),
        hero=hero, tags=llm_json.get("tags", []),
        sections=sections, quotes=quotes, stats=stats, share=share,
    )

# ── Report endpoint ──────────────────────────────────────────────

@app.get("/api/report/{report_id}", response_model=ReportPayload)
async def get_report_endpoint(report_id: str):
    """Get a generated report by ID. Returns 202 while processing, 200 when done."""
    row = get_report(report_id)
    if row is None:
        raise HTTPException(404, "报告不存在")
    if row["status"] == "error":
        raise HTTPException(500, f"报告生成失败: {row.get('error_msg', '未知错误')}")
    if row["status"] == "processing":
        raise HTTPException(202, "报告正在生成中，请稍后再试")
    payload = row["payload_json"]
    if not payload or payload == {}:
        raise HTTPException(202, "报告正在生成中，请稍后再试")
    return payload

# ── Share endpoints ──────────────────────────────────────────────

@app.post("/api/share/{report_id}", response_model=SharePayload)
async def create_share_endpoint(report_id: str):
    row = get_report(report_id)
    if row is None:
        raise HTTPException(404, "报告不存在")
    if row["status"] != "done":
        raise HTTPException(400, "报告尚未生成完成，无法分享")

    payload = row["payload_json"]
    from database import get_conn
    conn = get_conn()
    existing = conn.execute("SELECT slug FROM share_logs WHERE report_id = ?", (report_id,)).fetchone()
    conn.close()

    if existing:
        slug = existing["slug"]
    else:
        import uuid
        slug = uuid.uuid4().hex[:8]
        insert_share(slug, report_id, now_iso())

    if "share" in payload:
        payload["share"]["slug"] = slug

    origin = os.environ.get("SHARE_BASE_URL", "http://localhost:5173")
    return SharePayload(slug=slug, url=f"{origin}/share/{slug}", report=ReportPayload(**payload))

@app.get("/api/share/{slug}", response_model=SharePayload)
async def get_share_endpoint(slug: str):
    row = get_share(slug)
    if row is None:
        raise HTTPException(404, "分享链接不存在或已失效")
    report_row = get_report(row["report_id"])
    if report_row is None:
        raise HTTPException(404, "报告不存在")

    payload = report_row["payload_json"]
    origin = os.environ.get("SHARE_BASE_URL", "http://localhost:5173")
    if "share" in payload:
        payload["share"]["slug"] = slug
    return SharePayload(slug=slug, url=f"{origin}/share/{slug}", report=ReportPayload(**payload))

# ── Upload (JSON only) ───────────────────────────────────────────

from parser import parse_and_validate
from wechat_importer import export_wechat_chat, get_wechat_prepare_status, list_wechat_chats, prepare_wechat_data
import stats_extra


def _anonymize_messages(messages: list) -> dict[str, str]:
    senders = list(dict.fromkeys(m.sender for m in messages))
    alias_map: dict[str, str] = {}
    for i, sender in enumerate(senders):
        alias_map[sender] = f"{chr(65 + (i % 26))}同学"
    for message in messages:
        message.sender = alias_map.get(message.sender, message.sender)
    return alias_map

@app.post("/api/upload")
async def upload_and_analyze(req: dict):
    """Accept raw WeFlow JSON text, parse, anonymize, and launch analysis."""
    text = req.get("text", "")
    report_type = req.get("report_type", "group_roast")
    anonymized = req.get("anonymized", True)

    if not text.strip():
        raise HTTPException(400, "文本内容不能为空")

    messages = parse_and_validate(text)
    if not messages:
        raise HTTPException(400, "未能解析出消息，请检查JSON格式")

    if anonymized:
        _anonymize_messages(messages)

    from models import AnalyzeRequest, PrivacyConfig, ClientMeta
    analyze_req = AnalyzeRequest(
        report_type=report_type, source="weflow_json",
        messages=messages, privacy=PrivacyConfig(anonymized=anonymized),
        client_meta=ClientMeta(),
    )
    return await analyze(analyze_req)


@app.get("/api/wechat/chats")
async def list_wechat_chats_endpoint(
    query: str = "",
    limit: int = 50,
    start_time: str = "",
    end_time: str = "",
):
    """List local WeChat sessions from the configured wechat-decrypt project."""
    try:
        return list_wechat_chats(
            query=query,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"读取微信会话失败: {exc}") from exc


@app.get("/api/wechat/prepare")
async def get_wechat_prepare_status_endpoint():
    """Return whether local WeChat databases are already decrypted."""
    try:
        return get_wechat_prepare_status()
    except Exception as exc:
        raise HTTPException(500, f"读取微信准备状态失败: {exc}") from exc


@app.post("/api/wechat/prepare")
async def prepare_wechat_endpoint(req: dict | None = None):
    """Extract keys and decrypt bundled WeChat databases for local import."""
    req = req or {}
    try:
        return prepare_wechat_data(force=bool(req.get("force", False)))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"准备微信数据库失败: {exc}") from exc


@app.post("/api/wechat/export")
async def export_wechat_and_analyze(req: dict):
    """Export one WeChat chat to JSON, parse it, and launch the existing analysis."""
    username = str(req.get("username", "")).strip()
    if not username:
        raise HTTPException(400, "请选择一个微信会话")

    report_type = req.get("report_type", "group_roast")
    anonymized = req.get("anonymized", True)
    start_time = str(req.get("start_time", "") or "")
    end_time = str(req.get("end_time", "") or "")

    try:
        exported = export_wechat_chat(
            username=username,
            start_time=start_time,
            end_time=end_time,
        )
        export_path = exported.get("export_path", "")
        if not export_path:
            raise RuntimeError("导出完成但未找到 JSON 文件路径")
        with open(export_path, "r", encoding="utf-8") as f:
            text = f.read()
        messages = parse_and_validate(text)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(500, f"读取导出 JSON 失败: {exc}") from exc

    if anonymized:
        _anonymize_messages(messages)

    from models import AnalyzeRequest, PrivacyConfig, ClientMeta
    analyze_req = AnalyzeRequest(
        report_type=report_type, source="wechat_decrypt_json",
        messages=messages, privacy=PrivacyConfig(anonymized=anonymized),
        client_meta=ClientMeta(),
    )
    response = await analyze(analyze_req)
    payload = response.model_dump()
    payload["export"] = exported
    return payload

# ── Export ───────────────────────────────────────────────────────

@app.post("/api/export", response_model=ExportResponse)
async def export_report(req: ExportRequest):
    row = get_report(req.report_id)
    if row is None:
        raise HTTPException(404, "报告不存在")
    if row["status"] != "done":
        raise HTTPException(400, "报告尚未生成完成")

    payload = row["payload_json"]
    report = ReportPayload(**payload)

    if req.format == "json":
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        return ExportResponse(content=content, content_type="application/json",
                              filename=f"cyber-judge-report-{req.report_id}.json")
    elif req.format == "csv":
        csv_content, _ = stats_extra.build_export_data(payload)
        return ExportResponse(content=csv_content, content_type="text/csv; charset=utf-8",
                              filename=f"cyber-judge-report-{req.report_id}.csv")
    elif req.format == "xlsx":
        participants = payload.get("stats", {}).get("participants", [])
        tsv = "姓名\t消息数\t字数\t表情数\t平均长度\t图片数\t链接数\n"
        for p in participants:
            tsv += f'{p["name"]}\t{p["message_count"]}\t{p["character_count"]}\t{p["emoji_count"]}\t{p["average_length"]}\t{p.get("image_count",0)}\t{p.get("link_count",0)}\n'
        return ExportResponse(content=tsv, content_type="application/vnd.ms-excel",
                              filename=f"cyber-judge-report-{req.report_id}.xls")
    elif req.format == "txt":
        lines = [f"{'='*50}", f"  {report.title}", f"  {report.tagline}", f"{'='*50}", ""]
        for sec in report.sections:
            lines.append(f"## {sec.heading}\n{sec.body}\n")
        lines.append(f"\n{'='*50}\n  生成时间: {report.created_at}\n  报告ID: {report.report_id}")
        content = "\n".join(lines)
        return ExportResponse(content=content, content_type="text/plain; charset=utf-8",
                              filename=f"cyber-judge-report-{req.report_id}.txt")
    elif req.format == "html":
        html = _build_html_export(report)
        return ExportResponse(content=html, content_type="text/html; charset=utf-8",
                              filename=f"cyber-judge-report-{req.report_id}.html")
    else:
        raise HTTPException(400, f"Unsupported format: {req.format}")

def _build_html_export(report: ReportPayload) -> str:
    sections_html = "".join(
        f'<div class="section"><h2>{s.heading}</h2><p>{s.body}</p></div>'
        for s in report.sections
    )
    quotes_html = "".join(
        f'<blockquote><p>「{q.text}」</p><footer>— {q.speaker} | {q.comment}</footer></blockquote>'
        for q in report.quotes
    )
    tags_html = " ".join(f'<span class="tag">{t}</span>' for t in report.tags)
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{report.title}</title><style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:800px;margin:0 auto;padding:2rem;background:#0f0f23;color:#e0e0e0}}h1{{font-size:2rem;color:#a78bfa}}.tagline{{color:#888;font-style:italic}}.tags{{margin:1rem 0}}.tag{{background:#2d2d5e;color:#a78bfa;padding:.2rem .8rem;border-radius:1rem;font-size:.85rem;margin-right:.5rem}}.hero{{text-align:center;padding:3rem 0;border-bottom:1px solid #2d2d5e;margin-bottom:2rem}}.hero .kicker{{color:#a78bfa;font-size:.9rem;text-transform:uppercase;letter-spacing:.1em}}.hero .quote{{font-size:1.3rem;color:#c4b5fd;font-style:italic;margin:1rem 0}}.section{{margin:2rem 0;padding:1.5rem;background:#1a1a2e;border-radius:.75rem}}.section h2{{color:#a78bfa;margin-top:0}}blockquote{{border-left:3px solid #a78bfa;padding-left:1rem;margin:1rem 0}}blockquote footer{{color:#888;font-size:.85rem;margin-top:.5rem}}.watermark{{text-align:center;color:#555;margin-top:3rem;padding-top:1rem;border-top:1px solid #2d2d5e}}</style></head><body><div class="hero"><div class="kicker">{report.hero.kicker}</div><h1>{report.title}</h1><p class="tagline">{report.tagline}</p><div class="quote">"{report.hero.quote}"</div><div class="tags">{tags_html}</div></div>{sections_html}<div class="quotes">{quotes_html}</div><div class="watermark">{report.share.watermark} · {report.created_at[:10]}</div></body></html>"""

# ── Run ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8000")), reload=True)
