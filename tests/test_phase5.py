"""Phase 5 Automated Tests: SQLite Persistence, Stock Reservations, and Interrupted Order Recovery.

Verifies:
- Schema initialization idempotency.
- Catalog seeding does not overwrite live inventory quantities.
- Stock reservation and insufficient stock transaction rollback.
- Collection transaction and shelf balance invariants (0 <= reserved <= on_hand).
- Cancellation reservation release and picked cargo reconciliation.
- Exactly-once delivery confirmation and DeliveryError on incomplete items.
- Database persistence across connection closings and reopenings.
- Interrupted-order recovery detection and marking.
"""

import sqlite3
import pytest
from pathlib import Path

from database.db import get_db_connection, init_db, seed_catalog_if_empty
from database.repositories import (
    InventoryRepository,
    OrderRepository,
    InsufficientStockError,
    DeliveryError
)
from utils.config import ProductConfig


@pytest.fixture
def test_db(tmp_path: Path) -> sqlite3.Connection:
    """Fixture providing an isolated SQLite database initialized and seeded for each test."""
    db_file = tmp_path / "test_smartstock.sqlite"
    conn = get_db_connection(db_file)
    init_db(conn)

    sample_products = [
        ProductConfig(id="PROD-001", name="Laptop Pro", category="ELECTRONICS", unit_weight_kg=1.8, shelf_id="R01", initial_stock=25),
        ProductConfig(id="PROD-002", name="Keyboard", category="ELECTRONICS", unit_weight_kg=0.8, shelf_id="R02", initial_stock=15),
        ProductConfig(id="PROD-007", name="USB Cable", category="ACCESSORIES", unit_weight_kg=0.1, shelf_id="R07", initial_stock=50),
    ]
    seed_catalog_if_empty(conn, sample_products)
    return conn


def test_schema_repeat_initialization(test_db: sqlite3.Connection):
    """Verify that calling init_db repeatedly is safe and idempotent."""
    init_db(test_db)
    init_db(test_db)
    cursor = test_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "products" in tables
    assert "inventory" in tables
    assert "orders" in tables
    assert "order_lines" in tables
    assert "inventory_transactions" in tables
    assert "deliveries" in tables


def test_seed_does_not_overwrite_live_inventory(test_db: sqlite3.Connection):
    """Verify that seeding preserves modified live inventory on app restarts."""
    inv_repo = InventoryRepository(test_db)
    stock_before = inv_repo.get_stock("PROD-001")
    assert stock_before.on_hand == 25

    # Simulate operational stock change (e.g., items sold/dispatched)
    with test_db:
        test_db.execute("UPDATE inventory SET on_hand = 12 WHERE product_id = 'PROD-001'")

    # Run seed again (as would happen on application start)
    sample_products = [
        ProductConfig(id="PROD-001", name="Laptop Pro", category="ELECTRONICS", unit_weight_kg=1.8, shelf_id="R01", initial_stock=25)
    ]
    newly_seeded = seed_catalog_if_empty(test_db, sample_products)
    assert newly_seeded == 0

    # Live stock must remain 12, not reset to 25
    stock_after = inv_repo.get_stock("PROD-001")
    assert stock_after.on_hand == 12


def test_reserve_stock_success_and_rollback_on_shortage(test_db: sqlite3.Connection):
    """Verify transactional reservation succeeds and rolls back on insufficient stock."""
    inv_repo = InventoryRepository(test_db)

    # 1. Successful reservation of 5 units
    success = inv_repo.reserve_order_stock(
        order_id="ORD-001",
        items=[("PROD-001", 5)],
        idempotency_key="KEY-ORD-001-RES"
    )
    assert success is True
    rec = inv_repo.get_stock("PROD-001")
    assert rec.on_hand == 25
    assert rec.reserved == 5
    assert rec.available == 20

    # 2. Insufficient stock reservation: requested 25, only 20 available
    with pytest.raises(InsufficientStockError) as exc_info:
        inv_repo.reserve_order_stock(
            order_id="ORD-002",
            items=[("PROD-001", 25)],
            idempotency_key="KEY-ORD-002-FAIL"
        )
    assert "insufficient stock" in str(exc_info.value).lower()

    # 3. Invariant: Failed transaction must rollback completely (reserved remains 5)
    rec_after_fail = inv_repo.get_stock("PROD-001")
    assert rec_after_fail.reserved == 5
    assert rec_after_fail.available == 20


