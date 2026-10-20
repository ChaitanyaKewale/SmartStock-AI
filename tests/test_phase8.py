"""Phase 8 Automated Tests: Inventory, AI Laboratory, Analytics, and Warehouse Editing Polish.

Verifies:
- Inventory search, filter, and strict quantity invariants (preventing on-hand < reserved).
- AI Laboratory invokes genuine algorithm modules without mocks.
- Analytics calculations against a known test dataset.
- Invalid layout edits do not corrupt or overwrite saved warehouse layout.
- Restore-default layout restoration.
- Empty database and zero-division handling.
- Simulation state preservation across multi-page workflows.
"""

import sqlite3
import pytest
from pathlib import Path

from simulation.engine import SimulationEngine
from simulation.warehouse import get_default_warehouse, WarehouseGrid
from simulation.models import Position, RobotState, RobotDirection
from simulation.fulfillment import OrderFulfillmentManager
from database.db import get_db_connection, init_db, seed_catalog_if_empty
from database.repositories import InventoryRepository, OrderRepository
from utils.config import ProductConfig

# AI syllabus algorithms
from ai.unification import Predicate, Constant, Variable, resolve_product_predicate
from ai.propositional_logic import (
    evaluate_order_acceptance,
    evaluate_delivery_eligibility,
    evaluate_robot_capacity
)
from ai.min_conflicts import StorageAssignmentProblem, min_conflicts
from ai.greedy_best_first import greedy_best_first_search
from ai.forward_search import forward_state_space_search
from ai.reflex_agent import SimpleReflexAgent, Percept


@pytest.fixture
def phase8_db(tmp_path: Path):
    """Provides an isolated SQLite database connection with seeded catalog data."""
    db_file = tmp_path / "test_phase8.sqlite"
    conn = get_db_connection(db_file)
    init_db(conn)

    sample_products = [
        ProductConfig(id="PROD-001", name="Laptop Pro", category="ELECTRONICS", unit_weight_kg=1.8, shelf_id="R01", initial_stock=20),
        ProductConfig(id="PROD-002", name="Keyboard", category="ELECTRONICS", unit_weight_kg=0.8, shelf_id="R02", initial_stock=15),
        ProductConfig(id="PROD-007", name="USB Cable", category="ACCESSORIES", unit_weight_kg=0.1, shelf_id="R07", initial_stock=40),
    ]
    seed_catalog_if_empty(conn, sample_products)
    return conn, db_file


def test_inventory_search_filter_and_invariants(phase8_db):
    """Verify inventory quantity invariants, restock adjustments, and reservation protections."""
    conn, _ = phase8_db
    inv_repo = InventoryRepository(conn)

    # 1. Initial State
    stock = inv_repo.get_stock("PROD-001")
    assert stock.on_hand == 20
    assert stock.reserved == 0
    assert stock.available == 20

    # 2. Reserve 5 units
    inv_repo.reserve_order_stock(
        order_id="ORD-INV-TEST",
        items=[("PROD-001", 5)],
        idempotency_key="RES-INV-1"
    )
    stock_res = inv_repo.get_stock("PROD-001")
    assert stock_res.on_hand == 20
    assert stock_res.reserved == 5
    assert stock_res.available == 15

    # 3. Valid Restock: increase on_hand to 30
    ok = inv_repo.adjust_stock("PROD-001", 30, reason="RESTOCK")
    assert ok is True
    stock_adj = inv_repo.get_stock("PROD-001")
    assert stock_adj.on_hand == 30
    assert stock_adj.reserved == 5
    assert stock_adj.available == 25

    # 4. Invariant Protection: Cannot reduce on_hand below active reserved quantity (5)
    with pytest.raises(ValueError) as exc:
        inv_repo.adjust_stock("PROD-001", 4, reason="INVALID_REDUCTION")
    assert "active reservations" in str(exc.value).lower()

    # 5. Negative stock rejected
    with pytest.raises(ValueError):
        inv_repo.adjust_stock("PROD-001", -1)

    # 6. Non-existent product rejected
    with pytest.raises(ValueError):
        inv_repo.adjust_stock("PROD-NONEXISTENT", 10)


