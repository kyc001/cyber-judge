"""Cyber Judge (赛博判官) API Server.

Endpoints:
  POST /api/upload          — Upload WeFlow JSON, start analysis
  GET  /api/report/:id      — Get generated report (polls with 202 while processing)
  GET  /api/report/:id/progress — SSE stream of LLM sub-call progress
  POST /api/share/:id       — Create a share link
  GET  /api/share/:slug     — Load a shared report
  POST /api/export          — Export report as json/csv/txt/html
  GET  /api/llm/config      — Read local LLM provider/model state
  POST /api/llm/config      — Save local LLM provider/model/key
  POST /api/llm/test        — Test selected LLM connection
  GET  /api/health          — Health check

Architecture: Upload -> Parser -> Stats -> LLM (multi-call) -> Merge -> Store
                                                        ↓ (on failure)
                                                 Rule-based Fallback
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import traceback
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from database import get_report, get_share, init_db, insert_report, insert_share, update_report_error, update_report_payload
from fallback import generate_group_fallback, generate_relationship_fallback
from llm_service import (
    USE_MULTI_CALL,
    build_llm_input,
    call_llm,
    call_llm_multi,
    get_llm_config_for_api,
    save_llm_config_from_api,
    test_llm_config_from_api,
)
from models import (
    AnalyzeRequest, AnalyzeResponse, ContentHighlight, DialogueLine, ExportRequest, ExportResponse,
    ReportPayload, ReportSection, QuoteItem, HeroBlock, ShareBlock, Prediction,
    SharePayload, new_id, now_iso,
)
from prompts import build_group_roast_prompt, build_relationship_prompt, validate_llm_output
from stats import compute_stats

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

if os.environ.get("CYBER_JUDGE_DESKTOP") != "1":
    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv()

def _configure_piped_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                continue
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


_configure_piped_stdio()

MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "30"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

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
_wechat_import_store: dict[str, dict] = {}
_wechat_import_events: dict[str, asyncio.Event] = {}

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


def _set_wechat_import_progress(
    import_id: str,
    step: str,
    status: str,
    percent: int,
    message: str = "",
    error: str = "",
):
    """Record a local WeChat import step and notify SSE listeners."""
    if import_id not in _wechat_import_store:
        _wechat_import_store[import_id] = {"steps": [], "overall": "processing"}
    _wechat_import_store[import_id]["steps"].append({
        "step": step,
        "status": status,
        "percent": max(0, min(100, int(percent))),
        "message": message,
        "error": error,
        "ts": now_iso(),
    })
    if import_id in _wechat_import_events:
        _wechat_import_events[import_id].set()
        _wechat_import_events[import_id].clear()


def _finish_wechat_import(
    import_id: str,
    *,
    success: bool,
    report_id: str = "",
    export: dict | None = None,
    error: str = "",
):
    if import_id not in _wechat_import_store:
        _wechat_import_store[import_id] = {"steps": [], "overall": "processing"}
    _wechat_import_store[import_id]["overall"] = "done" if success else "error"
    _wechat_import_store[import_id]["report_id"] = report_id
    _wechat_import_store[import_id]["export"] = export or {}
    _wechat_import_store[import_id]["error"] = error
    if import_id in _wechat_import_events:
        _wechat_import_events[import_id].set()
    try:
        asyncio.create_task(_cleanup_wechat_import_later(import_id))
    except RuntimeError:
        pass


async def _cleanup_wechat_import_later(import_id: str, delay_seconds: int = 1800):
    await asyncio.sleep(delay_seconds)
    _wechat_import_events.pop(import_id, None)
    _wechat_import_store.pop(import_id, None)

# ── Health ───────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": now_iso()}


@app.get("/api/llm/config")
async def llm_config():
    """Return frontend-safe LLM configuration."""
    return get_llm_config_for_api()


@app.post("/api/llm/config")
async def save_llm_config(req: dict):
    """Persist local LLM provider/model/key settings."""
    try:
        return save_llm_config_from_api(req)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(500, f"保存模型配置失败: {exc}") from exc


@app.post("/api/llm/test")
async def test_llm_config(req: dict):
    """Check whether the selected provider/model/key can answer."""
    try:
        return await test_llm_config_from_api(req)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"模型连通性检查失败: {exc}") from exc

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


@app.get("/api/wechat/import/{import_id}/progress")
async def wechat_import_progress(import_id: str):
    if import_id not in _wechat_import_events:
        _wechat_import_events[import_id] = asyncio.Event()

    async def event_stream():
        store = _wechat_import_store.get(import_id, {})
        for step in store.get("steps", []):
            yield f"data: {json.dumps({'type': 'progress', **step}, ensure_ascii=False)}\n\n"

        sent_steps = len(store.get("steps", []))
        overall = store.get("overall", "processing")
        if overall in ("done", "error"):
            yield f"data: {json.dumps({'type': overall, 'report_id': store.get('report_id', ''), 'export': store.get('export', {}), 'error': store.get('error', '')}, ensure_ascii=False)}\n\n"
            _wechat_import_events.pop(import_id, None)
            return

        while True:
            try:
                await asyncio.wait_for(_wechat_import_events[import_id].wait(), timeout=30.0)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"
                continue

            store = _wechat_import_store.get(import_id, {})
            steps = store.get("steps", [])
            overall = store.get("overall", "processing")

            while sent_steps < len(steps):
                step = steps[sent_steps]
                yield f"data: {json.dumps({'type': 'progress', **step}, ensure_ascii=False)}\n\n"
                sent_steps += 1

            if overall in ("done", "error"):
                yield f"data: {json.dumps({'type': overall, 'report_id': store.get('report_id', ''), 'export': store.get('export', {}), 'error': store.get('error', '')}, ensure_ascii=False)}\n\n"
                break

        _wechat_import_events.pop(import_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/api/wechat/import/{import_id}/json")
async def download_wechat_import_json(import_id: str):
    store = _wechat_import_store.get(import_id)
    if not store or store.get("overall") != "done":
        raise HTTPException(404, "导入任务不存在或尚未完成")
    exported = store.get("export") or {}
    export_path = str(exported.get("export_path", "") or "")
    if not export_path or not Path(export_path).is_file():
        raise HTTPException(404, "导出的 JSON 文件不存在")
    return FileResponse(
        export_path,
        media_type="application/json",
        filename=str(exported.get("filename") or Path(export_path).name),
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


def _message_dict(message: object) -> dict:
    return {"sender": message.sender, "ts": message.ts, "content": message.content.strip()}


def _message_score(message: object, index: int, total: int, keyword_set: set[str]) -> float:
    content = message.content.strip()
    score = 0.0
    length = len(content)
    if 8 <= length <= 80:
        score += 3
    elif 81 <= length <= 160:
        score += 1.4
    if re.search(r"[!?？！…~]{1,}", content):
        score += 1.2
    if re.search(r"(哈哈|笑死|救命|离谱|绝了|破防|绷不住|牛|草|啊|？|！)", content, re.I):
        score += 2.4
    if any(word and word in content for word in keyword_set):
        score += 1.6
    if 0 < index < total - 1:
        score += 0.6
    return score


def _build_context_windows(messages: list, targets: list[tuple[int, object]], *, max_windows: int = 12) -> list[dict]:
    windows: list[dict] = []
    used_ranges: list[range] = []
    for index, message in targets:
        start = max(0, index - 1)
        end = min(len(messages), index + 3)
        current_range = range(start, end)
        if any(set(current_range).intersection(existing) for existing in used_ranges):
            continue
        evidence = [
            _message_dict(candidate)
            for candidate in messages[start:end]
            if candidate.type == "text" and candidate.content.strip()
        ][:4]
        if evidence:
            windows.append({
                "anchor_sender": message.sender,
                "anchor_ts": message.ts,
                "anchor": message.content.strip(),
                "evidence": evidence,
            })
            used_ranges.append(current_range)
        if len(windows) >= max_windows:
            break
    return windows


def _select_llm_message_samples(messages: list, stats: object, *, max_samples: int = 180) -> list[dict]:
    text_items = [
        (index, message)
        for index, message in enumerate(messages)
        if message.type == "text" and 3 <= len(message.content.strip()) <= 220
    ]
    if not text_items:
        return []

    keyword_set = {item.word for item in stats.keywords[:20]}
    scored = sorted(
        text_items,
        key=lambda item: _message_score(item[1], item[0], len(messages), keyword_set),
        reverse=True,
    )

    selected_indices: set[int] = set()
    selected: list[dict] = []

    def add_window(center_index: int) -> None:
        start = max(0, center_index - 1)
        end = min(len(messages), center_index + 3)
        for idx in range(start, end):
            if idx in selected_indices:
                continue
            message = messages[idx]
            if message.type != "text" or not message.content.strip():
                continue
            selected_indices.add(idx)
            selected.append(_message_dict(message))

    for index, _ in scored[:45]:
        add_window(index)
        if len(selected) >= max_samples:
            break

    sender_counts = Counter(message.sender for _, message in text_items)
    for sender, _ in sender_counts.most_common(20):
        per_sender = [item for item in text_items if item[1].sender == sender]
        if not per_sender:
            continue
        for position in (0, len(per_sender) // 2, len(per_sender) - 1):
            add_window(per_sender[position][0])
            if len(selected) >= max_samples:
                break
        if len(selected) >= max_samples:
            break

    stride = max(1, len(text_items) // 24)
    for index, _ in text_items[::stride]:
        add_window(index)
        if len(selected) >= max_samples:
            break

    selected.sort(key=lambda item: item.get("ts", ""))
    return selected[:max_samples]


def _build_highlight_windows(messages: list, stats: object) -> list[dict]:
    text_items = [
        (index, message)
        for index, message in enumerate(messages)
        if message.type == "text" and 6 <= len(message.content.strip()) <= 180
    ]
    keyword_set = {item.word for item in stats.keywords[:20]}
    scored = sorted(
        text_items,
        key=lambda item: _message_score(item[1], item[0], len(messages), keyword_set),
        reverse=True,
    )
    top_targets = scored[:20]
    return _build_context_windows(messages, top_targets, max_windows=10)

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

        top_messages = _select_llm_message_samples(messages, stats)
        highlight_windows = _build_highlight_windows(messages, stats)

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
            highlight_windows=highlight_windows,
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
                    highlight_windows=highlight_windows,
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
                report = generate_group_fallback(stats, stats.participants, top_names, highlight_windows)
            else:
                report = generate_relationship_fallback(stats, stats.participants, top_names, highlight_windows)
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

    content_highlights: list[ContentHighlight] = []
    for item in llm_json.get("content_highlights", []):
        evidence: list[DialogueLine] = []
        for line in item.get("evidence", [])[:4]:
            text = line.get("text") or line.get("content") or ""
            if not text:
                continue
            evidence.append(DialogueLine(
                sender=line.get("sender", ""),
                text=text,
                ts=line.get("ts") or None,
            ))
        if not evidence:
            continue
        content_highlights.append(ContentHighlight(
            id=item.get("id", f"h{len(content_highlights) + 1}"),
            title=item.get("title", "真实对话亮点"),
            insight=item.get("insight", ""),
            tag=item.get("tag", "content"),
            evidence=evidence,
        ))

    if not content_highlights and stats.famous_quotes:
        for index, quote in enumerate(stats.famous_quotes[:3], start=1):
            content_highlights.append(ContentHighlight(
                id=f"h{index}",
                title="算法抓到的名场面",
                insight="这句话在长度、语气或情绪上都比普通消息更突出，适合作为二次点评的证据片段。",
                tag="content",
                evidence=[DialogueLine(
                    sender=quote.get("sender", ""),
                    text=quote.get("content", ""),
                    ts=quote.get("ts") or None,
                )],
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
                body="基于数据趋势对群聊未来的预测。", chart_ref="predictions",
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
        sections=sections, quotes=quotes, content_highlights=content_highlights,
        insight_briefs=llm_json.get("insight_briefs", {}) if isinstance(llm_json.get("insight_briefs", {}), dict) else {},
        stats=stats, share=share,
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

from parser import parse_and_validate, parse_json_file
from wechat_importer import (
    export_wechat_chat,
    get_wechat_prepare_status,
    list_wechat_chats,
    prepare_wechat_data,
)
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
    if len(text.encode("utf-8")) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(400, f"文件超过 {MAX_UPLOAD_SIZE_MB}MB")

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
    kind: str = "all",
    limit: int = 50,
    start_time: str = "",
    end_time: str = "",
):
    """List local WeChat sessions from the configured wechat-decrypt project."""
    try:
        return list_wechat_chats(
            query=query,
            kind=kind,
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


@app.post("/api/wechat/import")
async def start_wechat_import(req: dict):
    """Start a local WeChat import task and stream progress over SSE."""
    username = str(req.get("username", "")).strip()
    if not username:
        raise HTTPException(400, "请选择一个微信会话")

    import_id = new_id()
    _wechat_import_events[import_id] = asyncio.Event()
    _wechat_import_store[import_id] = {"steps": [], "overall": "processing"}
    _set_wechat_import_progress(import_id, "queued", "started", 3, "导入任务已创建")
    asyncio.create_task(_process_wechat_import(import_id, req))
    return {"import_id": import_id, "status": "processing", "estimated_seconds": 20}


async def _process_wechat_import(import_id: str, req: dict):
    username = str(req.get("username", "")).strip()
    report_type = req.get("report_type", "group_roast")
    anonymized = req.get("anonymized", True)
    start_time = str(req.get("start_time", "") or "")
    end_time = str(req.get("end_time", "") or "")
    output_dir = str(req.get("output_dir", "") or "")
    incremental = bool(req.get("incremental", True)) and not start_time and not end_time

    try:
        _set_wechat_import_progress(import_id, "export", "started", 12, "正在导出微信聊天")
        exported = await asyncio.to_thread(
            export_wechat_chat,
            username=username,
            start_time=start_time,
            end_time=end_time,
            output_dir=output_dir,
            incremental=incremental,
        )
        export_path = exported.get("export_path", "")
        if not export_path:
            raise RuntimeError("导出完成但未找到 JSON 文件路径")
        exported["filename"] = Path(export_path).name
        _set_wechat_import_progress(
            import_id,
            "export",
            "done",
            48,
            f"已导出 {int(exported.get('message_count') or 0):,} 条消息",
        )

        _set_wechat_import_progress(import_id, "parse", "started", 58, "正在解析聊天 JSON")
        messages = await asyncio.to_thread(parse_json_file, export_path)
        _set_wechat_import_progress(
            import_id,
            "parse",
            "done",
            72,
            f"已解析 {len(messages):,} 条消息",
        )

        if anonymized:
            _set_wechat_import_progress(import_id, "privacy", "started", 78, "正在处理昵称脱敏")
            await asyncio.to_thread(_anonymize_messages, messages)
            _set_wechat_import_progress(import_id, "privacy", "done", 82, "昵称脱敏完成")

        _set_wechat_import_progress(import_id, "analysis", "started", 88, "正在创建分析任务")
        from models import AnalyzeRequest, PrivacyConfig, ClientMeta
        analyze_req = AnalyzeRequest(
            report_type=report_type, source="wechat_decrypt_json",
            messages=messages, privacy=PrivacyConfig(anonymized=anonymized),
            client_meta=ClientMeta(),
        )
        response = await analyze(analyze_req)
        payload = response.model_dump()
        payload["export"] = exported
        _set_wechat_import_progress(import_id, "analysis", "done", 96, "分析任务已创建")
        _finish_wechat_import(
            import_id,
            success=True,
            report_id=payload["report_id"],
            export=exported,
        )
    except Exception as exc:
        _set_wechat_import_progress(
            import_id,
            "error",
            "error",
            100,
            "导入失败",
            str(exc),
        )
        _finish_wechat_import(import_id, success=False, error=str(exc))


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
    output_dir = str(req.get("output_dir", "") or "")
    include_json = bool(req.get("include_json", False))
    incremental = bool(req.get("incremental", True)) and not start_time and not end_time

    try:
        exported = export_wechat_chat(
            username=username,
            start_time=start_time,
            end_time=end_time,
            output_dir=output_dir,
            incremental=incremental,
        )
        export_path = exported.get("export_path", "")
        if not export_path:
            raise RuntimeError("导出完成但未找到 JSON 文件路径")
        exported["filename"] = Path(export_path).name
        if include_json:
            with open(export_path, "r", encoding="utf-8") as f:
                text = f.read()
            exported["json_text"] = text
            messages = parse_and_validate(text)
        else:
            messages = parse_json_file(export_path)
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

def _frontend_dist_candidates() -> list[Path]:
    candidates: list[Path] = []
    explicit = os.environ.get("CYBER_JUDGE_FRONTEND_DIST", "").strip()
    if explicit:
        candidates.append(Path(explicit))

    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        candidates.extend([
            base / "frontend" / "dist",
            base / "frontend_dist",
            Path(sys.executable).resolve().parent / "frontend" / "dist",
        ])

    candidates.extend([
        PROJECT_DIR / "frontend" / "dist",
        BACKEND_DIR / "frontend_dist",
    ])
    return candidates


def _resolve_frontend_dist() -> Path | None:
    for candidate in _frontend_dist_candidates():
        if (candidate / "index.html").exists():
            return candidate.resolve()
    return None


FRONTEND_DIST_DIR = _resolve_frontend_dist()

if FRONTEND_DIST_DIR is not None:
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_app(full_path: str):
    """Serve the production React app in desktop/static mode."""
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(404, "API route not found")

    if FRONTEND_DIST_DIR is None:
        raise HTTPException(404, "Frontend build assets not found. Run npm run build first.")

    requested = (FRONTEND_DIST_DIR / full_path).resolve()
    try:
        requested.relative_to(FRONTEND_DIST_DIR)
    except ValueError:
        raise HTTPException(404, "File not found") from None

    if requested.is_file():
        return FileResponse(requested)
    return FileResponse(FRONTEND_DIST_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    reload_exclude_roots = [
        "data",
        "imported_chats",
        "wechat_decrypt/decrypted",
        "wechat_decrypt/decoded_images",
        "wechat_decrypt/exported_chats",
        "wechat_decrypt/wxwork_decrypted",
        "wechat_decrypt/wxwork_export",
    ]
    reload_excludes = [
        pattern
        for root in reload_exclude_roots
        for pattern in (f"{root}/*", f"{root}/**/*")
    ]
    reload_excludes.extend([
        "wechat_decrypt/config.json",
        "wechat_decrypt/all_keys*.json",
        "wechat_decrypt/wxwork_keys*.json",
    ])

    uvicorn.run("main:app", host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8000")), reload=True,
                reload_excludes=reload_excludes)
