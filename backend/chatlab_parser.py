"""ChatLab standard format parser.

WeFlow can expose messages through its local HTTP API in ChatLab format.
This parser converts that format into the Cyber Judge ChatMessage contract.
"""

from __future__ import annotations

from datetime import datetime
import html
import re
from typing import Any
import xml.etree.ElementTree as ET

from models import ChatMessage

_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_ID_CARD_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
_WX_ID_RE = re.compile(r"\b(?:wxid|gh|qkv|v1)_[A-Za-z0-9_-]+\b", re.IGNORECASE)
_XML_TAG_RE = re.compile(r"<[^>]+>")
_XML_NOISE_WORD_RE = re.compile(
    r"\b(?:template|fromusername|tousername|appmsg|msg|msgid|title|des|url|type|appid|sdkver|"
    r"thumburl|username|finderusername|objectid|objectnonceid|cdnthumburl|cdnmidimgurl)\b",
    re.IGNORECASE,
)


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _mask_sensitive_text(value: object) -> str:
    text = _as_text(value)
    text = _PHONE_RE.sub("phone****", text)
    text = _EMAIL_RE.sub("email****", text)
    text = _ID_CARD_RE.sub("id_card****", text)
    return text


def _strip_wechat_noise(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = _XML_TAG_RE.sub(" ", text)
    text = _WX_ID_RE.sub(" ", text)
    text = _XML_NOISE_WORD_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _find_xml_text(root: ET.Element, *names: str) -> str:
    targets = {name.lower() for name in names}
    for elem in root.iter():
        tag = elem.tag.split("}", 1)[-1].lower()
        if tag in targets and elem.text:
            value = _strip_wechat_noise(elem.text)
            if value:
                return value
    return ""


def _extract_xml_readable_text(value: object) -> str:
    raw = _as_text(value)
    if not raw or "<" not in raw or ">" not in raw:
        return _strip_wechat_noise(raw)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return _strip_wechat_noise(raw)
    parts = [
        _find_xml_text(root, "title"),
        _find_xml_text(root, "des", "description"),
        _find_xml_text(root, "content"),
    ]
    return " ".join(part for part in parts if part).strip()


def _format_timestamp(value: object) -> str:
    if isinstance(value, str) and "T" in value:
        return value
    try:
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%S")
    except (TypeError, ValueError, OSError):
        return ""


def _map_chatlab_type(value: object) -> str:
    if isinstance(value, str):
        normalized = value.lower()
        if normalized in {"text", "image", "emoji", "file", "link", "system", "red_packet", "transfer"}:
            return normalized
        if normalized in {"voice", "video"}:
            return "unknown"
    try:
        type_code = int(value)
    except (TypeError, ValueError):
        return "unknown"

    type_map = {
        0: "text",
        1: "image",
        2: "unknown",
        3: "unknown",
        4: "file",
        5: "emoji",
        7: "link",
        20: "red_packet",
        21: "transfer",
        80: "system",
        81: "system",
    }
    return type_map.get(type_code, "unknown")


def parse_chatlab_json(data: dict[str, Any]) -> list[ChatMessage]:
    """Parse ChatLab JSON into ChatMessage list."""

    raw_messages = data.get("messages", [])
    if not isinstance(raw_messages, list):
        return []

    messages: list[ChatMessage] = []
    for index, item in enumerate(raw_messages):
        if not isinstance(item, dict):
            continue

        msg_type = _map_chatlab_type(item.get("type"))
        sender = (
            _as_text(item.get("groupNickname"))
            or _as_text(item.get("accountName"))
            or _as_text(item.get("sender"))
            or "unknown"
        )
        readable_content = item.get("parsedContent") or item.get("displayContent") or item.get("content") or item.get("rawContent")
        content = _mask_sensitive_text(_extract_xml_readable_text(readable_content))
        if not content:
            content = f"[{msg_type}]"

        meta: dict[str, str | int | bool] = {}
        for source_key, meta_key in (
            ("sender", "sender_id"),
            ("accountName", "account_name"),
            ("groupNickname", "group_nickname"),
            ("mediaPath", "media_path"),
            ("platformMessageId", "platform_message_id"),
        ):
            value = item.get(source_key)
            if isinstance(value, (str, int, bool)) and value != "":
                meta[meta_key] = value

        messages.append(ChatMessage(
            msg_id=str(item.get("platformMessageId") or item.get("id") or index),
            sender=sender,
            ts=_format_timestamp(item.get("timestamp") or item.get("time")),
            type=msg_type,
            content=content,
            reply_to=_as_text(item.get("replyToMessageId")) or None,
            meta=meta or None,
        ))

    return messages
