"""Phase 9 Verification Suite: Full Scenario Matrix & Reliability Regression.

Executes all 28 required test scenarios defined in Section 738-769 of phases.md:
1. Valid order with one product.
2. Valid order with multiple products.
3. Unknown product.
4. Empty order.
5. Zero/negative quantity.
6. Insufficient stock.
7. Inactive product.
8. Capacity exceeded.
9. Shelf blocked but alternative route exists.
10. No route to a target.
11. Obstacle introduced during movement.
12. Product unexpectedly unavailable at pickup.
13. Collection attempted at wrong location.
14. Duplicate collection action.
15. Delivery attempted with missing items.
16. Duplicate delivery action.
17. Cancellation before movement.
18. Cancellation after partial collection.
19. Min-Conflicts succeeds.
20. Min-Conflicts reaches iteration limit or cannot find a valid allocation.
21. Invalid/malformed configuration.
22. SQLite transaction failure or rollback path, tested safely.
23. Application restart with no active order.
24. Application restart with an interrupted order.
25. Pause/resume during an active order.
26. Repeated UI reruns or duplicate frontend messages.
27. Warehouse layout edit validation.
28. Multiple sequential orders with different products.
"""

from __future__ import annotations

import sqlite3
import pytest
from pathlib import Path

from simulation.engine import SimulationEngine
from simulation.warehouse import get_default_warehouse, WarehouseGrid
from simulation.models import Position, RobotState, RobotDirection
from simulation.fulfillment import OrderFulfillmentManager
from database.db import get_db_connection, init_db, seed_catalog_if_empty
from database.repositories import InventoryRepository, OrderRepository, InsufficientStockError
from utils.config import ProductConfig, WarehouseConfig, load_warehouse_config, ConfigurationError

from ai.unification import Predicate, Constant, Variable, resolve_product_predicate
from ai.propositional_logic import evaluate_order_acceptance, evaluate_delivery_eligibility, evaluate_robot_capacity
from ai.min_conflicts import StorageAssignmentProblem, min_conflicts
from ai.greedy_best_first import greedy_best_first_search
from ai.forward_search import forward_state_space_search
from ai.reflex_agent import SimpleReflexAgent, Percept


@pytest.fixture
def p9_env(tmp_path: Path):
    """Provides an isolated SimulationEngine, SQLite database, and OrderFulfillmentManager."""
    db_file = tmp_path / "test_phase9.sqlite"
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
    return manager, conn


# =============================================================================
# SCENARIOS 1 - 8: Order Entry, Validation, and Capacity Edge Cases
# =============================================================================

def test_scenario_01_valid_order_single_product(p9_env):
    """Scenario 1: Valid order with one product executes completely to confirmed delivery."""
    mgr, _ = p9_env
    ok, _, oid = mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-S01")
    assert ok is True
    mgr.plan_order_mission()
    report = mgr.run_full_mission()
    assert report.status == "DELIVERED"
    assert report.items_delivered == 1
    assert mgr.order_repo.get_order(oid).status == "DELIVERED"


def test_scenario_02_valid_order_multiple_products(p9_env):
    """Scenario 2: Valid order with multiple distinct products fulfills all lines."""
    mgr, _ = p9_env
    ok, _, oid = mgr.validate_and_create_order([("PROD-001", 1), ("PROD-007", 2)], order_id="ORD-S02")
    assert ok is True
    mgr.plan_order_mission()
    report = mgr.run_full_mission()
    assert report.status == "DELIVERED"
    assert report.items_delivered == 3


def test_scenario_03_unknown_product_rejected(p9_env):
    """Scenario 3: Unknown product rejected by logical unification."""
    mgr, _ = p9_env
    ok, msg, _ = mgr.validate_and_create_order([("PROD-UNKNOWN-99", 1)])
    assert ok is False
    assert "unification failed" in msg.lower() or "missing" in msg.lower()