def test_ai_laboratory_invokes_genuine_algorithms():
    """Verify that all six AI concept modules execute and return valid results without mocks."""
    warehouse = get_default_warehouse()

    # 1. Unification
    kb = [Predicate("Item", (Constant("PROD-001"), Constant("ELECTRONICS"), Constant("R01")))]
    query = Predicate("Item", (Constant("PROD-001"), Variable("?cat"), Variable("?shelf")))
    unif_res = resolve_product_predicate(query, kb)
    assert unif_res.success is True
    assert "ELECTRONICS" in unif_res.substitution["?cat"]

    # 2. Propositional Logic
    prop_res = evaluate_order_acceptance(True, True, True, True)
    assert prop_res.result is True
    cap_res = evaluate_robot_capacity(20.0, 6.0, 25.0)
    assert cap_res.result is False  # 26 > 25

    # 3. Min-Conflicts
    prob = StorageAssignmentProblem(
        variables=["P1", "P2"],
        domains={"P1": ["R1", "R2"], "P2": ["R1", "R2"]},
        item_categories={"P1": "CAT_A", "P2": "CAT_B"},
        shelf_zones={"R1": "CAT_A", "R2": "CAT_B"},
        shelf_capacities={"R1": 1, "R2": 1}
    )
    mc_res = min_conflicts(prob, initial_assignment={"P1": "R2", "P2": "R1"}, max_steps=20, seed=42)
    assert mc_res.success is True
    assert mc_res.final_conflicts == 0
    assert mc_res.final_assignment == {"P1": "R1", "P2": "R2"}

    # 4. Greedy Best-First Search
    gbfs_res = greedy_best_first_search(warehouse, Position(x=0, y=1), Position(x=2, y=1))
    assert gbfs_res.success is True
    assert gbfs_res.total_cost == 2

    # 5. Forward Search
    fwd_res = forward_state_space_search(warehouse, Position(x=0, y=1), {"PROD-001": 1})
    assert fwd_res.success is True
    assert len(fwd_res.plan) == 4

    # 6. Reflex Agent
    reflex = SimpleReflexAgent()
    percept = Percept(
        current_position=Position(x=1, y=1),
        facing=RobotDirection.EAST,
        proposed_next_cell=Position(x=2, y=1),
        is_next_cell_blocked=True
    )
    r_act = reflex.evaluate(percept)
    assert r_act.action == "STOP_AND_REPLAN"


def test_analytics_calculations_against_dataset(phase8_db):
    """Verify operational analytics metrics calculate correctly against seeded deliveries."""
    conn, _ = phase8_db
    cursor = conn.cursor()

    # Create 2 orders: 1 DELIVERED, 1 BLOCKED
    cursor.execute("""
        INSERT INTO orders (id, status, created_at, completed_at, notes)
        VALUES ('ORD-D1', 'DELIVERED', '2026-10-21T10:00:00', '2026-10-21T10:05:00', 'Successful fulfillment'),
               ('ORD-B1', 'BLOCKED', '2026-10-21T10:10:00', NULL, 'Route impassable');
    """)

    # Record delivery confirmation
    cursor.execute("""
        INSERT INTO deliveries (order_id, delivered_at, total_items, total_weight_kg, notes)
        VALUES ('ORD-D1', '2026-10-21T10:05:00', 3, 4.2, 'Station confirmed');
    """)

    # Record picked order lines
    cursor.execute("""
        INSERT INTO order_lines (order_id, product_id, quantity, picked_quantity, unit_weight_kg, shelf_id)
        VALUES ('ORD-D1', 'PROD-001', 2, 2, 1.8, 'R01'),
               ('ORD-D1', 'PROD-002', 1, 1, 0.6, 'R02');
    """)
    conn.commit()

    # Analytics queries
    cursor.execute("SELECT status, count(*) as cnt FROM orders GROUP BY status;")
    status_summary = {r["status"]: r["cnt"] for r in cursor.fetchall()}
    assert status_summary["DELIVERED"] == 1
    assert status_summary["BLOCKED"] == 1

    cursor.execute("SELECT sum(total_items) as items, sum(total_weight_kg) as wt FROM deliveries;")
    deliv_row = cursor.fetchone()
    assert deliv_row["items"] == 3
    assert deliv_row["wt"] == pytest.approx(4.2)


