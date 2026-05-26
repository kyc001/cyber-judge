"""LLM service layer with multi-provider support, retry, fallback, and JSON repair.

Supports DeepSeek, Qwen, OpenAI, and OpenAI-compatible APIs.
Multi-call architecture splits report generation into targeted sub-calls
(participants, quotes, sections, predictions) for higher quality output.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Optional

import httpx

# ── Config ───────────────────────────────────────────────────────

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "deepseek")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

LLM_FALLBACK_PROVIDER = os.environ.get("LLM_FALLBACK_PROVIDER", "openai")
LLM_FALLBACK_API_KEY = os.environ.get("LLM_FALLBACK_API_KEY", "")
LLM_FALLBACK_API_BASE = os.environ.get("LLM_FALLBACK_API_BASE", "https://api.openai.com/v1")
LLM_FALLBACK_MODEL = os.environ.get("LLM_FALLBACK_MODEL", "gpt-4o-mini")

TIMEOUT = int(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))
MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "2"))
MAX_OUTPUT_TOKENS = 4096

# Multi-call mode: split into targeted sub-calls (better quality, shows progress)
USE_MULTI_CALL = os.environ.get("LLM_MULTI_CALL", "true").lower() == "true"


# ── LLM Client ───────────────────────────────────────────────────

class LLMClient:
    """OpenAI-compatible chat completion client with JSON mode support."""

    def __init__(self, provider: str, api_key: str, api_base: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model

    async def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a chat completion request with JSON mode enabled."""
        if not self.api_key:
            raise ValueError(f"LLM API key not configured for provider '{self.provider}'")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.8,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.api_base}/chat/completions"
        async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT)) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_raw(self, system_prompt: str, user_message: str) -> str:
        """Send a chat completion request without JSON mode (free-form text output)."""
        if not self.api_key:
            raise ValueError(f"LLM API key not configured for provider '{self.provider}'")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.8,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.api_base}/chat/completions"
        async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT)) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


def _get_primary_client() -> LLMClient:
    """Build the primary LLM client from environment config."""
    return LLMClient(provider=LLM_PROVIDER, api_key=LLM_API_KEY,
                     api_base=LLM_API_BASE, model=LLM_MODEL)

def _get_fallback_client() -> Optional[LLMClient]:
    """Build the fallback LLM client if a fallback API key is configured."""
    if LLM_FALLBACK_API_KEY:
        return LLMClient(provider=LLM_FALLBACK_PROVIDER, api_key=LLM_FALLBACK_API_KEY,
                         api_base=LLM_FALLBACK_API_BASE, model=LLM_FALLBACK_MODEL)
    return None


# ── JSON Repair ──────────────────────────────────────────────────

def repair_truncated_json(text: str) -> str:
    """Repair truncated JSON from LLM output.

    Handles three truncation scenarios (from whatsapp-wrapped-v3 pattern):
    1. Unclosed string — append closing quote
    2. Unclosed braces/brackets — count and append missing closers
    3. Markdown code fences — strip them first
    """
    text = text.strip()

    # Strip code fences
    if text.startswith("```"):
        if "\n" in text:
            text = text[text.index("\n") + 1:]
        else:
            text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # If it already parses, return as-is
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Close unclosed string (ends mid-value)
    # If last non-whitespace char is not } ] or ", we might be mid-string
    stripped = text.rstrip()
    if stripped and stripped[-1] not in (']', '}', '"'):
        # Check if we're inside a string value
        in_string = False
        escape_next = False
        for ch in stripped:
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
        if in_string:
            text = stripped + '"'

    # Count braces and brackets (respecting strings)
    def _count_structure(s: str):
        depth_brace = 0
        depth_bracket = 0
        in_str = False
        esc = False
        for ch in s:
            if esc:
                esc = False
                continue
            if ch == '\\':
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == '{':
                depth_brace += 1
            elif ch == '}':
                depth_brace -= 1
            elif ch == '[':
                depth_bracket += 1
            elif ch == ']':
                depth_bracket -= 1
        return depth_brace, depth_bracket

    open_braces, open_brackets = _count_structure(text)

    # Append missing closers
    if open_brackets > 0:
        text += "]" * open_brackets
    if open_braces > 0:
        text += "}" * open_braces

    return text


