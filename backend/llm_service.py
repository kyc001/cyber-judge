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
from pathlib import Path
from typing import Optional

import httpx

if os.environ.get("CYBER_JUDGE_DESKTOP") != "1":
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent / ".env")
        load_dotenv()
    except Exception:
        pass

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
MAX_OUTPUT_TOKENS = int(os.environ.get("LLM_MAX_OUTPUT_TOKENS", "8192"))

# Multi-call mode: split into targeted sub-calls (better quality, shows progress)
USE_MULTI_CALL = os.environ.get("LLM_MULTI_CALL", "true").lower() == "true"

PROVIDER_PRESETS = {
    "deepseek": {
        "label": "DeepSeek",
        "api_base": "https://api.deepseek.com",
        "models": ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-v4-pro",
    },
    "openai": {
        "label": "OpenAI",
        "api_base": "https://api.openai.com/v1",
        "models": [
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gpt-5.2",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
        ],
        "default_model": "gpt-5.4-mini",
    },
    "qwen": {
        "label": "通义千问",
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": [
            "qwen3.7-max",
            "qwen3.6-plus",
            "qwen3.6-flash",
            "qwen3.5-plus",
            "qwen3.5-flash",
            "qwen-plus",
            "qwen-plus-latest",
            "qwen-max",
            "qwen-max-latest",
            "qwen-turbo",
            "qwen-turbo-latest",
        ],
        "default_model": "qwen3.6-plus",
    },
}


def _app_data_dir() -> Path:
    root = os.environ.get("CYBER_JUDGE_APP_DATA", "").strip()
    if root:
        path = Path(root)
    elif os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(base) / "CyberJudge"
    else:
        path = Path.home() / ".cyber-judge"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config_path() -> Path:
    return _app_data_dir() / "llm_config.json"


def _allow_env_config() -> bool:
    return os.environ.get("CYBER_JUDGE_DESKTOP") != "1"


def _normalise_provider(provider: str | None) -> str:
    provider_id = (provider or "").strip().lower()
    return provider_id if provider_id in PROVIDER_PRESETS else "deepseek"


def _normalise_model(provider: str, model: str | None) -> str:
    preset = PROVIDER_PRESETS[provider]
    model_name = (model or "").strip()
    return model_name if model_name in preset["models"] else preset["default_model"]


def _is_real_key(value: str | None) -> bool:
    key = (value or "").strip()
    return bool(key) and key.lower() not in {"your-api-key", "your-fallback-key", "sk-xxx", "sk-"}


