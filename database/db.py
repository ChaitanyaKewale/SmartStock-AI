"""SQLite database connection and session management for SmartStock AI."""

from __future__ import annotations
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "smartstock.sqlite"


def get_db_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a configured sqlite3 connection with row_factory enabled."""
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