# ── JSON Extraction ──────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Extract valid JSON from LLM response, with repair fallback."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try repair
    repaired = repair_truncated_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in code fences
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            repaired = repair_truncated_json(m.group(1))
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    # Try to find outermost braces
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            repaired = repair_truncated_json(m.group(0))
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Failed to extract valid JSON from LLM response: {text[:200]}...")


# ── Main Call with Retry + Fallback ──────────────────────────────

async def call_llm(system_prompt: str, user_message: str) -> dict:
    """Single call to LLM with retry and fallback. Returns parsed JSON."""
    last_error: Optional[Exception] = None

    primary = _get_primary_client()
    for attempt in range(MAX_RETRIES + 1):
        try:
            raw = await primary.chat(system_prompt, user_message)
            return _extract_json(raw)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"[LLM] Primary attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

    fallback = _get_fallback_client()
    if fallback:
        print(f"[LLM] Primary exhausted. Trying fallback ({fallback.provider})...")
        try:
            raw = await fallback.chat(system_prompt, user_message)
            return _extract_json(raw)
        except Exception as e:
            last_error = e
            print(f"[LLM] Fallback also failed: {e}")

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


async def call_llm_raw(system_prompt: str, user_message: str) -> str:
    """Single call to LLM returning raw text (no JSON parsing)."""
    last_error: Optional[Exception] = None

    primary = _get_primary_client()
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await primary.chat_raw(system_prompt, user_message)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"[LLM] Raw attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

    fallback = _get_fallback_client()
    if fallback:
        print(f"[LLM] Raw primary exhausted. Trying fallback ({fallback.provider})...")
        try:
            return await fallback.chat_raw(system_prompt, user_message)
        except Exception as e:
            last_error = e
            print(f"[LLM] Raw fallback also failed: {e}")

    raise RuntimeError(f"All LLM providers failed for raw call. Last error: {last_error}")


# ── Multi-Call: Targeted LLM Calls ───────────────────────────────

async def analyze_participants(
    participants: list[dict],
    message_samples: list[dict],
    report_type: str,
) -> list[dict]:
    """Per-person roast + personality, informed by their actual messages.

    Returns list of {"name": "...", "roast": "...", "personality": "..."}
    """
    # Build per-person message samples
    person_msgs: dict[str, list[str]] = {}
    for m in message_samples:
        name = m.get("sender", m.get("name", ""))
        if name not in person_msgs:
            person_msgs[name] = []
        if len(person_msgs[name]) < 8:
            person_msgs[name].append(m.get("content", "")[:120])

    lines = ["## 成员统计与真实发言\n"]
    for p in participants[:10]:
        name = p["name"]
        msgs = person_msgs.get(name, [])
        lines.append(f"### {name}")
        lines.append(f"数据: {p.get('message_count',0)}条消息, {p.get('character_count',0)}字, "
                     f"表情{p.get('emoji_count',0)}次, 平均{p.get('average_length',0)}字/条")
        if msgs:
            lines.append("真实发言样本:")
            for msg in msgs[:6]:
                lines.append(f"  - 「{msg}」")
        lines.append("")

    system = PARTICIPANTS_SYSTEM
    user = "\n".join(lines) + "\n请为每位成员生成锐评和性格标签。只输出 JSON。"

    result = await call_llm(system, user)
    return result.get("participants", [])


async def extract_quotes(
    message_samples: list[dict],
    report_type: str,
) -> list[dict]:
    """Extract memorable quotes from actual message content.

    Returns list of {"speaker": "...", "text": "...", "comment": "...", "icon": "..."}
    """
    # Format messages as readable transcript
    lines = ["## 聊天记录样本（请从中挑选金句）\n"]
    for i, m in enumerate(message_samples[:200]):
        sender = m.get("sender", m.get("name", ""))
        content = m.get("content", "")[:150]
        ts = (m.get("ts", "") or "")[:16]
        if content.strip():
            lines.append(f"[{i}] {sender}: {content}")

    system = QUOTES_SYSTEM
    if report_type == "relationship":
        system = QUOTES_SYSTEM_RELATIONSHIP
    user = "\n".join(lines) + "\n\n请从上述聊天记录中挑选 3-5 条金句并点评。只输出 JSON。"

    result = await call_llm(system, user)
    return result.get("quotes", [])