def _read_saved_config() -> dict:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_saved_config(data: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def _provider_options() -> list[dict]:
    return [
        {
            "id": provider,
            "label": preset["label"],
            "models": preset["models"],
            "default_model": preset["default_model"],
        }
        for provider, preset in PROVIDER_PRESETS.items()
    ]


def _saved_api_keys(saved: dict) -> dict[str, str]:
    keys = saved.get("api_keys")
    if isinstance(keys, dict):
        result = {str(k): str(v) for k, v in keys.items() if _is_real_key(str(v))}
    else:
        result = {}
    legacy_key = saved.get("api_key")
    legacy_provider = _normalise_provider(str(saved.get("provider", "")))
    if _is_real_key(str(legacy_key or "")) and legacy_provider not in result:
        result[legacy_provider] = str(legacy_key).strip()
    return result


def _mask_key(key: str) -> str:
    key = key.strip()
    if not key:
        return ""
    return key[-4:] if len(key) > 4 else key


def get_llm_config_for_api() -> dict:
    """Return frontend-safe LLM settings. The API key is never returned."""
    saved = _read_saved_config()
    env_enabled = _allow_env_config()
    provider = _normalise_provider(str(saved.get("provider") or (LLM_PROVIDER if env_enabled else "deepseek")))
    model = _normalise_model(provider, str(saved.get("model") or (LLM_MODEL if env_enabled else "")))
    keys = _saved_api_keys(saved)
    saved_key = keys.get(provider, "")
    env_key = (
        LLM_API_KEY
        if env_enabled and _normalise_provider(LLM_PROVIDER) == provider and _is_real_key(LLM_API_KEY)
        else ""
    )
    key = saved_key or env_key
    provider_key_state = {
        provider_id: {
            "has_api_key": bool(keys.get(provider_id)),
            "api_key_tail": _mask_key(keys.get(provider_id, "")),
        }
        for provider_id in PROVIDER_PRESETS
    }
    return {
        "provider": provider,
        "model": model,
        "has_api_key": bool(key),
        "api_key_tail": _mask_key(key),
        "provider_keys": provider_key_state,
        "providers": _provider_options(),
        "source": "local" if saved_key else ("environment" if env_key else "missing"),
    }


def save_llm_config_from_api(payload: dict) -> dict:
    provider = _normalise_provider(str(payload.get("provider") or "deepseek"))
    model = _normalise_model(provider, str(payload.get("model") or ""))
    saved = _read_saved_config()
    keys = _saved_api_keys(saved)

    if payload.get("clear_api_key"):
        keys.pop(provider, None)
    elif "api_key" in payload:
        api_key = str(payload.get("api_key") or "").strip()
        if api_key:
            keys[provider] = api_key

    _write_saved_config({
        "provider": provider,
        "model": model,
        "api_keys": keys,
    })
    return get_llm_config_for_api()


def _resolve_primary_config(payload: dict | None = None) -> dict:
    payload = payload or {}
    saved = _read_saved_config()
    keys = _saved_api_keys(saved)
    env_enabled = _allow_env_config()
    provider = _normalise_provider(str(payload.get("provider") or saved.get("provider") or (LLM_PROVIDER if env_enabled else "deepseek")))
    model = _normalise_model(provider, str(payload.get("model") or saved.get("model") or (LLM_MODEL if env_enabled else "")))
    payload_key = str(payload.get("api_key") or "").strip()
    saved_key = keys.get(provider, "")
    env_key = (
        LLM_API_KEY
        if env_enabled and _normalise_provider(LLM_PROVIDER) == provider and _is_real_key(LLM_API_KEY)
        else ""
    )
    api_base = PROVIDER_PRESETS[provider]["api_base"]
    if env_enabled and not saved and not payload and LLM_API_BASE.strip():
        api_base = LLM_API_BASE.strip()
    return {
        "provider": provider,
        "api_key": payload_key or saved_key or env_key,
        "api_base": api_base,
        "model": model,
        "timeout_seconds": TIMEOUT,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }


async def test_llm_config_from_api(payload: dict) -> dict:
    config = _resolve_primary_config(payload)
    if not _is_real_key(config["api_key"]):
        raise ValueError("请先填写 API Key")
    client = LLMClient(
        provider=config["provider"],
        api_key=config["api_key"],
        api_base=config["api_base"],
        model=config["model"],
        timeout=30,
        max_tokens=96,
    )
    raw = await client.chat(
        "你是 Cyber Judge 的模型连通性检查器，只能输出 JSON。",
        '返回 {"ok": true, "message": "ready"}，不要输出额外文字。',
    )
    data = _extract_json(raw)
    return {
        "ok": bool(data.get("ok", True)),
        "provider": config["provider"],
        "model": config["model"],
        "message": str(data.get("message") or "ready"),
    }


# ── LLM Client ───────────────────────────────────────────────────

class LLMClient:
    """OpenAI-compatible chat completion client with JSON mode support."""

    def __init__(
        self,
        provider: str,
        api_key: str,
        api_base: str,
        model: str,
        timeout: int = TIMEOUT,
        max_tokens: int = MAX_OUTPUT_TOKENS,
    ):
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

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
            "max_tokens": self.max_tokens,
            "temperature": 0.8,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.api_base}/chat/completions"
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
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
            "max_tokens": self.max_tokens,
            "temperature": 0.8,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.api_base}/chat/completions"
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


def _get_primary_client() -> LLMClient:
    """Build the primary LLM client from frontend-saved config or env fallback."""
    config = _resolve_primary_config()
    return LLMClient(
        provider=config["provider"],
        api_key=config["api_key"],
        api_base=config["api_base"],
        model=config["model"],
        timeout=config["timeout_seconds"],
        max_tokens=config["max_output_tokens"],
    )

def _get_fallback_client() -> Optional[LLMClient]:
    """Build the fallback LLM client if a fallback API key is configured."""
    if not _allow_env_config():
        return None
    key = LLM_FALLBACK_API_KEY.strip()
    if _is_real_key(key):
        return LLMClient(provider=LLM_FALLBACK_PROVIDER, api_key=LLM_FALLBACK_API_KEY,
                         api_base=LLM_FALLBACK_API_BASE, model=LLM_FALLBACK_MODEL)
    return None


