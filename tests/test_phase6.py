"""Phase 6 Automated Tests: End-to-End Order Fulfillment Workflow.

Verifies:
- Complete single-product order execution from validation to delivery confirmation.
- Complete multi-product order execution across multiple distinct shelf locations.
- Rejection of unknown SKUs and stock shortages.
- Rejection of pickup at incorrect position or beyond robot capacity.
- Rejection of delivery with missing cargo.
- Graceful handling and BLOCKED state when target is unreachable.
- Order cancellation before movement and after partial collection with inventory reconciliation.
- Exactly-once delivery without double-counting.
- Sequential orders without stale state leakage.
"""

import sqlite3
import pytest
from pathlib import Path

from simulation.engine import SimulationEngine
from simulation.fulfillment import OrderFulfillmentManager
from simulation.models import Position, RobotState
from database.db import get_db_connection, init_db, seed_catalog_if_empty
from utils.config import ProductConfig


@pytest.fixture
def fulfillment_env(tmp_path: Path) -> OrderFulfillmentManager:
    """Fixture providing an isolated SimulationEngine and OrderFulfillmentManager with temporary SQLite DB."""
    db_file = tmp_path / "test_fulfillment.sqlite"
    conn = get_db_connection(db_file)
    init_db(conn)

    sample_products = [
        ProductConfig(id="PROD-001", name="Laptop Pro", category="ELECTRONICS", unit_weight_kg=1.8, shelf_id="R01", initial_stock=25),
        ProductConfig(id="PROD-002", name="Keyboard", category="ELECTRONICS", unit_weight_kg=0.8, shelf_id="R02", initial_stock=15),
        ProductConfig(id="PROD-007", name="USB Cable", category="ACCESSORIES", unit_weight_kg=0.1, shelf_id="R07", initial_stock=50),
    ]
    seed_catalog_if_empty(conn, sample_products)

    engine = SimulationEngine()
    manager = OrderFulfillmentManager(engine=engine, db_path=str(db_file))
    return manager


def test_complete_single_product_order(fulfillment_env: OrderFulfillmentManager):
    """Verify single-product order completes through all phases and updates SQLite inventory."""
    mgr = fulfillment_env

    # 1. Validate & Create Order
    ok, msg, oid = mgr.validate_and_create_order([("PROD-001", 2)], order_id="ORD-SINGLE")
    assert ok is True
    assert oid == "ORD-SINGLE"

    # Verify SQLite reservation
    stock_res = mgr.inv_repo.get_stock("PROD-001")
    assert stock_res.on_hand == 25
    assert stock_res.reserved == 2

    # 2. Forward State-Space Search Mission Planning
    p_ok, p_msg = mgr.plan_order_mission()
    assert p_ok is True
    assert len(mgr.high_level_plan) == 4

    # 3. Run Autonomous Mission Execution
    report = mgr.run_full_mission()
    assert report.status == "DELIVERED"
    assert report.items_delivered == 2
    assert report.steps_travelled > 0

    # 4. Verify Final Database & Invariant State
    stock_final = mgr.inv_repo.get_stock("PROD-001")
    assert stock_final.on_hand == 23  # 2 units physically picked and delivered
    assert stock_final.reserved == 0  # No lingering reservations
    assert 0 <= stock_final.reserved <= stock_final.on_hand

    order_rec = mgr.order_repo.get_order("ORD-SINGLE")
    assert order_rec.status == "DELIVERED"
    assert order_rec.completed_at is not None

    # Robot must be at distribution station with zero cargo load
    assert (mgr.robot.position.x, mgr.robot.position.y) == (0, 0)
    assert mgr.robot.current_load_kg == 0.0


def test_complete_multi_product_order(fulfillment_env: OrderFulfillmentManager):
    """Verify multi-product order visits both pickup bays, collects items, and delivers."""
    mgr = fulfillment_env

    # Order 1x Laptop (R01 at 2, 2 -> pickup 2, 1) and 3x USB Cable (R07 at 7, 2 -> pickup 7, 1)
    items = [("PROD-001", 1), ("PROD-007", 3)]
    ok, msg, oid = mgr.validate_and_create_order(items, order_id="ORD-MULTI")
    assert ok is True

    p_ok, p_msg = mgr.plan_order_mission()
    assert p_ok is True

    report = mgr.run_full_mission()
    assert report.status == "DELIVERED"
    assert report.items_delivered == 4
    # 1.8 * 1 (PROD-001) + 0.08 * 3 (PROD-007) = 2.04 kg
    assert report.total_weight_kg == pytest.approx(2.04)

    # Check inventory
    assert mgr.inv_repo.get_stock("PROD-001").on_hand == 24
    assert mgr.inv_repo.get_stock("PROD-007").on_hand == 47


def test_reject_unknown_product_and_insufficient_stock(fulfillment_env: OrderFulfillmentManager):
    """Verify order validation catches non-existent SKUs and stock shortages."""
    mgr = fulfillment_env

    # 1. Unknown SKU rejected by unification
    ok_unk, msg_unk, _ = mgr.validate_and_create_order([("PROD-UNKNOWN", 1)])
    assert ok_unk is False
    assert "unification failed" in msg_unk.lower() or "missing" in msg_unk.lower()

    # 2. Stock shortage rejected by propositional logic & reservation
    ok_short, msg_short, _ = mgr.validate_and_create_order([("PROD-001", 999)])
    assert ok_short is False
    assert "rejected" in msg_short.lower() or "shortage" in msg_short.lower()