async def generate_sections(
    stats_input: str,
    report_type: str,
) -> list[dict]:
    """Generate body text for each report section based on stats.

    Returns list of section objects with id, type, heading, body, chart_ref.
    """
    system = SECTIONS_SYSTEM_GROUP if report_type == "group_roast" else SECTIONS_SYSTEM_RELATIONSHIP
    user = f"{stats_input}\n\n请为每个 section 生成 body 文案。只输出 JSON。"

    result = await call_llm(system, user)
    return result.get("sections", [])


async def generate_hero_and_tags(
    stats_input: str,
    report_type: str,
) -> dict:
    """Generate hero block, title, tagline, and tags.

    Returns {"title": "...", "tagline": "...", "hero": {...}, "tags": [...]}
    """
    system = HERO_SYSTEM_GROUP if report_type == "group_roast" else HERO_SYSTEM_RELATIONSHIP
    user = f"{stats_input}\n\n请生成报告的主标题、副标题、Hero 区块和标签。只输出 JSON。"

    result = await call_llm(system, user)
    return result


async def generate_predictions(
    stats_input: str,
    report_type: str,
) -> list[dict]:
    """Generate predictions about the group/relationship future.

    Returns list of {"id": "...", "title": "...", "body": "...", "probability": "高/中/低"}
    """
    system = PREDICTIONS_SYSTEM
    user = f"{stats_input}\n\n请生成 3 条有趣预测。只输出 JSON。"

    result = await call_llm(system, user)
    return result.get("predictions", [])


# ── Multi-Call Orchestrator ────────────────────────────────────

async def call_llm_multi(
    system_prompt: str,
    user_message: str,
    participants: list[dict],
    message_samples: list[dict],
    stats_input: str,
    report_type: str,
    progress_callback=None,
) -> dict:
    """Orchestrate multiple targeted LLM calls and assemble the result.

    Each sub-call has a focused task with relevant data, producing
    higher-quality output than a single monolithic prompt.
    """
    async def _run_with_progress(name: str, coro):
        if progress_callback:
            await progress_callback({"step": name, "status": "started"})
        try:
            result = await coro
            if progress_callback:
                await progress_callback({"step": name, "status": "done"})
            return result
        except Exception as e:
            if progress_callback:
                await progress_callback({"step": name, "status": "error", "error": str(e)})
            raise

    # Run independent calls in parallel
    results = {}

    # Call 1: Hero + Tags + Title (needs stats overview)
    hero_result = await _run_with_progress(
        "hero", generate_hero_and_tags(stats_input, report_type)
    )
    results.update(hero_result)

    # Call 2 & 3: Participants & Quotes (independent, can run in parallel)
    participant_future = _run_with_progress(
        "participants",
        analyze_participants(participants, message_samples, report_type),
    )
    quotes_future = _run_with_progress(
        "quotes",
        extract_quotes(message_samples, report_type),
    )

    participant_roasts, quotes = await asyncio.gather(participant_future, quotes_future)
    results["participant_roasts"] = participant_roasts
    results["quotes"] = quotes

    # Call 4: Sections (depends on having full stats)
    sections = await _run_with_progress(
        "sections",
        generate_sections(stats_input, report_type),
    )
    results["sections"] = sections

    # Call 5: Predictions
    predictions = await _run_with_progress(
        "predictions",
        generate_predictions(stats_input, report_type),
    )
    results["predictions_content"] = predictions

    # Call 6: Chat DNA text (short, focused)
    dna_text = await _run_with_progress(
        "chat_dna",
        _generate_chat_dna(stats_input, report_type),
    )
    results["chat_dna_text"] = dna_text

    # Generate share block
    results["share"] = _build_share_block(hero_result, report_type)

    return results


async def _generate_chat_dna(stats_input: str, report_type: str) -> str:
    """Generate the chat DNA paragraph (Spotify Wrapped style)."""
    system = CHAT_DNA_SYSTEM
    prefix = "群聊" if report_type == "group_roast" else "关系"
    user = f"{stats_input}\n\n请为这个{prefix}写一段150字的基因总结。只输出 JSON。"

    result = await call_llm(system, user)
    return result.get("dna_text", "")


def _build_share_block(hero_result: dict, report_type: str) -> dict:
    """Build share block from hero data."""
    hook = hero_result.get("tagline", "来测测你的聊天画像")[:15]
    return {
        "hook": hook,
        "watermark": "赛博判官生成",
    }


# ── Prompt Templates (targeted per call type) ────────────────────

