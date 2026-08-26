"""
database/connection.py

Single source of truth for SQLite access. Nothing outside this module
should call sqlite3.connect() directly — services/ import get_db_connection
from here and build their SQL on top of it.

Design choices:
- WAL mode: lets Streamlit's multiple script reruns / sessions read and
  write concurrently without "database is locked" errors.
- PRAGMA foreign_keys = ON: SQLite disables FK enforcement by default,
  and it's a per-connection setting, so we set it on every connection,
  not just once at setup.
- Context manager wraps `with conn:` internally, so callers get automatic
  commit-on-success / rollback-on-exception for free, and the connection
  is always closed even if an exception propagates.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _configure_connection(conn: sqlite3.Connection) -> None:
    """Apply per-connection PRAGMAs. Must run on every new connection."""
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.row_factory = sqlite3.Row


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    """
    Yield a configured SQLite connection as a context manager.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...", (params,))
            rows = cursor.fetchall()

    The `with conn:` block below means: if the block under this
    contextmanager's `yield` completes without raising, SQLite commits;
    if it raises, SQLite rolls back. The connection itself is always
    closed via `finally`, independent of commit/rollback outcome.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Default isolation_level ("") means sqlite3 opens an implicit
    # transaction before the first DML statement, and `with conn:`
    # commits it on success or rolls it back on exception.
    conn = sqlite3.connect(DB_PATH, timeout=10)
    _configure_connection(conn)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    """
    Idempotently create tables from schema.sql. Safe to call on every
    app startup (CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text()

    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        _configure_connection(conn)
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