def test_scenario_04_empty_order_rejected(p9_env):
    """Scenario 4: Empty order submission rejected."""
    mgr, _ = p9_env
    ok, msg, _ = mgr.validate_and_create_order([])
    assert ok is False
    assert "empty" in msg.lower()


def test_scenario_05_zero_negative_quantity_rejected(p9_env):
    """Scenario 5: Zero or negative quantities strictly rejected."""
    mgr, _ = p9_env
    ok_zero, msg_zero, _ = mgr.validate_and_create_order([("PROD-001", 0)])
    assert ok_zero is False
    assert "positive" in msg_zero.lower()

    ok_neg, msg_neg, _ = mgr.validate_and_create_order([("PROD-001", -3)])
    assert ok_neg is False
    assert "positive" in msg_neg.lower()


def test_scenario_06_insufficient_stock_rejected(p9_env):
    """Scenario 6: Order quantity exceeding available stock rejected."""
    mgr, _ = p9_env
    ok, msg, _ = mgr.validate_and_create_order([("PROD-001", 999)])
    assert ok is False
    assert "insufficient" in msg.lower() or "rejected" in msg.lower()


def test_scenario_07_inactive_product_rejected(p9_env):
    """Scenario 7: Inactive product rejected during acceptance."""
    mgr, _ = p9_env
    mgr.grid.products_by_id["PROD-001"].active = False
    ok, msg, _ = mgr.validate_and_create_order([("PROD-001", 1)])
    assert ok is False
    assert "inactive" in msg.lower()
    mgr.grid.products_by_id["PROD-001"].active = True


def test_scenario_08_capacity_exceeded_rejected(p9_env):
    """Scenario 8: Order exceeding robot maximum capacity (25 kg) rejected."""
    mgr, _ = p9_env
    # PROD-001 is 1.8 kg each. 15 * 1.8 = 27 kg > 25 kg
    ok, msg, _ = mgr.validate_and_create_order([("PROD-001", 15)])
    assert ok is False
    assert "capacity" in msg.lower()


# =============================================================================
# SCENARIOS 9 - 14: Navigation, Obstacles, Collection, and Preconditions
# =============================================================================

def test_scenario_09_shelf_blocked_alternative_route_exists(p9_env):
    """Scenario 9: Aisle blocked, GBFS finds detour route to destination."""
    mgr, _ = p9_env
    # Place obstacle in direct aisle
    mgr.grid.add_obstacle(1, 1)
    gbfs_res = greedy_best_first_search(mgr.grid, Position(x=0, y=1), Position(x=2, y=1))
    assert gbfs_res.success is True
    # Path routes around (1, 1)
    assert Position(x=1, y=1) not in gbfs_res.path


def test_scenario_10_no_route_to_target_blocked_state(p9_env):
    """Scenario 10: Completely boxed-in target bay halts safely in BLOCKED state."""
    mgr, _ = p9_env
    # Box in target pickup bay (2, 1)
    mgr.grid.add_obstacle(2, 0)
    mgr.grid.add_obstacle(1, 1)
    mgr.grid.add_obstacle(3, 1)

    ok, _, oid = mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-S10")
    mgr.plan_order_mission()
    s_ok, s_msg, _ = mgr.execute_next_step()
    assert s_ok is False
    assert mgr.robot.state == RobotState.BLOCKED
    assert mgr.order_repo.get_order(oid).status == "BLOCKED"


def test_scenario_11_obstacle_introduced_during_movement(p9_env):
    """Scenario 11: Dynamic obstacle introduced in robot's path triggers Reflex STOP and replan."""
    mgr, _ = p9_env
    mgr.validate_and_create_order([("PROD-007", 1)], order_id="ORD-S11")
    mgr.plan_order_mission()

    # Step to (1, 1)
    mgr.execute_next_step()
    assert mgr.robot.position == Position(x=1, y=1)

    # Inject obstacle at (2, 1)
    mgr.grid.add_obstacle(2, 1)

    # Next step detects blocked next cell and replans detour
    s_ok, s_msg, _ = mgr.execute_next_step()
    assert s_ok is True
    assert mgr.robot.position == Position(x=1, y=1)  # Did not step on obstacle
    assert Position(x=2, y=1) not in mgr.current_gbfs_route


