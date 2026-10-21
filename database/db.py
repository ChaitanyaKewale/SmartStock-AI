"""SQLite database connection, schema initialization, and catalog seeding for SmartStock AI.

Enforces:
- Foreign key constraints
- Safe seed process that preserves live inventory on app restart
- Invariant 0 <= reserved <= on_hand
- Explicit transactions and startup recovery flagging
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional
from utils.config import ProductConfig, load_products_config, ConfigurationError

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "smartstock.sqlite"


def get_db_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a configured sqlite3 connection with row_factory, thread-safety, and foreign keys enabled."""
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


SCHEMA_SQL = """
-- 1. Products Catalog Reference
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_weight_kg REAL NOT NULL CHECK (unit_weight_kg > 0),
    shelf_id TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

-- 2. Inventory On-hand and Reserved Quantities
CREATE TABLE IF NOT EXISTS inventory (
    product_id TEXT PRIMARY KEY,
    shelf_id TEXT NOT NULL,
    on_hand INTEGER NOT NULL CHECK (on_hand >= 0),
    reserved INTEGER NOT NULL DEFAULT 0 CHECK (reserved >= 0 AND reserved <= on_hand),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- 3. Customer Orders
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    notes TEXT
);

-- 4. Order Line Items
CREATE TABLE IF NOT EXISTS order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    picked_quantity INTEGER NOT NULL DEFAULT 0 CHECK (picked_quantity >= 0 AND picked_quantity <= quantity),
    unit_weight_kg REAL NOT NULL,
    shelf_id TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 5. Inventory Transactions (Audit Log with Idempotency)
CREATE TABLE IF NOT EXISTS inventory_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT UNIQUE,
    order_id TEXT,
    product_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    delta_on_hand INTEGER NOT NULL DEFAULT 0,
    delta_reserved INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 6. Delivery Confirmations (Exactly-once delivery record)
CREATE TABLE IF NOT EXISTS deliveries (
    order_id TEXT PRIMARY KEY,
    delivered_at TEXT NOT NULL,
    total_items INTEGER NOT NULL,
    total_weight_kg REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- 7. Durable Operational Events
CREATE TABLE IF NOT EXISTS durable_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT,
    category TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    explanation TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
"""


def init_db(connection: sqlite3.Connection) -> None:
    """Initialize database tables and schema if they do not exist."""
    with connection:
        connection.executescript(SCHEMA_SQL)


def seed_catalog_if_empty(
    connection: sqlite3.Connection,
    products: Optional[List[ProductConfig]] = None
) -> int:
    """Safely seed products and initial inventory from catalog configuration.

    Invariant:
    - Products are inserted or updated without altering live operational stock.
    - Inventory records are inserted with INSERT OR IGNORE so existing on_hand
      and reserved balances are NEVER overwritten on application restart.

    Returns:
        Number of newly seeded inventory records.
    """
    if products is None:
        try:
            products = load_products_config()
        except ConfigurationError:
            return 0

    new_seeded_count = 0
    with connection:
        for p in products:
            # 1. Upsert product reference
            connection.execute(
                """
                INSERT INTO products (id, name, category, unit_weight_kg, shelf_id, active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    category = excluded.category,
                    unit_weight_kg = excluded.unit_weight_kg,
                    shelf_id = excluded.shelf_id,
                    active = excluded.active;
                """,
                (p.id, p.name, p.category, p.unit_weight_kg, p.shelf_id, 1 if p.active else 0)
            )

            # 2. Insert initial inventory only if not already present
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO inventory (product_id, shelf_id, on_hand, reserved)
                VALUES (?, ?, ?, 0);
                """,
                (p.id, p.shelf_id, p.initial_stock)
            )
            if cursor.rowcount > 0:
                new_seeded_count += 1

    return new_seeded_count