PARTICIPANTS_SYSTEM = """你是一个名为「赛博判官」的群聊分析师。你的任务是根据成员的统计数据和真实发言样本，为每位成员生成锐评和性格标签。

## 要求
- 锐评要在25字以内，幽默有梗，一针见血
- 性格标签要基于他的真实发言风格（用词习惯、表情使用、活跃时间等）
- 锐评要引用或暗指他的实际发言内容，让人一看就知道说的是他
- 不要人身攻击，保持轻松调侃
- 每个成员的锐评必须不同，体现个性化

## 输出格式
{"participants": [{"name": "成员名", "roast": "25字锐评", "personality": "性格标签(5-10字)"}]}"""

QUOTES_SYSTEM = """你是一个群聊金句猎人。从聊天记录中挑选 3-5 条最有代表性、最幽默、或最有记忆点的真实发言作为"金句"。

## 挑选标准
- 必须是聊天记录中真实存在的内容，不能编造
- 优先选择有梗、好笑、或能体现群聊氛围的发言
- 金句要在30字以内，太长的可以截取精华部分
- 配上一句幽默点评（25字以内）
- icon 从以下选: sparkles（金句）, flame（火爆）, zap（犀利）, heart（暖心）, star（名场面）

## 输出格式
{"quotes": [{"speaker": "发言人", "text": "原话(30字内)", "comment": "幽默点评(25字内)", "icon": "sparkles"}]}"""

QUOTES_SYSTEM_RELATIONSHIP = """你是一个关系金句猎人。从两人的聊天记录中挑选 3-5 条最能体现两人关系特点的真实发言。

## 挑选标准
- 必须是聊天记录中真实存在的内容，不能编造
- 优先选择体现默契、关心、或两人独特互动模式的发言
- icon 从以下选: heart（暖心）, sparkles（默契）, star（名场面）, message-circle（经典）, sun（温暖）

## 输出格式
{"quotes": [{"speaker": "发言人", "text": "原话(30字内)", "comment": "点评(25字内)", "icon": "heart"}]}"""

SECTIONS_SYSTEM_GROUP = """你是一个群聊报告撰写 AI。根据提供的统计数据，为每个报告板块生成一句话总结（body 字段）。

## 集成参考项目能力
- AnnualReport/WeFlow: 年度总览、峰值日期、月份高峰，用在 monthly/chat-dna/summary 中
- WechatVisualization: 词汇特异性、共同高频词，用在 specificity/keywords 中
- chat-analytics/echotrace: 消息类型、链接、撤回、红包、互动矩阵，用在 msg-types/links/initiative/timeline 中
- whatsapp-wrapped-v3/welink: 作息、聊天基因、个性勋章，用在 chronotype/chat-dna/badges 中
- 不要新增 section id，不要拉长报告；把新洞察揉进已有 section 的 body

## 板块列表与要求
- summary: 180-240字的群聊氛围锐评，要有洞察力，必须引用2-3个具体数字
- dragon: 一句话总结龙王榜（20字）
- heatmap: 一句话总结活跃时段特征
- keywords: 一句话总结高频词汇
- msg-types: 一句话总结消息类型分布
- specificity: 一句话总结每个人的口头禅特点
- chronotype: 一句话总结成员的作息模式
- sentiment: 一句话总结群聊情绪基调
- radar: 一句话总结群聊人格雷达
- emoji: 一句话总结表情包偏好
- monthly: 一句话总结月度活跃趋势
- initiative: 一句话总结话题发起模式
- links: 一句话总结分享习惯
- timeline: 一句话总结关键时刻
- badges: 一句话总结勋章分布

## 输出格式
{"sections": [{"id": "...", "heading": "...", "body": "一句话总结"}]}

注意：body 字段必须有实质内容，不能只是"暂无数据"。普通板块控制在60字以内，summary/chat-dna可以更长。"""