def test_scenario_12_product_unavailable_at_pickup(p9_env):
    """Scenario 12: Product unexpectedly unavailable at pickup shelf halts pickup safely."""
    mgr, _ = p9_env
    shelf = mgr.grid.get_shelf_by_id("R01")
    # Set shelf stock count to 0 unexpectedly
    shelf.current_stock_count = 0

    # Move robot to pickup position (2, 1)
    mgr.robot.position = Position(x=2, y=1)
    p_ok, p_msg = mgr.engine.executor.execute_pickup("R01", "PROD-001", quantity=1)
    assert p_ok is False
    assert "insufficient stock" in p_msg.lower()
    assert mgr.robot.current_load_kg == 0.0


def test_scenario_13_collection_at_wrong_location_rejected(p9_env):
    """Scenario 13: Collection attempted while robot is not at the shelf pickup location rejected."""
    mgr, _ = p9_env
    mgr.robot.position = Position(x=0, y=1)  # Robot is at home, not at shelf R01 pickup (2, 1)
    p_ok, p_msg = mgr.engine.executor.execute_pickup("R01", "PROD-001", quantity=1)
    assert p_ok is False
    assert "not at designated pickup position" in p_msg.lower()


def test_scenario_14_duplicate_collection_rejected(p9_env):
    """Scenario 14: Duplicate collection action with same idempotency token rejected."""
    mgr, _ = p9_env
    mgr.robot.position = Position(x=2, y=1)
    token = "PICK-IDEMP-01"

    # First pickup succeeds
    p1, _ = mgr.engine.pickup("R01", "PROD-001", 1, action_token=token)
    assert p1 is True
    load_after_first = mgr.robot.current_load_kg

    # Repeated submission of same token must not double-increment load
    p2, _ = mgr.engine.pickup("R01", "PROD-001", 1, action_token=token)
    assert p2 is True
    assert mgr.robot.current_load_kg == load_after_first


# =============================================================================
# SCENARIOS 15 - 18: Delivery, Confirmation, and Cancellations
# =============================================================================

def test_scenario_15_delivery_attempted_with_missing_items(p9_env):
    """Scenario 15: Delivery confirmation attempted before cargo is picked raises error."""
    mgr, _ = p9_env
    ok, _, oid = mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-S15")
    # Attempting to confirm delivery without picked cargo raises error
    with pytest.raises(Exception):
        mgr.order_repo.confirm_delivery(oid, total_items=1, total_weight_kg=1.8, idempotency_key="DEL-EARLY")


def test_scenario_16_duplicate_delivery_idempotent(p9_env):
    """Scenario 16: Duplicate delivery confirmation is idempotent and does not double-count."""
    mgr, _ = p9_env
    mgr.validate_and_create_order([("PROD-002", 1)], order_id="ORD-S16")
    mgr.plan_order_mission()
    mgr.run_full_mission()

    # Call confirm_delivery again with same key
    rec = mgr.order_repo.confirm_delivery("ORD-S16", total_items=1, total_weight_kg=0.8, idempotency_key="DELIV-ORD-S16")
    assert rec.total_items == 1
    assert len(mgr.order_repo.get_completed_orders()) == 1


def test_scenario_17_cancellation_before_movement(p9_env):
    """Scenario 17: Order cancellation before movement cleanly releases stock reservations."""
    mgr, _ = p9_env
    mgr.validate_and_create_order([("PROD-001", 2)], order_id="ORD-S17")
    assert mgr.inv_repo.get_stock("PROD-001").reserved == 2

    c_ok, _ = mgr.cancel_active_order()
    assert c_ok is True
    assert mgr.inv_repo.get_stock("PROD-001").reserved == 0
    assert mgr.inv_repo.get_stock("PROD-001").on_hand == 25