def test_collection_transaction_and_invariants(test_db: sqlite3.Connection):
    """Verify picking stock deducts shelf on-hand, frees reservation, and maintains 0 <= reserved <= on_hand."""
    inv_repo = InventoryRepository(test_db)
    order_repo = OrderRepository(test_db)

    # Create order with 4 units of PROD-001
    order_repo.create_order(
        order_id="ORD-100",
        lines=[{"product_id": "PROD-001", "quantity": 4, "unit_weight_kg": 1.8, "shelf_id": "R01"}]
    )
    inv_repo.reserve_order_stock("ORD-100", [("PROD-001", 4)], idempotency_key="RES-ORD-100")

    stock1 = inv_repo.get_stock("PROD-001")
    assert stock1.on_hand == 25
    assert stock1.reserved == 4

    # Robot picks 2 units
    inv_repo.record_item_picked("ORD-100", "PROD-001", quantity=2, idempotency_key="PICK-ORD-100-1")

    stock2 = inv_repo.get_stock("PROD-001")
    assert stock2.on_hand == 23  # Physically removed from shelf
    assert stock2.reserved == 2  # Converted from reservation to carried payload
    assert 0 <= stock2.reserved <= stock2.on_hand

    lines = order_repo.get_order_lines("ORD-100")
    assert lines[0].picked_quantity == 2


def test_cancellation_release_and_picked_reconciliation(test_db: sqlite3.Connection):
    """Verify cancellation frees unpicked reservations and returns picked cargo to shelf on-hand."""
    inv_repo = InventoryRepository(test_db)
    order_repo = OrderRepository(test_db)

    # Order 5 units
    order_repo.create_order(
        order_id="ORD-200",
        lines=[{"product_id": "PROD-001", "quantity": 5, "unit_weight_kg": 1.8, "shelf_id": "R01"}]
    )
    inv_repo.reserve_order_stock("ORD-200", [("PROD-001", 5)], idempotency_key="RES-200")

    # Pick 2 units
    inv_repo.record_item_picked("ORD-200", "PROD-001", 2, "PICK-200-1")
    stock_mid = inv_repo.get_stock("PROD-001")
    assert stock_mid.on_hand == 23
    assert stock_mid.reserved == 3

    # Cancel order with reconciliation
    inv_repo.release_and_reconcile_order("ORD-200", reconcile_picked=True)
    order_repo.update_status("ORD-200", "CANCELLED")

    stock_final = inv_repo.get_stock("PROD-001")
    assert stock_final.reserved == 0   # All reservations cleared
    assert stock_final.on_hand == 25    # 2 picked units restocked back to shelf


def test_idempotent_delivery_confirmation(test_db: sqlite3.Connection):
    """Verify exactly-once delivery and rejection of delivery when items are unpicked."""
    inv_repo = InventoryRepository(test_db)
    order_repo = OrderRepository(test_db)

    # 1. Incomplete order: 2 units ordered, none picked
    order_repo.create_order(
        order_id="ORD-300",
        lines=[{"product_id": "PROD-002", "quantity": 2, "unit_weight_kg": 0.8, "shelf_id": "R02"}]
    )
    inv_repo.reserve_order_stock("ORD-300", [("PROD-002", 2)], "RES-300")

    with pytest.raises(DeliveryError) as exc_info:
        order_repo.confirm_delivery("ORD-300", total_items=2, total_weight_kg=1.6, idempotency_key="DELIV-300")
    assert "incomplete items" in str(exc_info.value).lower()

    # 2. Fully pick items
    inv_repo.record_item_picked("ORD-300", "PROD-002", 2, "PICK-300")

    # 3. Delivery confirmation succeeds
    deliv1 = order_repo.confirm_delivery("ORD-300", total_items=2, total_weight_kg=1.6, idempotency_key="DELIV-300")
    assert deliv1.order_id == "ORD-300"
    assert deliv1.total_items == 2

    ord_rec = order_repo.get_order("ORD-300")
    assert ord_rec.status == "DELIVERED"
    assert ord_rec.completed_at is not None

    # 4. Exactly-once idempotency: repeating delivery returns identical record without error
    deliv2 = order_repo.confirm_delivery("ORD-300", total_items=2, total_weight_kg=1.6, idempotency_key="DELIV-300")
    assert deliv2.delivered_at == deliv1.delivered_at


