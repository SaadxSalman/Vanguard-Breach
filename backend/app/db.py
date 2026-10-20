"""SQLite persistence layer (stdlib only).

Schema:
  campaigns    – user-defined attack campaigns
  runs         – one execution of a campaign through the agent graph
  events       – structured run telemetry (streamed to the console via WS)
  findings     – confirmed vulnerabilities with evidence + remediation
  graphs       – synthesized attack-graph JSON per run
  reports      – generated report artifacts (md/html/json)
  kb_docs      – user-ingested adversarial knowledge documents
  vectors      – vector store persistence (default 'local' backend)
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .config import get_settings

_LOCK = threading.RLock()
_CONN: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    domain        TEXT NOT NULL DEFAULT 'general',
    target_ids    TEXT NOT NULL DEFAULT '[]',
    agents        TEXT NOT NULL DEFAULT '[]',
    config        TEXT NOT NULL DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'draft',
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id            TEXT PRIMARY KEY,
    campaign_id   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    current_node  TEXT NOT NULL DEFAULT '',
    progress      REAL NOT NULL DEFAULT 0.0,
    seed          INTEGER NOT NULL DEFAULT 1337,
    stats         TEXT NOT NULL DEFAULT '{}',
    error         TEXT NOT NULL DEFAULT '',
    started_at    REAL,
    finished_at   REAL,
    created_at    REAL NOT NULL,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL,
    ts            REAL NOT NULL,
    level         TEXT NOT NULL DEFAULT 'info',
    node          TEXT NOT NULL DEFAULT '',
    agent         TEXT NOT NULL DEFAULT '',
    message       TEXT NOT NULL,
    data          TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, id);
CREATE TABLE IF NOT EXISTS findings (
    id            TEXT PRIMARY KEY,
    run_id        TEXT NOT NULL,
    campaign_id   TEXT NOT NULL,
    title         TEXT NOT NULL,
    category      TEXT NOT NULL,
    severity      REAL NOT NULL DEFAULT 0.0,
    severity_label TEXT NOT NULL DEFAULT 'INFO',
    owasp         TEXT NOT NULL DEFAULT '',
    atlas         TEXT NOT NULL DEFAULT '',
    target_id     TEXT NOT NULL DEFAULT '',
    description   TEXT NOT NULL DEFAULT '',
    evidence      TEXT NOT NULL DEFAULT '{}',
    remediation   TEXT NOT NULL DEFAULT '',
    chain_id      TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'open',
    created_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_run ON findings(run_id);
CREATE TABLE IF NOT EXISTS graphs (
    run_id        TEXT PRIMARY KEY,
    graph         TEXT NOT NULL,
    created_at    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    id            TEXT PRIMARY KEY,
    run_id        TEXT NOT NULL,
    format        TEXT NOT NULL,
    path          TEXT NOT NULL,
    summary       TEXT NOT NULL DEFAULT '{}',
    created_at    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS kb_docs (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL DEFAULT 'manual',
    category      TEXT NOT NULL DEFAULT 'custom',
    title         TEXT NOT NULL,
    content       TEXT NOT NULL,
    meta          TEXT NOT NULL DEFAULT '{}',
    created_at    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS vectors (
    collection    TEXT NOT NULL,
    id            TEXT NOT NULL,
    vector        TEXT NOT NULL,
    payload       TEXT NOT NULL DEFAULT '{}',
    created_at    REAL NOT NULL,
    PRIMARY KEY (collection, id)
);
"""


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def get_conn() -> sqlite3.Connection:
    global _CONN
    with _LOCK:
        if _CONN is None:
            settings = get_settings()
            settings.ensure_dirs()
            _CONN = sqlite3.connect(str(settings.db_path), check_same_thread=False)
            _CONN.row_factory = sqlite3.Row
            _CONN.executescript(SCHEMA)
            _CONN.commit()
        return _CONN


def init_db() -> None:
    get_conn()


def close_db() -> None:
    global _CONN
    with _LOCK:
        if _CONN is not None:
            _CONN.close()
            _CONN = None


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with _LOCK:
        rows = get_conn().execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def query_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    with _LOCK:
        row = get_conn().execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> None:
    with _LOCK:
        conn = get_conn()
        conn.execute(sql, params)
        conn.commit()


def insert(table: str, values: dict[str, Any]) -> None:
    cols = ", ".join(values.keys())
    marks = ", ".join("?" for _ in values)
    execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(values.values()))


def now() -> float:
    return time.time()


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def loads(text: str | None, default: Any = None) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default
