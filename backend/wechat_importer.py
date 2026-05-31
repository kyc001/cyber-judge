"""Adapter for importing chats from the bundled wechat-decrypt module."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent
BUNDLED_WECHAT_DECRYPT_DIR = BACKEND_DIR / "wechat_decrypt"
DEFAULT_IMPORT_DIR = BACKEND_DIR / "imported_chats"


@dataclass(frozen=True)
class WechatModules:
    export_all_chats: ModuleType
    mcp_server: ModuleType


def _project_dir() -> Path:
    return Path(os.environ.get("WECHAT_DECRYPT_PROJECT_DIR", str(BUNDLED_WECHAT_DECRYPT_DIR)))


def _code_dir() -> Path:
    configured = os.environ.get("WECHAT_DECRYPT_CODE_DIR", "").strip()
    if configured:
        return Path(configured)
    project_dir = _project_dir()
    if (project_dir / "main.py").exists():
        return project_dir
    return BUNDLED_WECHAT_DECRYPT_DIR


def _configure_wechat_project(project_dir: Path) -> None:
    os.environ["WECHAT_DECRYPT_APP_DIR"] = str(project_dir)


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _unload_wechat_decrypt_modules(code_dir: Path) -> None:
    removed = False
    for name, module in list(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        if _path_is_within(Path(module_file), code_dir):
            sys.modules.pop(name, None)
            removed = True
    if removed:
        importlib.invalidate_caches()


def _modules_need_refresh(code_dir: Path, project_dir: Path) -> bool:
    mcp_server = sys.modules.get("mcp_server")
    if mcp_server is None:
        return False

    module_file = getattr(mcp_server, "__file__", None)
    if module_file and not _path_is_within(Path(module_file), code_dir):
        return True

    expected_keys = str((project_dir / "all_keys.json").resolve())
    expected_decrypted = str((project_dir / "decrypted").resolve())
    loaded_keys = str(Path(getattr(mcp_server, "KEYS_FILE", "")).resolve())
    loaded_decrypted = str(Path(getattr(mcp_server, "DECRYPTED_DIR", "")).resolve())
    if loaded_keys != expected_keys or loaded_decrypted != expected_decrypted:
        return True

    keys_file = project_dir / "all_keys.json"
    if keys_file.exists() and not getattr(mcp_server, "MSG_DB_KEYS", []):
        return True

    return False


def _script_runner() -> list[str]:
    runner = os.environ.get("CYBER_JUDGE_SCRIPT_RUNNER", "").strip()
    if runner:
        return [runner]
    return [sys.executable]


def _desktop_log_path() -> Path | None:
    explicit = os.environ.get("CYBER_JUDGE_DESKTOP_LOG", "").strip()
    if explicit:
        return Path(explicit)
    if os.environ.get("CYBER_JUDGE_DESKTOP") != "1":
        return None
    root = os.environ.get("CYBER_JUDGE_APP_DATA", "").strip()
    if root:
        return Path(root) / "desktop.log"
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return Path(local_app_data) / "CyberJudge" / "desktop.log"
    return None


def _log_desktop_diagnostic(message: str) -> None:
    log_path = _desktop_log_path()
    if log_path is None:
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")
    except OSError:
        pass


def _session_db_candidates(project_dir: Path) -> list[Path]:
    return [
        project_dir / "decrypted" / "session" / "session.db",
        project_dir / "decrypted" / "_monitor_cache" / "session_session.db",
    ]


def get_wechat_prepare_status() -> dict[str, Any]:
    project_dir = _project_dir()
    session_db = next((path for path in _session_db_candidates(project_dir) if path.exists()), None)
    return {
        "project_dir": str(project_dir),
        "config_exists": (project_dir / "config.json").exists(),
        "keys_exists": (project_dir / "all_keys.json").exists(),
        "decrypted": session_db is not None,
        "session_db": str(session_db) if session_db else "",
    }


def prepare_wechat_data(*, force: bool = False) -> dict[str, Any]:
    """Run the bundled decrypt flow so Cyber Judge can list local WeChat chats."""
    project_dir = _project_dir()
    code_dir = _code_dir()
    _configure_wechat_project(project_dir)
    if not code_dir.exists():
        raise RuntimeError(f"未找到微信解密模块目录：{code_dir}")
    project_dir.mkdir(parents=True, exist_ok=True)
    if not project_dir.exists():
        raise RuntimeError(f"未找到微信解密模块目录：{project_dir}")

    before = get_wechat_prepare_status()
    if before["decrypted"] and not force:
        _unload_wechat_decrypt_modules(code_dir)
        return {**before, "ran": False, "message": "微信数据库已准备好"}

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("WECHAT_DECRYPT_NONINTERACTIVE", "1")
    env.setdefault("WECHAT_DECRYPT_APP_DIR", str(project_dir))
    timeout = int(os.environ.get("WECHAT_PREPARE_TIMEOUT_SECONDS", "600"))
    cmd = [*_script_runner(), str(code_dir / "main.py"), "decrypt"]
    result = subprocess.run(
        cmd,
        cwd=str(project_dir),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    tail = "\n".join(output.splitlines()[-40:])
    if result.returncode != 0:
        raise RuntimeError(
            "自动准备微信数据库失败。请确认微信已登录，并用管理员身份启动 Cyber Judge。\n"
            + tail
        )

    status = get_wechat_prepare_status()
    if not status["decrypted"]:
        raise RuntimeError(
            "解密命令已结束，但没有找到 decrypted/session/session.db。\n"
            + tail
        )
    _unload_wechat_decrypt_modules(code_dir)
    return {**status, "ran": True, "message": "微信数据库已准备好", "output_tail": tail}


def _load_modules() -> WechatModules:
    project_dir = _project_dir()
    code_dir = _code_dir()
    _configure_wechat_project(project_dir)
    if not code_dir.exists():
        raise RuntimeError(f"未找到微信解密项目目录：{code_dir}。请设置 WECHAT_DECRYPT_CODE_DIR。")
    project_dir.mkdir(parents=True, exist_ok=True)
    if not project_dir.exists():
        raise RuntimeError(
            f"未找到微信解密项目目录：{project_dir}。请设置 WECHAT_DECRYPT_PROJECT_DIR。"
        )
    if _modules_need_refresh(code_dir, project_dir):
        _unload_wechat_decrypt_modules(code_dir)

    code_text = str(code_dir)
    if code_text not in sys.path:
        sys.path.insert(0, code_text)
    try:
        export_all_chats = importlib.import_module("export_all_chats")
        mcp_server = importlib.import_module("mcp_server")
    except Exception as exc:
        _log_desktop_diagnostic(
            "wechat_importer failed to import bundled modules\n"
            f"code_dir={code_dir}\n"
            f"project_dir={project_dir}\n"
            + traceback.format_exc()
        )
        raise RuntimeError(
            "无法加载微信解密项目。请确认已安装其 requirements.txt，且 config.json 已配置/解密完成。"
        ) from exc
    return WechatModules(export_all_chats=export_all_chats, mcp_server=mcp_server)


def _parse_time(value: str | None, *, is_end: bool = False) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    formats = (
        ("%Y-%m-%d %H:%M:%S", False),
        ("%Y-%m-%d %H:%M", False),
        ("%Y-%m-%d", True),
    )
    for fmt, date_only in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if date_only and is_end:
                parsed = parsed.replace(hour=23, minute=59, second=59)
            return int(parsed.timestamp())
        except ValueError:
            pass
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"时间格式无效：{value}。支持 YYYY-MM-DD / YYYY-MM-DD HH:MM / Unix 时间戳。") from exc


def _session_db_path(modules: WechatModules) -> str:
    mcp_server = modules.mcp_server
    rel_key = os.path.join("session", "session.db")
    try:
        path = mcp_server._cache.get(rel_key)
    except Exception:
        path = None
    if path and os.path.exists(path):
        return path
    fallback = os.path.join(mcp_server.DECRYPTED_DIR, "session", "session.db")
    if os.path.exists(fallback):
        return fallback
    raise RuntimeError("未找到 session.db。请先在微信解密项目中完成数据库解密。")


def list_wechat_chats(
    *,
    query: str = "",
    kind: str = "all",
    limit: int = 50,
    start_time: str = "",
    end_time: str = "",
) -> dict[str, Any]:
    modules = _load_modules()
    export_all = modules.export_all_chats
    mcp_server = modules.mcp_server
    session_db = _session_db_path(modules)
    start_ts = _parse_time(start_time)
    end_ts = _parse_time(end_time, is_end=True)

    sessions = export_all._load_session_usernames(session_db)
    names = mcp_server.get_contact_names()
    contact_full = mcp_server.get_contact_full()
    rows = export_all._build_chat_rows(sessions, names, contact_full)

    allowed_kind = kind if kind in {"group", "single"} else "all"
    if allowed_kind != "all":
        rows = [row for row in rows if row.get("kind") == allowed_kind]

    needle = query.strip().lower()
    if needle:
        rows = [
            row for row in rows
            if needle in str(row.get("display_name", "")).lower()
            or needle in str(row.get("username", "")).lower()
            or needle in str(row.get("remark", "")).lower()
            or needle in str(row.get("nick_name", "")).lower()
        ]

    requested_limit = max(1, min(limit, 200))
    stats_limit = max(requested_limit, int(os.environ.get("WECHAT_CHAT_STATS_LIMIT", "500")))
    stats_rows = rows[: min(len(rows), stats_limit)]
    stats_by_username = {}
    if stats_rows:
        stats_by_username = export_all._collect_all_plan_stats(
            stats_rows,
            start_ts=start_ts,
            end_ts=end_ts,
            size_mode="estimate",
        )

    enriched_rows = []
    for row in stats_rows:
        stats = stats_by_username.get(row["username"], {})
        enriched_rows.append({
            "index": row["index"],
            "username": row["username"],
            "display_name": row["display_name"],
            "kind": row["kind"],
            "remark": row.get("remark", ""),
            "nick_name": row.get("nick_name", ""),
            "message_count": stats.get("message_count", 0),
            "first_time": stats.get("first_time", ""),
            "last_time": stats.get("last_time", ""),
            "size_status": stats.get("size_status", ""),
        })

    enriched_rows.sort(
        key=lambda chat: (
            int(chat["message_count"] or 0) > 0,
            str(chat.get("last_time") or ""),
            int(chat["message_count"] or 0),
        ),
        reverse=True,
    )
    chats = enriched_rows[:requested_limit]

    return {
        "project_dir": str(_project_dir()),
        "total": len(rows),
        "chats": chats,
    }


def export_wechat_chat(
    *,
    username: str,
    start_time: str = "",
    end_time: str = "",
    output_dir: str = "",
    incremental: bool = False,
) -> dict[str, Any]:
    modules = _load_modules()
    export_all = modules.export_all_chats
    names = modules.mcp_server.get_contact_names()
    start_ts = _parse_time(start_time)
    end_ts = _parse_time(end_time, is_end=True)
    if start_ts is not None and end_ts is not None and start_ts > end_ts:
        raise ValueError("开始时间不能晚于结束时间。")

    configured_dir = output_dir.strip() or os.environ.get("WECHAT_IMPORT_OUTPUT_DIR", str(DEFAULT_IMPORT_DIR))
    configured_dir = configured_dir.strip().strip('"').strip("'")
    target_dir = Path(configured_dir).expanduser()
    if not target_dir.is_absolute():
        target_dir = BACKEND_DIR / target_dir
    target_dir = target_dir.resolve()
    if target_dir.exists() and not target_dir.is_dir():
        raise ValueError(f"导出目录不能是文件：{target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    ok, total_count, new_count, error = export_all.export_one(
        username,
        str(target_dir),
        names,
        transcribe=False,
        start_ts=start_ts,
        end_ts=end_ts,
        incremental=incremental,
    )
    if not ok:
        raise RuntimeError(error or "微信聊天记录导出失败。")

    index_path = target_dir / export_all.EXPORT_INDEX_FILE
    export_path = ""
    display_name = names.get(username, username)
    if index_path.exists():
        with index_path.open("r", encoding="utf-8") as f:
            index_data = json.load(f)
        current_file = index_data.get("chats", {}).get(username, {}).get("current_file", "")
        if current_file:
            export_path = str(target_dir / current_file)

    if not export_path:
        candidates = sorted(target_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        candidates = [item for item in candidates if item.name != export_all.EXPORT_INDEX_FILE]
        if candidates:
            export_path = str(candidates[0])

    return {
        "chat": display_name,
        "username": username,
        "output_dir": str(target_dir),
        "export_path": export_path,
        "message_count": total_count,
        "new_count": new_count,
    }