def test_persistence_across_connection_reopen(tmp_path: Path):
    """Verify SQLite durability after closing and opening a new connection."""
    db_file = tmp_path / "persistent.sqlite"

    # Connection 1: write order and reserve stock
    conn1 = get_db_connection(db_file)
    init_db(conn1)
    seed_catalog_if_empty(conn1)

    inv_repo1 = InventoryRepository(conn1)
    order_repo1 = OrderRepository(conn1)
    order_repo1.create_order("ORD-DURABLE", [{"product_id": "PROD-001", "quantity": 3, "unit_weight_kg": 1.8, "shelf_id": "R01"}])
    inv_repo1.reserve_order_stock("ORD-DURABLE", [("PROD-001", 3)], "RES-DURABLE")
    conn1.close()

    # Connection 2: reopen same file
    conn2 = get_db_connection(db_file)
    inv_repo2 = InventoryRepository(conn2)
    order_repo2 = OrderRepository(conn2)

    ord_rec = order_repo2.get_order("ORD-DURABLE")
    assert ord_rec is not None
    assert ord_rec.id == "ORD-DURABLE"

    stock = inv_repo2.get_stock("PROD-001")
    assert stock.reserved == 3
    assert stock.available == 22
    conn2.close()


def test_interrupted_orders_flagged_for_recovery(test_db: sqlite3.Connection):
    """Verify startup recovery detects in-flight orders and flags them RECOVERY_REQUIRED."""
    order_repo = OrderRepository(test_db)

    # Insert test orders with various statuses
    order_repo.create_order("ORD-ACTIVE-1", [{"product_id": "PROD-001", "quantity": 1, "unit_weight_kg": 1.8, "shelf_id": "R01"}], status="IN_PROGRESS")
    order_repo.create_order("ORD-ACTIVE-2", [{"product_id": "PROD-002", "quantity": 1, "unit_weight_kg": 0.8, "shelf_id": "R02"}], status="COLLECTING")
    order_repo.create_order("ORD-DONE", [{"product_id": "PROD-007", "quantity": 1, "unit_weight_kg": 0.1, "shelf_id": "R07"}], status="DELIVERED")
    order_repo.create_order("ORD-CANCELLED", [{"product_id": "PROD-007", "quantity": 1, "unit_weight_kg": 0.1, "shelf_id": "R07"}], status="CANCELLED")
    order_repo.create_order("ORD-DRAFT", [{"product_id": "PROD-007", "quantity": 1, "unit_weight_kg": 0.1, "shelf_id": "R07"}], status="DRAFT")

    flagged = order_repo.flag_interrupted_orders()
    assert "ORD-ACTIVE-1" in flagged
    assert "ORD-ACTIVE-2" in flagged
    assert len(flagged) == 2

    # Verified updated status
    assert order_repo.get_order("ORD-ACTIVE-1").status == "RECOVERY_REQUIRED"
    assert order_repo.get_order("ORD-ACTIVE-2").status == "RECOVERY_REQUIRED"

    # Terminal or draft orders untouched
    assert order_repo.get_order("ORD-DONE").status == "DELIVERED"
    assert order_repo.get_order("ORD-CANCELLED").status == "CANCELLED"
    assert order_repo.get_order("ORD-DRAFT").status == "DRAFT"
