"""WeFlow JSON chat export parser.

The parser converts WeFlow's raw JSON records into the project's
ChatMessage contract. It is intentionally defensive because real WeFlow
exports may vary slightly across versions and message types.
"""

from __future__ import annotations

from datetime import datetime
import html
import json
import re
from typing import Any
import xml.etree.ElementTree as ET

from models import ChatMessage

_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
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


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


def _mask_sensitive_text(value: object) -> str:
    """Mask common private identifiers before messages enter the stats pipeline."""

    text = _as_text(value)
    text = _PHONE_RE.sub("phone****", text)
    text = _EMAIL_RE.sub("email****", text)
    text = _ID_CARD_RE.sub("id_card****", text)
    return text


def _strip_wechat_noise(text: str) -> str:
    """Remove WeChat XML/template identifiers that would pollute word stats."""

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
    """Extract a human-readable title/description from WeChat XML-like content."""

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


def _format_timestamp(msg: dict[str, Any]) -> str:
    """Return an ISO-like timestamp using formattedTime, createTime, or timestamp."""

    formatted = _as_text(msg.get("formattedTime"))
    if formatted:
        return formatted.replace(" ", "T")

    for key in ("createTime", "timestamp"):
        raw = msg.get(key)
        if raw in (None, ""):
            continue
        try:
            timestamp = float(raw)
            if timestamp > 10_000_000_000:
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError, OSError):
            continue

    return ""


def _has_link(msg: dict[str, Any]) -> bool:
    return bool(
        _direct_url(msg.get("linkUrl"))
        or _extract_first_url(msg.get("content"), msg.get("source"), msg.get("xml"))
        or "link" in _as_text(msg.get("type")).lower()
        or "链接" in _as_text(msg.get("type"))
    )


def _detect_message_type(msg: dict[str, Any]) -> str:
    """Map WeFlow localType plus content clues to the project's MessageType."""

    local_type = _as_int(msg.get("localType"), 1)
    raw_type = _as_text(msg.get("type"))
    content = _as_text(msg.get("content"))

    if local_type == 10000:
        if "撤回" in content or "recalled" in content.lower():
            return "system"
        return "system"

    if "红包" in raw_type or "红包" in content:
        return "red_packet"
    if "转账" in raw_type or "转账" in content:
        return "transfer"

    if local_type == 1:
        return "link" if _has_link(msg) else "text"
    if local_type == 3:
        return "image"
    if local_type == 47:
        return "emoji"
    if local_type == 49:
        return "link" if _has_link(msg) else "file"

    # Voice/video are not part of the current ChatMessage union, so keep them
    # importable without pretending they are images.
    if local_type in (34, 43, 50):
        return "unknown"

    return "link" if _has_link(msg) else "unknown"


def _build_meta(msg: dict[str, Any], msg_type: str) -> dict[str, str | int | bool] | None:
    """Collect useful raw fields for later stats without exposing raw messages."""

    local_type = _as_int(msg.get("localType"), 1)
    meta: dict[str, str | int | bool] = {
        "local_type": local_type,
    }

    for source_key, meta_key in (
        ("platformMessageId", "platform_message_id"),
        ("source", "source"),
        ("senderUsername", "sender_username"),
        ("senderAvatarKey", "sender_avatar_key"),
    ):
        value = _as_text(msg.get(source_key))
        if value:
            meta[meta_key] = value

    if msg_type == "emoji":
        sticker_url = (
            _direct_url(msg.get("emojiCdnUrl"))
            or _direct_url(msg.get("source"))
            or _extract_first_url(msg.get("content"), msg.get("source"), msg.get("xml"))
        )
        sticker_md5 = _as_text(msg.get("emojiMd5"))
        sticker_caption = _as_text(msg.get("emojiCaption"))
        sticker_local_path = _as_text(msg.get("emojiLocalPath"))
        if sticker_url:
            meta["url"] = sticker_url
        if sticker_caption:
            meta["caption"] = sticker_caption
        if sticker_md5:
            meta["md5"] = sticker_md5
        if sticker_local_path:
            meta["local_path"] = sticker_local_path

    if msg_type == "link":
        link_url = _direct_url(msg.get("linkUrl")) or _extract_first_url(
            msg.get("content"), msg.get("source"), msg.get("xml")
        )
        link_title = _as_text(msg.get("linkTitle"))
        if link_url:
            meta["link_url"] = link_url
            meta["url"] = link_url
        if link_title:
            meta["link_title"] = link_title

    if msg_type == "file":
        file_name = _as_text(msg.get("fileName")) or _as_text(msg.get("fileNameMd5"))
        if file_name:
            meta["file_name"] = file_name

    return meta if len(meta) > 1 else None


def _message_content(msg: dict[str, Any], msg_type: str) -> str:
    """Build display/stat content for a normalized message."""

    readable_content = (
        msg.get("parsedContent")
        or msg.get("displayContent")
        or msg.get("content")
        or msg.get("rawContent")
    )

    if msg_type == "emoji":
        return _as_text(msg.get("emojiCaption")) or "[emoji]"

    if msg_type == "image":
        return _mask_sensitive_text(readable_content) or "[image]"

    if msg_type == "link":
        link_title = _as_text(msg.get("linkTitle"))
        link_url = _direct_url(msg.get("linkUrl")) or _extract_first_url(
            readable_content, msg.get("source"), msg.get("xml")
        )
        content = _mask_sensitive_text(_extract_xml_readable_text(readable_content))
        return content or link_title or link_url or "[link]"

    if msg_type == "file":
        return _mask_sensitive_text(_extract_xml_readable_text(readable_content)) or _as_text(msg.get("fileName")) or "[file]"

    if msg_type in ("red_packet", "transfer", "system", "unknown"):
        return _mask_sensitive_text(_extract_xml_readable_text(readable_content)) or f"[{msg_type}]"

    return _mask_sensitive_text(_extract_xml_readable_text(readable_content))


def parse_weflow_json(text: str) -> list[ChatMessage]:
    """Parse WeFlow JSON export into structured ChatMessage objects."""

    data = json.loads(text)
    raw_msgs = data.get("messages", []) if isinstance(data, dict) else []
    if not isinstance(raw_msgs, list):
        return []

    messages: list[ChatMessage] = []
    for i, raw_msg in enumerate(raw_msgs):
        if not isinstance(raw_msg, dict):
            continue

        msg: dict[str, Any] = raw_msg
        msg_type = _detect_message_type(msg)
        content = _message_content(msg, msg_type)
        sender = _as_text(msg.get("senderDisplayName")) or _as_text(msg.get("senderUsername")) or "unknown"

        messages.append(ChatMessage(
            msg_id=str(msg.get("localId") or msg.get("platformMessageId") or i),
            sender=sender,
            ts=_format_timestamp(msg),
            type=msg_type,
            content=content,
            reply_to=_as_text(msg.get("replyToMessageId")) or None,
            meta=_build_meta(msg, msg_type),
        ))

    return messages


def parse_and_validate(text: str) -> list[ChatMessage]:
    """Validate and parse WeFlow JSON text. Raises ValueError on invalid input."""

    try:
        json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON. Please upload a WeFlow JSON export file.") from exc

    messages = parse_weflow_json(text)
    if not messages:
        raise ValueError("No messages found. Please check whether this is a WeFlow JSON export.")
    return messages
