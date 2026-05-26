"""SQLite database layer for report persistence and share logs."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DATABASE_PATH", "./data/cyber_judge.db")


def _ensure_dir() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reports (
            report_id     TEXT PRIMARY KEY,
            report_type   TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'processing',
            payload_json  TEXT NOT NULL DEFAULT '{}',
            error_msg     TEXT
        );

        CREATE TABLE IF NOT EXISTS share_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            slug         TEXT UNIQUE NOT NULL,
            report_id    TEXT NOT NULL REFERENCES reports(report_id),
            created_at   TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_share_slug ON share_logs(slug);
        CREATE INDEX IF NOT EXISTS idx_share_report ON share_logs(report_id);
        """
    )
    conn.commit()
    conn.close()


# ── Report CRUD ──────────────────────────────────────────────────

def insert_report(report_id: str, report_type: str, created_at: str, status: str = "processing") -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO reports (report_id, report_type, created_at, status) VALUES (?, ?, ?, ?)",
        (report_id, report_type, created_at, status),
    )
    conn.commit()
    conn.close()


def update_report_payload(report_id: str, payload: dict, status: str = "done") -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE reports SET payload_json = ?, status = ? WHERE report_id = ?",
        (json.dumps(payload, ensure_ascii=False), status, report_id),
    )
    conn.commit()
    conn.close()


def update_report_error(report_id: str, error_msg: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE reports SET status = 'error', error_msg = ? WHERE report_id = ?",
        (error_msg, report_id),
    )
    conn.commit()
    conn.close()


def get_report(report_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    r = dict(row)
    r["payload_json"] = json.loads(r["payload_json"])
    return r


# ── Share CRUD ───────────────────────────────────────────────────

def insert_share(slug: str, report_id: str, created_at: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO share_logs (slug, report_id, created_at) VALUES (?, ?, ?)",
        (slug, report_id, created_at),
    )
    conn.commit()
    conn.close()


def get_share(slug: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM share_logs WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    return dict(row) if row else None