SECTIONS_SYSTEM_RELATIONSHIP = """你是一个关系报告撰写 AI。根据提供的统计数据，为每个报告板块生成总结文案。

## 集成参考项目能力
- 使用互动矩阵判断谁更常接话，而不是只看消息数
- 使用共同词汇、表情共性、深夜比例、回复节奏判断关系模式
- 使用峰值日期、最长断联、关系里程碑解释关系变化
- 不要新增 section id，不要拉长报告；把新洞察揉进已有 section 的 body

## 板块列表与要求
- relationship-summary: 180-240字的关系定性分析，必须引用2-3个具体数字
- relationship-map: 一句话总结谁更主动
- relationship-keywords: 一句话总结两人的高频暗号
- commonality: 一句话总结两人的共享词汇
- relationship-timeline: 一句话总结关系升温过程
- relationship-radar: 一句话总结相处模式
- sentiment: 一句话总结聊天情绪

## 输出格式
{"sections": [{"id": "...", "heading": "...", "body": "一句话总结"}]}

普通板块控制在60字以内，relationship-summary/chat-dna可以更长。"""

HERO_SYSTEM_GROUP = """你是一个群聊锐评标题生成 AI。根据群聊统计数据，生成有冲击力的报告标题和 Hero 区块。

## 要求
- title: 15字以内，有冲击力，让人想点进来看
- tagline: 25字以内，金句概括群聊本质
- hero.visual: 一个代表字（单个汉字），如"判""水""卷""燃"
- hero.kicker: 5-8字的群聊人格标签
- hero.quote: 30字以内的锐评金句，要有洞察力
- tags: 3-5个标签，每个3-6字

## 输出格式
{"title": "...", "tagline": "...", "hero": {"kicker": "...", "quote": "...", "visual": "..."}, "tags": ["..."]}"""

HERO_SYSTEM_RELATIONSHIP = """你是一个关系报告标题生成 AI。根据两人聊天统计数据，生成有温度的报告标题和 Hero 区块。

## 要求
- title: 15字以内，有温度有悬念
- tagline: 25字以内，金句概括关系本质
- hero.visual: 一个代表字（单个汉字），如"双""默""暖""熟"
- hero.kicker: 5-8字的关系标签
- hero.quote: 30字以内的关系锐评金句
- tags: 3-5个标签

## 输出格式
{"title": "...", "tagline": "...", "hero": {"kicker": "...", "quote": "...", "visual": "..."}, "tags": ["..."]}"""

PREDICTIONS_SYSTEM = """你是一个赛博占卜 AI。根据群聊/关系的统计数据和趋势，生成 3 条有趣但不严肃的预测。

## 要求
- 每条预测要有标题（10字以内）和内容（30字以内）
- probability 从 "高""中""低" 中选择
- 预测要有趣但不冒犯，必须基于具体数据趋势（活跃时段、月度峰值、互动矩阵、共同词、作息）
- 风格: 像星座运势一样好玩，但要基于真实数据

## 输出格式
{"predictions": [{"id": "p1", "title": "...", "body": "...", "probability": "高"}]}"""

CHAT_DNA_SYSTEM = """你是一个数据叙事 AI。根据聊天统计数据，写一段150字左右的"基因报告"，类似 Spotify Wrapped 风格——用数据讲故事。

## 要求
- 把冷冰冰的数字讲成有趣的故事
- 可以用"你们的聊天基因里写着..."这类表达
- 提到具体的数字（消息量、活跃时段、高频词、峰值日期、夜聊比例、龙王/主动者等）
- 150字左右，有节奏感

## 输出格式
{"dna_text": "150字的基因报告"}"""


# ── Rich LLM Input Builder (for single-call fallback) ────────────

