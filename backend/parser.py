"""WeFlow JSON chat export parser.

Parses the WeFlow JSON export format into ChatMessage objects
matching the frontend contract. Handles text, image, emoji,
file, and system message types.
"""

from __future__ import annotations

import html
import json
import re
from models import ChatMessage

_URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _clean_url(value: str) -> str:
    return html.unescape(value).rstrip(".,;)")


def _direct_url(value: object) -> str:
    text = _clean_url(_as_text(value))
    return text if text.startswith(("http://", "https://")) else ""


def _extract_first_url(*values: object) -> str:
    for value in values:
        match = _URL_RE.search(_as_text(value))
        if match:
            return _clean_url(match.group(0))
    return ""


def _detect_message_type(local_type: int) -> str:
    """Map WeFlow localType integer to message type string."""

    type_map = {1: "text", 3: "image", 34: "image", 43: "image", 47: "emoji",
                49: "file", 50: "unknown", 10000: "system"}
    return type_map.get(local_type, "text")


def parse_weflow_json(text: str) -> list[ChatMessage]:
    """Parse WeFlow JSON export into structured ChatMessage list.
    Handles localType mapping: 1=text, 3/34/43=image, 47=emoji, 49=file, 10000=system.
    """
    data = json.loads(text)
    raw_msgs = data.get("messages", []) if isinstance(data, dict) else []

    messages: list[ChatMessage] = []
    for i, m in enumerate(raw_msgs):
        local_type = m.get("localType", 1)
        msg_type = _detect_message_type(local_type)
        if local_type == 10000:
            msg_type = "system"

        content = m.get("content", "") or ""
        meta = None
        if local_type == 47:
            sticker_md5 = m.get("emojiMd5", "")
            sticker_url = (
                _direct_url(m.get("emojiCdnUrl"))
                or _direct_url(m.get("source"))
                or _extract_first_url(m.get("content"), m.get("source"))
            )
            sticker_local_path = _as_text(m.get("emojiLocalPath"))
            label = m.get("emojiCaption", "") or "[表情包]"
            content = label
            meta = {"url": sticker_url, "caption": label, "md5": sticker_md5}
            if sticker_local_path:
                meta["local_path"] = sticker_local_path

        messages.append(ChatMessage(
            msg_id=str(m.get("localId", i)),
            sender=m.get("senderDisplayName", "") or m.get("senderUsername", ""),
            ts=m.get("formattedTime", "").replace(" ", "T") if m.get("formattedTime") else "",
            type=msg_type,
            content=content,
            meta=meta,
        ))
    return messages


def parse_and_validate(text: str) -> list[ChatMessage]:
    """Validate and parse WeFlow JSON text. Raises ValueError on invalid input."""
    try:
        json.loads(text.strip())
    except json.JSONDecodeError:
        raise ValueError("JSON格式解析失败，请上传WeFlow导出的JSON文件。")

    messages = parse_weflow_json(text)
    if not messages:
        raise ValueError("未能解析出消息，请检查JSON格式是否为WeFlow导出。")
    return messages
