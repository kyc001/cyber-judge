"""Client for WeFlow's local HTTP API service."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

DEFAULT_WEFLOW_BASE_URL = "http://127.0.0.1:5031"


class WeFlowClientError(RuntimeError):
    """Raised when the local WeFlow API cannot be reached or returns an error."""


def _normalize_base_url(base_url: str | None) -> str:
    value = (base_url or DEFAULT_WEFLOW_BASE_URL).strip().rstrip("/")
    return value or DEFAULT_WEFLOW_BASE_URL


def _auth_headers(access_token: str | None) -> dict[str, str]:
    token = (access_token or "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


async def check_weflow_status(base_url: str | None = None) -> dict[str, Any]:
    """Check whether WeFlow's local API service is reachable."""

    root = _normalize_base_url(base_url)
    last_error = ""
    try:
        async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
            for path in ("/health", ""):
                try:
                    response = await client.get(f"{root}{path}")
                    if response.status_code < 500:
                        return {
                            "running": True,
                            "base_url": root,
                            "status_code": response.status_code,
                            "detail": response.text[:200],
                        }
                    last_error = response.text[:200] or f"HTTP {response.status_code}"
                except httpx.HTTPError as exc:
                    last_error = str(exc)
    except httpx.HTTPError as exc:
        last_error = str(exc)

    return {
        "running": False,
        "base_url": root,
        "status_code": 0,
        "detail": last_error or "No response from WeFlow API",
    }