def test_scenario_18_cancellation_after_partial_collection(p9_env):
    """Scenario 18: Order cancellation after partial collection reconciles picked cargo to shelf."""
    mgr, _ = p9_env
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-S18")
    mgr.plan_order_mission()

    # Step through until pickup is complete (first 2 actions: NAVIGATE and COLLECT)
    while mgr.current_plan_index < 2:
        s_ok, _, _ = mgr.execute_next_step()
        if not s_ok:
            break

    assert mgr.robot.current_load_kg > 0

    # Cancel order
    c_ok, _ = mgr.cancel_active_order()
    assert c_ok is True
    assert mgr.robot.current_load_kg == 0.0
    assert mgr.inv_repo.get_stock("PROD-001").on_hand == 25
    assert mgr.inv_repo.get_stock("PROD-001").reserved == 0


# =============================================================================
# SCENARIOS 19 - 22: Min-Conflicts, Configuration, and SQLite Rollback
# =============================================================================

def test_scenario_19_min_conflicts_succeeds():
    """Scenario 19: Min-Conflicts resolves zone and capacity conflicts successfully."""
    prob = StorageAssignmentProblem(
        variables=["P1", "P2"],
        domains={"P1": ["R1", "R2"], "P2": ["R1", "R2"]},
        item_categories={"P1": "ELECTRONICS", "P2": "ACCESSORIES"},
        shelf_zones={"R1": "ELECTRONICS", "R2": "ACCESSORIES"},
        shelf_capacities={"R1": 1, "R2": 1}
    )
    res = min_conflicts(prob, initial_assignment={"P1": "R2", "P2": "R1"}, max_steps=30, seed=42)
    assert res.success is True
    assert res.final_conflicts == 0


def test_scenario_20_min_conflicts_iteration_limit():
    """Scenario 20: Min-Conflicts detects unresolvable constraints and halts at step limit."""
    # 2 items needing ZONE_A, but only 1 capacity exists in ZONE_A
    prob = StorageAssignmentProblem(
        variables=["P1", "P2"],
        domains={"P1": ["R1"], "P2": ["R1"]},
        item_categories={"P1": "ELECTRONICS", "P2": "ELECTRONICS"},
        shelf_zones={"R1": "ELECTRONICS"},
        shelf_capacities={"R1": 1}  # Shelf can only hold 1
    )
    res = min_conflicts(prob, initial_assignment={"P1": "R1", "P2": "R1"}, max_steps=10, seed=42)
    assert res.success is False
    assert res.final_conflicts > 0
    assert "iteration limit" in res.explanation.lower()


