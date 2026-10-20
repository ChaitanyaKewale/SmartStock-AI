"""Repository abstractions for inventory, orders, and persistent records."""

from __future__ import annotations
import sqlite3
from typing import Optional


class BaseRepository:
    """Base repository wrapping a sqlite3 connection."""

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