def _format_http_error(error: httpx.HTTPStatusError) -> str:
    try:
        body = error.response.text[:500]
    except Exception:
        body = ""
    return f"{error.response.status_code} from {error.request.url}: {body}"


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
        except httpx.HTTPStatusError as e:
            last_error = RuntimeError(_format_http_error(e))
            status = e.response.status_code
            if 400 <= status < 500 and status != 429:
                print(f"[LLM] Primary request rejected: {last_error}")
                break
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"[LLM] Primary attempt {attempt + 1} failed: {last_error}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
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
        except httpx.HTTPStatusError as e:
            last_error = RuntimeError(_format_http_error(e))
            print(f"[LLM] Fallback request rejected: {last_error}")
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
        except httpx.HTTPStatusError as e:
            last_error = RuntimeError(_format_http_error(e))
            status = e.response.status_code
            if 400 <= status < 500 and status != 429:
                print(f"[LLM] Raw primary request rejected: {last_error}")
                break
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"[LLM] Raw attempt {attempt + 1} failed: {last_error}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
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
        except httpx.HTTPStatusError as e:
            last_error = RuntimeError(_format_http_error(e))
            print(f"[LLM] Raw fallback request rejected: {last_error}")
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

    Returns list of {"id": "...", "title": "...", "body": "...", "probability": "中"}
    """
    system = PREDICTIONS_SYSTEM
    user = f"{stats_input}\n\n请生成 3 条有趣预测。只输出 JSON。"

    result = await call_llm(system, user)
    return result.get("predictions", [])


async def generate_content_highlights(
    highlight_windows: list[dict],
    report_type: str,
) -> list[dict]:
    """Generate content-level insights backed by real dialogue snippets."""
    if not highlight_windows:
        return []
    windows = highlight_windows[:12]
    batches = [windows[index:index + 4] for index in range(0, len(windows), 4)]
    tasks = [
        asyncio.create_task(_generate_content_highlight_batch(batch, report_type, batch_index * 4 + 1))
        for batch_index, batch in enumerate(batches)
    ]
    batch_results = await asyncio.gather(*tasks)
    merged = [item for batch in batch_results for item in batch]
    return _dedupe_content_highlights(merged, limit=5)


async def _generate_content_highlight_batch(
    windows: list[dict],
    report_type: str,
    start_index: int,
) -> list[dict]:
    lines = [
        "## 真实对话候选片段",
        "请只基于下面片段提取 1-2 个内容亮点。每个亮点必须有一个判断和 2-4 行证据。",
        "不要编造未出现的对话；可以概括关系模式、群聊梗、名场面、隐含情绪、反复出现的话题。",
        "",
    ]
    for idx, window in enumerate(windows, start=start_index):
        lines.append(f"### 片段 {idx}")
        for item in window.get("evidence", [])[:4]:
            ts = (item.get("ts", "") or "")[:16]
            sender = item.get("sender", "")
            content = item.get("content", item.get("text", ""))[:160]
            if content:
                lines.append(f"[{ts}] {sender}: {content}")
        lines.append("")

    system = CONTENT_HIGHLIGHTS_SYSTEM_RELATIONSHIP if report_type == "relationship" else CONTENT_HIGHLIGHTS_SYSTEM_GROUP
    user = "\n".join(lines) + "\n只输出 JSON。"
    result = await call_llm(system, user)
    return result.get("highlights", [])


def _dedupe_content_highlights(highlights: list[dict], limit: int = 5) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for item in highlights:
        evidence = item.get("evidence", [])
        evidence_text = ""
        if isinstance(evidence, list) and evidence:
            first = evidence[0] if isinstance(evidence[0], dict) else {}
            evidence_text = str(first.get("text") or first.get("content") or "")
        key_source = f"{item.get('title', '')}|{item.get('insight', '')[:50]}|{evidence_text[:50]}"
        key = re.sub(r"\s+", "", key_source).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        next_item = dict(item)
        next_item["id"] = f"h{len(deduped) + 1}"
        deduped.append(next_item)
        if len(deduped) >= limit:
            break
    return deduped


async def generate_insight_briefs(
    stats_input: str,
    report_type: str,
) -> dict:
    """Generate longer LLM-only briefs for the intermediate insight pages."""
    system = INSIGHT_BRIEFS_SYSTEM_RELATIONSHIP if report_type == "relationship" else INSIGHT_BRIEFS_SYSTEM_GROUP
    user = f"{stats_input}\n\n请为中间分析页生成 10 个页面锐评。只输出 JSON。"
    result = await call_llm(system, user)
    briefs = result.get("insight_briefs", {})
    return briefs if isinstance(briefs, dict) else {}


# ── Multi-Call Orchestrator ────────────────────────────────────

async def call_llm_multi(
    system_prompt: str,
    user_message: str,
    participants: list[dict],
    message_samples: list[dict],
    stats_input: str,
    report_type: str,
    highlight_windows: list[dict] | None = None,
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

    # All targeted calls are independent; run them together to minimize report latency.
    tasks = {
        "hero": asyncio.create_task(_run_with_progress("hero", generate_hero_and_tags(stats_input, report_type))),
        "participants": asyncio.create_task(
            _run_with_progress("participants", analyze_participants(participants, message_samples, report_type))
        ),
        "quotes": asyncio.create_task(_run_with_progress("quotes", extract_quotes(message_samples, report_type))),
        "sections": asyncio.create_task(_run_with_progress("sections", generate_sections(stats_input, report_type))),
        "predictions": asyncio.create_task(
            _run_with_progress("predictions", generate_predictions(stats_input, report_type))
        ),
        "content_highlights": asyncio.create_task(
            _run_with_progress(
                "content_highlights",
                generate_content_highlights(highlight_windows or [], report_type),
            )
        ),
        "insight_briefs": asyncio.create_task(
            _run_with_progress("insight_briefs", generate_insight_briefs(stats_input, report_type))
        ),
        "chat_dna": asyncio.create_task(_run_with_progress("chat_dna", _generate_chat_dna(stats_input, report_type))),
    }

    try:
        await asyncio.gather(*tasks.values())
    except Exception:
        for task in tasks.values():
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks.values(), return_exceptions=True)
        raise

    results = {}
    hero_result = tasks["hero"].result()
    results.update(hero_result)
    results["participant_roasts"] = tasks["participants"].result()
    results["quotes"] = tasks["quotes"].result()
    results["sections"] = tasks["sections"].result()
    results["predictions_content"] = tasks["predictions"].result()
    results["content_highlights"] = tasks["content_highlights"].result()
    results["insight_briefs"] = tasks["insight_briefs"].result()
    results["chat_dna_text"] = tasks["chat_dna"].result()

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
- WeFlow/chat review: 时间范围总览、峰值日期、月份高峰，用在 monthly/chat-dna/summary 中
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
- radar: 一句话总结群聊特征标签
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
- probability 固定填 "中"，不要在文案里展示强弱判断
- 预测要有趣但不冒犯，必须基于具体数据趋势（活跃时段、月度峰值、互动矩阵、共同词、作息）
- 风格: 像星座运势一样好玩，但要基于真实数据

## 输出格式
{"predictions": [{"id": "p1", "title": "...", "body": "...", "probability": "中"}]}"""