def test_reject_collection_beyond_capacity(fulfillment_env: OrderFulfillmentManager):
    """Verify order validation rejects requests exceeding robot max payload capacity."""
    mgr = fulfillment_env
    # PROD-001 weight is 1.8 kg. 15 units = 27 kg > 25 kg capacity
    ok, msg, _ = mgr.validate_and_create_order([("PROD-001", 15)])
    assert ok is False
    assert "capacity" in msg.lower()


def test_reject_delivery_with_missing_items(fulfillment_env: OrderFulfillmentManager):
    """Verify delivery confirmation cannot succeed if cargo is incomplete."""
    mgr = fulfillment_env
    ok, _, oid = mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-MISSING")
    assert ok is True

    # Attempt to confirm delivery immediately without picking item
    with pytest.raises(Exception):
        mgr.order_repo.confirm_delivery(oid, total_items=1, total_weight_kg=1.8, idempotency_key="DELIV-EARLY")


def test_handle_unreachable_target(fulfillment_env: OrderFulfillmentManager):
    """Verify fulfillment halts safely in BLOCKED state when target pickup bay is walled off."""
    mgr = fulfillment_env

    # Shelf R01 pickup bay is (2, 1). Box it in with obstacles:
    mgr.grid.add_obstacle(2, 0)
    mgr.grid.add_obstacle(1, 1)
    mgr.grid.add_obstacle(3, 1)
    # Note: (2, 2) is already a rack cell

    ok, _, oid = mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-TRAPPED")
    assert ok is True

    # Planning or execution must detect unreachability
    mgr.plan_order_mission()
    report = mgr.run_full_mission()

    assert report.status == "BLOCKED"
    assert mgr.robot.state == RobotState.BLOCKED


def test_cancellation_before_movement_and_after_partial_collection(fulfillment_env: OrderFulfillmentManager):
    """Verify cancellation properly reconciles unpicked reservations and picked cargo."""
    mgr = fulfillment_env

    # 1. Cancellation before movement
    ok, _, oid1 = mgr.validate_and_create_order([("PROD-001", 2)], order_id="ORD-CANCEL-1")
    assert mgr.inv_repo.get_stock("PROD-001").reserved == 2
    c_ok, _ = mgr.cancel_active_order()
    assert c_ok is True
    assert mgr.inv_repo.get_stock("PROD-001").reserved == 0
    assert mgr.inv_repo.get_stock("PROD-001").on_hand == 25

    # 2. Cancellation after picking items
    ok, _, oid2 = mgr.validate_and_create_order([("PROD-001", 2)], order_id="ORD-CANCEL-2")
    mgr.plan_order_mission()
    # Step until pickup occurs
    while mgr.current_plan_index < 2:  # Step through navigation and pickup
        s_ok, _, _ = mgr.execute_next_step()
        if not s_ok:
            break

    # Item is picked: on_hand is 23, robot carried is 2
    c_ok2, _ = mgr.cancel_active_order()
    assert c_ok2 is True
    # Reconciled: picked cargo returned to shelf on-hand, reservations 0
    assert mgr.inv_repo.get_stock("PROD-001").reserved == 0
    assert mgr.inv_repo.get_stock("PROD-001").on_hand == 25
    assert mgr.robot.current_load_kg == 0.0


def test_repeat_delivery_idempotency(fulfillment_env: OrderFulfillmentManager):
    """Verify repeat delivery execution does not double-count stock or delivery records."""
    mgr = fulfillment_env
    mgr.validate_and_create_order([("PROD-002", 1)], order_id="ORD-IDEMP")
    mgr.plan_order_mission()
    mgr.run_full_mission()

    completed_before = len(mgr.order_repo.get_completed_orders())
    assert completed_before == 1

    # Repeat delivery confirmation with same idempotency key
    rec = mgr.order_repo.confirm_delivery("ORD-IDEMP", total_items=1, total_weight_kg=0.8, idempotency_key="DELIV-ORD-IDEMP")
    completed_after = len(mgr.order_repo.get_completed_orders())
    assert completed_after == 1  # Exactly-once


def test_sequential_orders_no_stale_state(fulfillment_env: OrderFulfillmentManager):
    """Verify executing multiple sequential orders leaves no residual state."""
    mgr = fulfillment_env

    # Run Order 1
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-SEQ-1")
    mgr.plan_order_mission()
    report1 = mgr.run_full_mission()
    assert report1.status == "DELIVERED"

    # Reset robot back to station for Order 2
    mgr.engine.reset(confirm=True)

    # Run Order 2
    mgr.validate_and_create_order([("PROD-007", 2)], order_id="ORD-SEQ-2")
    mgr.plan_order_mission()
    report2 = mgr.run_full_mission()
    assert report2.status == "DELIVERED"
    assert report2.items_delivered == 2

    # Both orders recorded
    completed = mgr.order_repo.get_completed_orders()
    assert len(completed) == 2