async def fetch_sessions(
    base_url: str | None = None,
    access_token: str | None = None,
    keyword: str = "",
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Fetch WeFlow sessions and normalize fields for the frontend selector."""

    root = _normalize_base_url(base_url)
    params: dict[str, Any] = {"limit": max(1, min(limit, 500))}
    if keyword.strip():
        params["keyword"] = keyword.strip()

    try:
        async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
            response = await client.get(
                f"{root}/api/v1/sessions",
                params=params,
                headers=_auth_headers(access_token),
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise WeFlowClientError(f"Failed to fetch WeFlow sessions: {exc}") from exc

    raw_sessions = data.get("sessions") if isinstance(data, dict) else data
    if not isinstance(raw_sessions, list):
        return []

    sessions: list[dict[str, Any]] = []
    for item in raw_sessions:
        if not isinstance(item, dict):
            continue
        session_id = (
            item.get("id")
            or item.get("sessionId")
            or item.get("session_id")
            or item.get("username")
            or item.get("talker")
            or item.get("talkerId")
        )
        if not session_id:
            continue
        sessions.append({
            "id": str(session_id),
            "name": item.get("name") or item.get("displayName") or item.get("remark") or str(session_id),
            "type": item.get("type") or item.get("sessionType") or "unknown",
            "message_count": item.get("messageCount") or item.get("message_count") or item.get("msgCount") or 0,
            "last_message_at": (
                item.get("lastMessageAt")
                or item.get("last_message_at")
                or item.get("lastTimestamp")
                or item.get("lastTime")
                or item.get("updateTime")
                or 0
            ),
        })
    return sessions


async def fetch_session_messages_chatlab(
    session_id: str,
    base_url: str | None = None,
    access_token: str | None = None,
    page_limit: int = 5000,
    max_messages: int = 50000,
    start_time: int | None = None,
    end_time: int | None = None,
) -> dict[str, Any]:
    """Fetch one session's messages in ChatLab format, following offsets when present."""

    root = _normalize_base_url(base_url)
    safe_limit = max(1, min(page_limit, 5000))
    safe_max = max(1, min(max_messages, 100000))
    offset = 0
    all_messages: list[dict[str, Any]] = []
    merged: dict[str, Any] = {
        "chatlab": {},
        "meta": {"name": session_id, "platform": "wechat"},
        "members": [],
        "messages": all_messages,
    }
    seen_member_ids: set[str] = set()

    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        while len(all_messages) < safe_max:
            params = {
                "talker": session_id,
                "limit": min(safe_limit, safe_max - len(all_messages)),
                "offset": offset,
                "format": "chatlab",
                "chatlab": "1",
            }
            if start_time:
                params["start"] = start_time
                params["startTime"] = start_time
                params["start_time"] = start_time
                params["since"] = start_time
            if end_time:
                params["end"] = end_time
                params["endTime"] = end_time
                params["end_time"] = end_time
            try:
                response = await client.get(
                    f"{root}/api/v1/messages",
                    params=params,
                    headers=_auth_headers(access_token),
                )
                if response.status_code == 404:
                    encoded = quote(session_id, safe="")
                    response = await client.get(
                        f"{root}/api/v1/sessions/{encoded}/messages",
                        params={
                            "limit": params["limit"],
                            "offset": offset,
                            "format": "chatlab",
                            "chatlab": "1",
                            **({"since": start_time} if start_time else {}),
                            **({"end": end_time} if end_time else {}),
                        },
                        headers=_auth_headers(access_token),
                    )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise WeFlowClientError(f"Failed to fetch WeFlow messages: {exc}") from exc

            if not isinstance(data, dict):
                break

            if data.get("chatlab") and not merged.get("chatlab"):
                merged["chatlab"] = data.get("chatlab") or {}
            if data.get("meta"):
                merged["meta"] = data.get("meta") or merged["meta"]

            members = data.get("members", [])
            if isinstance(members, list):
                for member in members:
                    if not isinstance(member, dict):
                        continue
                    member_id = str(member.get("platformId") or member.get("id") or member.get("accountName") or "")
                    if member_id and member_id not in seen_member_ids:
                        merged["members"].append(member)
                        seen_member_ids.add(member_id)

            page_messages = data.get("messages", [])
            if not isinstance(page_messages, list) or not page_messages:
                break
            all_messages.extend(page_messages)

            sync = data.get("sync") if isinstance(data.get("sync"), dict) else {}
            has_more = bool(sync.get("hasMore") or data.get("hasMore"))
            next_offset = sync.get("nextOffset") or data.get("nextOffset")
            if next_offset is not None:
                try:
                    offset = int(next_offset)
                except (TypeError, ValueError):
                    offset += len(page_messages)
            else:
                offset += len(page_messages)

            if not has_more and len(page_messages) < safe_limit:
                break

    return merged


async def fetch_session_messages_raw(
    session_id: str,
    base_url: str | None = None,
    access_token: str | None = None,
    page_limit: int = 5000,
    max_messages: int = 50000,
    start_time: int | None = None,
    end_time: int | None = None,
) -> dict[str, Any]:
    """Fetch one session's messages in WeFlow's raw JSON format."""

    root = _normalize_base_url(base_url)
    safe_limit = max(1, min(page_limit, 10000))
    safe_max = max(1, min(max_messages, 100000))
    offset = 0
    all_messages: list[dict[str, Any]] = []
    merged: dict[str, Any] = {
        "success": True,
        "talker": session_id,
        "messages": all_messages,
    }

    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        while len(all_messages) < safe_max:
            params = {
                "talker": session_id,
                "limit": min(safe_limit, safe_max - len(all_messages)),
                "offset": offset,
                "format": "json",
            }
            if start_time:
                params["start"] = start_time
                params["startTime"] = start_time
                params["start_time"] = start_time
                params["since"] = start_time
            if end_time:
                params["end"] = end_time
                params["endTime"] = end_time
                params["end_time"] = end_time
            try:
                response = await client.get(
                    f"{root}/api/v1/messages",
                    params=params,
                    headers=_auth_headers(access_token),
                )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise WeFlowClientError(f"Failed to fetch raw WeFlow messages: {exc}") from exc

            if not isinstance(data, dict):
                break
            page_messages = data.get("messages", [])
            if not isinstance(page_messages, list) or not page_messages:
                break
            all_messages.extend(page_messages)

            has_more = bool(data.get("hasMore"))
            next_offset = data.get("nextOffset")
            if next_offset is not None:
                try:
                    offset = int(next_offset)
                except (TypeError, ValueError):
                    offset += len(page_messages)
            else:
                offset += len(page_messages)

            if not has_more and len(page_messages) < safe_limit:
                break

    return merged