CONTENT_HIGHLIGHTS_SYSTEM_GROUP = """你是「赛博判官」的内容侦探，任务是从真实群聊片段里提取内容级亮点。
要求：
- 只使用用户提供的真实片段，不要编造新对话。
- 不要只复述统计数字，要解释这个片段说明了什么：群聊梗、关系模式、控场方式、吐槽风格、共同暗号、名场面。
- 语气可以锐评，但不要人身攻击。
- 每个 highlights 项必须有 2-4 行 evidence，evidence 的 text 必须来自输入片段，可以轻微截断但不能改写。
- title 12 字以内，insight 40-80 字，tag 选 content / roast / relationship / meme / warmth。

输出格式：
{"highlights":[{"id":"h1","title":"亮点标题","insight":"洞察点评","tag":"meme","evidence":[{"sender":"发言人","text":"原话","ts":"时间"}]}]}"""

CONTENT_HIGHLIGHTS_SYSTEM_RELATIONSHIP = """你是「赛博判官」的双人关系内容侦探，任务是从真实聊天片段里提取关系亮点。
要求：
- 只使用用户提供的真实片段，不要编造新对话。
- 优先解释主动关心、接话方式、共同语言、玩笑边界、情绪安抚、关系默契。
- 不要替用户定义现实关系，不要给现实关系建议。
- 每个 highlights 项必须有 2-4 行 evidence，evidence 的 text 必须来自输入片段，可以轻微截断但不能改写。
- title 12 字以内，insight 40-80 字，tag 选 relationship / warmth / meme / rhythm / content。

输出格式：
{"highlights":[{"id":"h1","title":"亮点标题","insight":"洞察点评","tag":"relationship","evidence":[{"sender":"发言人","text":"原话","ts":"时间"}]}]}"""