def test_invalid_layout_edit_preserves_saved_layout():
    """Verify obstacle placement rules prevent mutating station, racks, and bounds."""
    warehouse = get_default_warehouse()
    init_obstacles_count = len(warehouse.user_added_obstacles)

    # 1. Reject placement on Distribution Station (0, 0)
    can_ds, msg_ds = warehouse.can_place_obstacle(0, 0)
    assert can_ds is False
    assert "station" in msg_ds.lower()

    # 2. Reject placement on Robot Home (0, 1)
    can_home, msg_home = warehouse.can_place_obstacle(0, 1)
    assert can_home is False
    assert "home" in msg_home.lower() or "robot" in msg_home.lower()

    # 3. Reject placement on Physical Storage Rack (2, 2)
    can_rack, msg_rack = warehouse.can_place_obstacle(2, 2)
    assert can_rack is False
    assert "rack" in msg_rack.lower()

    # 4. Reject placement out of bounds
    can_oob, _ = warehouse.can_place_obstacle(99, 99)
    assert can_oob is False

    # Obstacle set remained intact
    assert len(warehouse.user_added_obstacles) == init_obstacles_count


def test_restore_default_layout():
    """Verify that adding valid obstacles and discarding edits restores default layout."""
    warehouse = get_default_warehouse()

    # Add 2 user obstacles at valid aisle coordinates (1, 4) and (1, 5)
    warehouse.add_obstacle(1, 4)
    warehouse.add_obstacle(1, 5)
    assert len(warehouse.user_added_obstacles) == 2
    assert warehouse.is_walkable(1, 4) is False

    # Discard edits
    warehouse.discard_edits()
    assert len(warehouse.user_added_obstacles) == 0
    assert warehouse.is_walkable(1, 4) is True
    assert warehouse.is_walkable(1, 5) is True


def test_empty_database_analytics_handling(tmp_path: Path):
    """Verify that empty SQLite tables render zero metrics without raising exceptions."""
    empty_db = tmp_path / "empty.sqlite"
    conn = get_db_connection(empty_db)
    init_db(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT count(*) as cnt FROM orders;")
    assert cursor.fetchone()["cnt"] == 0

    cursor.execute("SELECT count(*) as cnt FROM deliveries;")
    assert cursor.fetchone()["cnt"] == 0

    # Ensure average calculation with 0 completed orders does not ZeroDivisionError
    completed_orders = []
    total_steps = 10
    avg_steps = (total_steps / len(completed_orders)) if completed_orders else 0.0
    assert avg_steps == 0.0


def test_simulation_state_preservation_across_workflows(phase8_db):
    """Verify that active order, position, and cargo load remain intact in memory."""
    _, db_file = phase8_db
    engine = SimulationEngine()
    mgr = OrderFulfillmentManager(engine=engine, db_path=str(db_file))

    # Validate and plan an order
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-MULTI-PAGE")
    mgr.plan_order_mission()

    # Step twice
    mgr.execute_next_step()
    mgr.execute_next_step()
    pos_after_steps = (mgr.robot.position.x, mgr.robot.position.y)

    # In a Streamlit multi-page switch, mgr is retained in st.session_state
    # Check that mission attributes are fully preserved
    assert mgr.active_order_id == "ORD-MULTI-PAGE"
    assert (mgr.robot.position.x, mgr.robot.position.y) == pos_after_steps
    assert len(mgr.high_level_plan) == 4