def build_llm_input(
    report_type: str,
    participants: list[dict],
    keywords: list[dict],
    emojis: list[dict],
    timeline: list[dict],
    total_messages: int,
    active_days: int,
    top_messages: list[dict],
    chat_dna: dict | None = None,
    chronotypes: list[dict] | None = None,
    sentiment: dict | None = None,
    monthly_activity: list[dict] | None = None,
    initiative_scores: list[dict] | None = None,
    message_type_breakdown: list[dict] | None = None,
    word_specificity: list[dict] | None = None,
    word_commonality: list[dict] | None = None,
    link_stats: list[dict] | None = None,
    personality_badges: list[dict] | None = None,
    hourly_distribution: list[dict] | None = None,
    weekday_distribution: list[dict] | None = None,
    yearly_monthly: list[dict] | None = None,
    interaction_matrix: list[dict] | None = None,
    at_mentions: list[dict] | None = None,
    famous_quotes: list[dict] | None = None,
    peak_day: dict | None = None,
    annual_summary: dict | None = None,
    recall_stats: dict | None = None,
    red_packet_overview: dict | None = None,
) -> str:
    """Build structured LLM input from ALL computed statistics."""

    lines = [
        f"## 报告类型: {'群聊锐评' if report_type == 'group_roast' else '双人关系锐评'}",
        f"## 基础数据: 共{total_messages}条消息, 跨越{active_days}个活跃日",
    ]

    if chat_dna:
        lines += [
            "",
            "## 群聊基因数据 (Chat DNA):",
            f"- 总消息: {chat_dna.get('total_messages', 0)}",
            f"- 总字数: {chat_dna.get('total_words', 0)}",
            f"- 活跃天数: {chat_dna.get('active_days', 0)}",
            f"- 跨越多个月: {chat_dna.get('active_months', 0)}",
            f"- 时间跨度: {chat_dna.get('date_range_days', 0)}天",
            f"- 起止日期: {chat_dna.get('first_date', '')} ~ {chat_dna.get('last_date', '')}",
            f"- 黄金时段: {chat_dna.get('top_hour', 0)}点",
            f"- 最爱星期几: {_day_name(chat_dna.get('top_day', 0))}",
            f"- 日均消息: {chat_dna.get('avg_daily_messages', 0)}条",
            f"- 深夜占比: {chat_dna.get('late_night_ratio', 0)}%",
            f"- 最爱表情: {chat_dna.get('top_emoji', '')}",
            f"- 高频词TOP1: {chat_dna.get('top_word', '')}",
        ]

    lines += [
        "",
        "## 参与成员统计:",
    ]
    for p in participants[:10]:
        lines.append(
            f"- {p['name']}: {p['message_count']}条消息, {p['character_count']}字, "
            f"表情{p['emoji_count']}次, 图片{p.get('image_count',0)}次, 平均{p['average_length']}字/条"
        )

    if message_type_breakdown:
        lines += ["", "## 消息类型分布:"]
        for mt in message_type_breakdown:
            lines.append(f"- {mt['label']}: {mt['count']}条 ({mt['percentage']}%)")

    if word_specificity:
        lines += ["", "## 谁最爱说什么 (词汇特异性):"]
        for ws in word_specificity[:12]:
            specificity = ws['specificity']
            direction = "最常说" if specificity > 0 else "几乎不说"
            lines.append(f"- [{ws['sender']}] {direction}「{ws['word']}」(特异性:{specificity})")

    if word_commonality:
        lines += ["", "## 两人共同词汇:"]
        for wc in word_commonality[:10]:
            lines.append(f"- 「{wc['word']}」 A说了{wc['count_a']}次, B说了{wc['count_b']}次 (共性值:{wc['commonality']})")

    if chronotypes:
        lines += ["", "## 作息鉴定:"]
        for ch in chronotypes[:8]:
            lines.append(f"- {ch['name']}: {ch['label']} (高峰{ch['peak_hour']}点, 深夜{ch['night_ratio']}%, 早晨{ch['morning_ratio']}%)")

    if sentiment:
        lines += ["", "## 情绪分析:",
                  f"- 积极词占比: {sentiment.get('positive_ratio', 0)}%",
                  f"- 中性词占比: {sentiment.get('neutral_ratio', 0)}%",
                  f"- 消极词占比: {sentiment.get('negative_ratio', 0)}%",
                  f"- 整体判断: {sentiment.get('label', '')}"]

    if monthly_activity:
        lines += ["", "## 月度活跃趋势:"]
        for ma in monthly_activity[-12:]:
            lines.append(f"- {ma['label']}: {ma['count']}条消息")

    if annual_summary:
        lines += [
            "",
            "## 年度总览:",
            f"- 年份: {annual_summary.get('year', '')}",
            f"- 总消息: {annual_summary.get('total_messages', 0)}",
            f"- 总联系人/成员: {annual_summary.get('total_friends', 0)}",
            f"- 首末日期: {annual_summary.get('first_date', '')} ~ {annual_summary.get('last_date', '')}",
            f"- 夜聊王: {annual_summary.get('night_king', '')} ({annual_summary.get('night_king_count', 0)}条凌晨消息)",
            f"- 年度主角: {'、'.join(annual_summary.get('top_friends', [])[:3])}",
        ]

    if peak_day:
        lines += [
            "",
            "## 峰值日期:",
            f"- 单日最高: {peak_day.get('date', '')}, {peak_day.get('count', 0)}条消息, 主力: {peak_day.get('top_sender', '')}",
        ]

    if hourly_distribution:
        top_hours = sorted(hourly_distribution, key=lambda h: h.get("count", 0), reverse=True)[:5]
        lines += ["", "## 24小时活跃分布 TOP:"]
        for h in top_hours:
            lines.append(f"- {h.get('hour', 0)}点: {h.get('count', 0)}条 ({h.get('pct', 0)}%)")

    if weekday_distribution:
        lines += ["", "## 星期活跃分布:"]
        for d in weekday_distribution:
            lines.append(f"- {d.get('label', '')}: {d.get('count', 0)}条 ({d.get('pct', 0)}%)")

    if yearly_monthly:
        top_months = sorted(yearly_monthly, key=lambda m: m.get("count", 0), reverse=True)[:4]
        lines += ["", "## 年内月份高峰:"]
        for m in top_months:
            lines.append(f"- {m.get('label', '')}: {m.get('count', 0)}条 ({m.get('pct', 0)}%)")

    if initiative_scores:
        lines += ["", "## 话题发起者排名:"]
        for ini in initiative_scores[:6]:
            lines.append(f"- {ini['name']}: 发起{ini['initiations']}次 (得分{ini['score']}) - {ini['label']}")

    if interaction_matrix:
        lines += ["", "## 互动矩阵 TOP:"]
        for edge in interaction_matrix[:10]:
            lines.append(f"- {edge.get('from', '')} → {edge.get('to', '')}: {edge.get('count', 0)}次快速接话")

    if at_mentions:
        lines += ["", "## @提及统计:"]
        for item in at_mentions[:8]:
            lines.append(f"- @{item.get('name', '')}: {item.get('count', 0)}次, 常被{item.get('top_mentioner', '')}提到")

    if link_stats:
        lines += ["", "## 最爱分享的链接:"]
        for ls in link_stats[:6]:
            lines.append(f"- {ls['domain']}: {ls['count']}次 (主力:{ls['top_sharer']})")

    if personality_badges:
        lines += ["", "## 已获得的勋章:"]
        for pb in personality_badges:
            lines.append(f"- {pb['awarded_to']} 获得「{pb['name']}」{pb['icon']}: {pb['description']}")

    if red_packet_overview and red_packet_overview.get("total", 0):
        lines += [
            "",
            "## 红包/转账概览:",
            f"- 总数: {red_packet_overview.get('total', 0)}, 主力: {red_packet_overview.get('top_sender', '')} ({red_packet_overview.get('top_count', 0)}次)",
        ]

    if recall_stats and recall_stats.get("total_recalls", 0):
        lines += [
            "",
            "## 撤回统计:",
            f"- 总撤回: {recall_stats.get('total_recalls', 0)}, 撤回主力: {recall_stats.get('top_recaller', '')} ({recall_stats.get('top_count', 0)}次)",
        ]

    lines += [
        "",
        "## 高频关键词:",
    ]
    for k in keywords[:20]:
        lines.append(f"- {k['word']} (出现{k['count']}次) [{k.get('tone','')}]")

    lines += [
        "",
        "## 常用表情包:",
    ]
    for e in emojis[:8]:
        lines.append(f"- {e['label']} (使用{e['value']}次, 主力:{e.get('owner','未知')})")

    lines += [
        "",
        "## 关键时刻:",
    ]
    for t in timeline[:7]:
        lines.append(f"- [{t['time']}] {t['title']}: {t['body']}")

    if famous_quotes:
        lines += [
            "",
            "## 算法筛出的名场面候选（可供金句板块参考，但最终 quotes 必须来自真实聊天样本）:",
        ]
        for q in famous_quotes[:8]:
            lines.append(f"- [{q.get('ts', '')[:16]}] {q.get('sender', '')}: 「{q.get('content', '')[:80]}」(score={q.get('score', 0)})")

    lines += [
        "",
        "## 消息样本（真实聊天内容，请仔细阅读以理解每个人的说话风格和群聊氛围）:",
    ]
    for m in top_messages[:200]:
        ts = (m.get('ts', '') or '')[:16]
        lines.append(f"[{ts}] {m['sender']}: {m['content'][:120]}")

    return "\n".join(lines)


def _day_name(day: int) -> str:
    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return days[day] if 0 <= day <= 6 else str(day)