INSIGHT_BRIEFS_SYSTEM_GROUP = """你是「赛博判官」的中间分析页撰稿人。你的任务不是写最终报告，而是给每个中间主题页写一段更有信息量、更好玩的页面锐评。

必须只输出 JSON：
{"insight_briefs":{"summary":"...","time":"...","language":"...","emoji":"...","interaction":"...","emotion":"...","media":"...","relationship":"...","quotes":"...","predictions":"..."}}

要求：
- 10 个 key 必须齐全，不能新增 key。
- 每段 100-160 个中文字符，允许两句话，但不要写成列表。
- 必须基于输入里的统计和真实聊天片段写，至少自然带入 1-2 个具体数字、名字、词、表情或原话线索。
- 风格要像年度报告里的中间页旁白：有梗、有观察、有判断，但不是总结报告。
- 不要出现“AI”“大模型”“模型判断”等字样。
- 不要人身攻击，不要编造输入中没有出现的事实。"""

INSIGHT_BRIEFS_SYSTEM_RELATIONSHIP = """你是「赛博判官」的双人关系中间页撰稿人。你的任务不是写最终报告，而是给每个中间主题页写一段更有信息量、更好玩的页面锐评。

必须只输出 JSON：
{"insight_briefs":{"summary":"...","time":"...","language":"...","emoji":"...","interaction":"...","emotion":"...","media":"...","relationship":"...","quotes":"...","predictions":"..."}}

要求：
- 10 个 key 必须齐全，不能新增 key。
- 每段 100-160 个中文字符，允许两句话，但不要写成列表。
- 必须基于输入里的统计和真实聊天片段写，至少自然带入 1-2 个具体数字、名字、词、表情或原话线索。
- 风格要像年度报告里的中间页旁白：有观察、有温度，也可以轻微锐评。
- 不要出现“AI”“大模型”“模型判断”等字样。
- 不要替用户定义现实关系，不要给现实关系建议，不要编造输入中没有出现的事实。"""

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
    highlight_windows: list[dict] | None = None,
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
            "## 时间范围总览:",
            f"- 总消息: {annual_summary.get('total_messages', 0)}",
            f"- 总联系人/成员: {annual_summary.get('total_friends', 0)}",
            f"- 首末日期: {annual_summary.get('first_date', '')} ~ {annual_summary.get('last_date', '')}",
            f"- 夜聊王: {annual_summary.get('night_king', '')} ({annual_summary.get('night_king_count', 0)}条凌晨消息)",
            f"- 高频成员: {'、'.join(annual_summary.get('top_friends', [])[:3])}",
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
        lines += ["", "## 月份高峰:"]
        for m in top_months:
            lines.append(f"- {m.get('label', '')}: {m.get('count', 0)}条 ({m.get('pct', 0)}%)")

    if initiative_scores:
        lines += ["", "## 话题发起者排名:"]
        for ini in initiative_scores[:6]:
            lines.append(f"- {ini['name']}: 发起{ini['initiations']}次 - {ini['label']}")

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
            lines.append(f"- [{q.get('ts', '')[:16]}] {q.get('sender', '')}: 「{q.get('content', '')[:80]}」")

    if highlight_windows:
        lines += [
            "",
            "## 高信息密度对话窗口（用于内容亮点、关系判断和名场面，请优先阅读）:",
        ]
        for idx, window in enumerate(highlight_windows[:12], start=1):
            lines.append(f"### 片段 {idx}")
            for item in window.get("evidence", [])[:4]:
                ts = (item.get("ts", "") or "")[:16]
                content = item.get("content", item.get("text", ""))[:120]
                lines.append(f"[{ts}] {item.get('sender', '')}: {content}")

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