def test_scenario_21_invalid_malformed_configuration(tmp_path: Path):
    """Scenario 21: Malformed configuration file raises ConfigurationError cleanly."""
    bad_file = tmp_path / "bad_warehouse.json"
    bad_file.write_text("{ malformed_json: true }", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_warehouse_config(bad_file)


def test_scenario_22_sqlite_transaction_rollback(p9_env):
    """Scenario 22: Transaction rollback on shortage leaves zero partial reservations."""
    _, conn = p9_env
    inv_repo = InventoryRepository(conn)

    # Attempt atomic reservation for PROD-001 (has 25) and PROD-002 (request 999 - shortage)
    with pytest.raises(InsufficientStockError):
        inv_repo.reserve_order_stock(
            order_id="ORD-ROLLBACK",
            items=[("PROD-001", 5), ("PROD-002", 999)],
            idempotency_key="RES-FAIL"
        )

    # PROD-001 must have 0 reserved due to complete transaction rollback
    assert inv_repo.get_stock("PROD-001").reserved == 0


# =============================================================================
# SCENARIOS 23 - 28: Restarts, Pause/Resume, Idempotency, and Sequential Orders
# =============================================================================

def test_scenario_23_app_restart_clean_state(p9_env):
    """Scenario 23: Application restart with no active order leaves clean recovery state."""
    _, conn = p9_env
    order_repo = OrderRepository(conn)
    interrupted = order_repo.flag_interrupted_orders()
    assert interrupted == []


def test_scenario_24_app_restart_interrupted_order_recovery(p9_env):
    """Scenario 24: Application restart flags in-flight active orders as RECOVERY_REQUIRED."""
    _, conn = p9_env
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (id, status, created_at, notes)
        VALUES ('ORD-INTERRUPTED', 'IN_PROGRESS', '2026-10-21T00:00:00', 'Interrupted by app crash');
    """)
    conn.commit()

    order_repo = OrderRepository(conn)
    flagged = order_repo.flag_interrupted_orders()
    assert "ORD-INTERRUPTED" in flagged
    assert order_repo.get_order("ORD-INTERRUPTED").status == "RECOVERY_REQUIRED"


def test_scenario_25_pause_resume_during_active_order(p9_env):
    """Scenario 25: Pause and resume preserves exact coordinates and cargo during an order."""
    mgr, _ = p9_env
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-S25")
    mgr.plan_order_mission()

    mgr.execute_next_step()
    curr_pos = (mgr.robot.position.x, mgr.robot.position.y)

    mgr.engine.pause()
    assert mgr.robot.state == RobotState.PAUSED

    # Step attempt rejected while paused
    s_ok, _, _ = mgr.execute_next_step()
    assert s_ok is False
    assert (mgr.robot.position.x, mgr.robot.position.y) == curr_pos

    mgr.engine.resume()
    assert mgr.robot.state != RobotState.PAUSED


def test_scenario_26_repeated_reruns_duplicate_tokens(p9_env):
    """Scenario 26: Repeated submissions with identical action tokens return cached responses."""
    mgr, _ = p9_env
    token = "UI-RERUN-TOKEN-99"
    ok1, msg1 = mgr.engine.move(RobotDirection.SOUTH, action_token=token)
    assert ok1 is True
    dist1 = mgr.robot.distance_travelled

    # Repeated click
    ok2, msg2 = mgr.engine.move(RobotDirection.SOUTH, action_token=token)
    assert ok2 is True
    assert msg2 == msg1
    assert mgr.robot.distance_travelled == dist1


def test_scenario_27_warehouse_layout_edit_validation(p9_env):
    """Scenario 27: Warehouse layout edit validates placements and prevents invalid obstacles."""
    mgr, _ = p9_env
    # Cannot place obstacle on station (0, 0)
    can_ds, _ = mgr.grid.can_place_obstacle(0, 0)
    assert can_ds is False

    # Cannot place obstacle on robot initial (0, 1)
    can_home, _ = mgr.grid.can_place_obstacle(0, 1)
    assert can_home is False

    # Cannot place obstacle on rack (2, 2)
    can_rack, _ = mgr.grid.can_place_obstacle(2, 2)
    assert can_rack is False


def test_scenario_28_multiple_sequential_orders(p9_env):
    """Scenario 28: Sequential orders execute cleanly without stale state leakage."""
    mgr, _ = p9_env

    # Order 1: Laptop
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-SEQ-A")
    mgr.plan_order_mission()
    rep1 = mgr.run_full_mission()
    assert rep1.status == "DELIVERED"

    # Reset simulation for next order
    mgr.engine.reset(confirm=True)

    # Order 2: Keyboard & USB Cable
    mgr.validate_and_create_order([("PROD-002", 1), ("PROD-007", 2)], order_id="ORD-SEQ-B")
    mgr.plan_order_mission()
    rep2 = mgr.run_full_mission()
    assert rep2.status == "DELIVERED"
    assert rep2.items_delivered == 3

    completed = mgr.order_repo.get_completed_orders()
    assert len(completed) == 2
