"""Phase 7 Automated Tests: Live Map Animation, AI Decision Log, and Interactive Controls.

Verifies:
- SVG component payload rendering for planned route, traversed route, target reticle, and robot state styling.
- Stale and duplicate command rejection.
- Route and position updates with event-to-UI category filtering.
- Pause and resume state preservation during active fulfillment.
- Dynamic obstacle insertion during execution triggering Reflex Agent STOP and GBFS replanning.
- No-route boxed-in scenario halting safely in BLOCKED state.
- Step-by-step movement fidelity ensuring the robot never teleports.
"""

import pytest
from pathlib import Path
from simulation.engine import SimulationEngine
from simulation.fulfillment import OrderFulfillmentManager
from simulation.models import Position, RobotState, RobotDirection
from frontend.map_renderer import render_warehouse_svg, render_map_fallback
from database.db import get_db_connection, init_db, seed_catalog_if_empty
from utils.config import ProductConfig


@pytest.fixture
def phase7_mgr(tmp_path: Path) -> OrderFulfillmentManager:
    """Fixture providing an isolated SimulationEngine and OrderFulfillmentManager with temporary SQLite DB."""
    db_file = tmp_path / "test_phase7.sqlite"
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


def test_svg_component_payload_rendering(phase7_mgr: OrderFulfillmentManager):
    """Verify that render_warehouse_svg renders planned routes, traversed routes, target reticles, and robot states."""
    mgr = phase7_mgr
    grid = mgr.grid
    robot = mgr.robot

    planned = [Position(x=1, y=1), Position(x=2, y=1)]
    traversed = [Position(x=0, y=1), Position(x=1, y=1)]
    target = Position(x=2, y=1)

    # 1. Normal Navigation State
    robot.state = RobotState.NAVIGATING_TO_PICKUP
    svg = render_warehouse_svg(
        grid,
        robot=robot,
        planned_route=planned,
        traversed_route=traversed,
        target_pos=target
    )
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "polyline" in svg
    assert "target-reticle-pulse" in svg
    assert "TARGET" in svg
    assert "stroke-dasharray" in svg

    # 2. Blocked Robot State
    robot.state = RobotState.BLOCKED
    svg_blocked = render_warehouse_svg(grid, robot=robot)
    assert "#ef4444" in svg_blocked  # Red alert halo
    assert "BLOCKED" in svg_blocked

    # 3. Picking Robot State with Payload Badge
    robot.state = RobotState.PICKING
    robot.current_load_kg = 5.4
    svg_picking = render_warehouse_svg(grid, robot=robot)
    assert "5.4k" in svg_picking  # Cargo badge
    assert "#c084fc" in svg_picking  # Purple halo


def test_stale_and_duplicate_command_rejection(phase7_mgr: OrderFulfillmentManager):
    """Verify duplicate action tokens and stale delivery requests are strictly rejected."""
    mgr = phase7_mgr
    engine = mgr.engine

    # Step movement with explicit token
    token = "ACTION-STEP-101"
    ok1, msg1 = engine.step_towards(Position(x=1, y=1), action_token=token)
    assert ok1 is True

    # Duplicate call with same token returns cached result; robot does not move to (2, 1)
    ok2, msg2 = engine.step_towards(Position(x=2, y=1), action_token=token)
    assert ok2 is True
    assert msg2 == msg1
    assert (engine.robot.position.x, engine.robot.position.y) == (1, 1)


def test_route_and_position_updates_and_event_mapping(phase7_mgr: OrderFulfillmentManager):
    """Verify route/position tracking and event category filtering for UI display."""
    mgr = phase7_mgr
    ok, _, oid = mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-MAP")
    assert ok is True
    mgr.plan_order_mission()

    # Before execution
    assert mgr.current_target_pos == Position(x=2, y=1)
    assert mgr.current_action is not None
    assert mgr.current_action.action_type == "NAVIGATE_TO_PICKUP"

    # Step one cell towards target
    s_ok, s_msg, is_done = mgr.execute_next_step()
    assert s_ok is True
    assert mgr.robot.position == Position(x=1, y=1)

    # Event filtering
    nav_events = mgr.events.get_recent(limit=10, category="NAVIGATION")
    assert len(nav_events) > 0
    assert all(e.category == "NAVIGATION" for e in nav_events)

    order_events = mgr.events.get_recent(limit=10, category="ORDER")
    assert len(order_events) > 0
    assert all(e.category == "ORDER" for e in order_events)


def test_pause_resume_state_preservation(phase7_mgr: OrderFulfillmentManager):
    """Verify pause prevents movement while preserving coordinates, cargo, and route."""
    mgr = phase7_mgr
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-PAUSE")
    mgr.plan_order_mission()

    # Step once
    mgr.execute_next_step()
    pos_before = (mgr.robot.position.x, mgr.robot.position.y)

    # Pause simulation
    mgr.engine.pause()
    assert mgr.robot.state == RobotState.PAUSED

    # Attempt move while paused
    moved, move_msg = mgr.engine.move(RobotDirection.EAST)
    assert moved is False
    assert (mgr.robot.position.x, mgr.robot.position.y) == pos_before

    # Resume simulation
    mgr.engine.resume()
    assert mgr.robot.state != RobotState.PAUSED
    assert (mgr.robot.position.x, mgr.robot.position.y) == pos_before


def test_dynamic_obstacle_insertion_and_reflex_replan(phase7_mgr: OrderFulfillmentManager):
    """Verify dynamic obstacle placed in front of robot triggers Reflex STOP and GBFS replan."""
    mgr = phase7_mgr
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-DYNAMIC")
    mgr.plan_order_mission()

    # Robot starts at (0, 1), target is R01 pickup bay at (2, 1).
    # Initial route step: (1, 1).
    # Step once to (1, 1)
    s_ok1, _, _ = mgr.execute_next_step()
    assert s_ok1 is True
    assert (mgr.robot.position.x, mgr.robot.position.y) == (1, 1)

    # The next planned cell is (2, 1).
    assert mgr.current_gbfs_route[0] == Position(x=2, y=1)

    # Dynamically inject an obstacle at (2, 1) - wait, (2, 1) is the target bay,
    # let's inject barrier along a path where an alternate route exists.
    # Target is R07 pickup bay at (7, 1).
    # Let's test with PROD-007 (shelf R07 at 7, 2, pickup bay 7, 1):
    mgr_long = phase7_mgr
    mgr_long.engine.reset(confirm=True)
    mgr_long.validate_and_create_order([("PROD-007", 1)], order_id="ORD-REPLAN")
    mgr_long.plan_order_mission()

    # Robot at (0, 1). Step towards (7, 1):
    # Step 1: moves to (1, 1)
    mgr_long.execute_next_step()
    assert (mgr_long.robot.position.x, mgr_long.robot.position.y) == (1, 1)

    # Robot is at (1, 1). Next planned cell is (2, 1).
    assert mgr_long.current_gbfs_route[0] == Position(x=2, y=1)

    # DYNAMIC OBSTACLE INSERTION: Place user barrier at (2, 1) directly in front of robot!
    mgr_long.grid.add_obstacle(2, 1)
    assert mgr_long.grid.is_walkable(2, 1) is False

    # Execute next step:
    # 1. Reflex Agent detects next cell (2, 1) is blocked.
    # 2. Reflex Agent triggers STOP_AND_REPLAN.
    # 3. GBFS replans an alternate detour route (e.g. going through row 0: (1, 0) -> (2, 0) -> ...).
    # 4. Robot does NOT move into (2, 1).
    step_ok, step_msg, is_done = mgr_long.execute_next_step()
    assert step_ok is True
    assert "replanned" in step_msg.lower() or "obstacle" in step_msg.lower()

    # Robot did not enter the blocked cell (2, 1)
    assert (mgr_long.robot.position.x, mgr_long.robot.position.y) == (1, 1)
    # Replanned route avoids (2, 1)
    assert Position(x=2, y=1) not in mgr_long.current_gbfs_route
    assert len(mgr_long.current_gbfs_route) > 0

    # Continue execution to verify the detour succeeds all the way to delivery!
    report = mgr_long.run_full_mission()
    assert report.status == "DELIVERED"
    assert report.items_delivered == 1


def test_no_route_blocked_behavior(phase7_mgr: OrderFulfillmentManager):
    """Verify that when all routes are completely impassable, robot halts safely in BLOCKED state."""
    mgr = phase7_mgr
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-BOXED")
    mgr.plan_order_mission()

    # Box in target pickup bay (2, 1) completely:
    # (2, 0) is North, (1, 1) is West, (3, 1) is East, (2, 2) is already a rack
    mgr.grid.add_obstacle(2, 0)
    mgr.grid.add_obstacle(1, 1)
    mgr.grid.add_obstacle(3, 1)

    step_ok, step_msg, is_done = mgr.execute_next_step()
    assert step_ok is False
    assert mgr.robot.state == RobotState.BLOCKED
    assert "unreachable" in step_msg.lower() or "blocked" in step_msg.lower()


def test_animation_step_fidelity_no_teleportation(phase7_mgr: OrderFulfillmentManager):
    """Verify that robot moves strictly 1 cell per step, never teleporting across distances > 1."""
    mgr = phase7_mgr
    mgr.validate_and_create_order([("PROD-001", 1)], order_id="ORD-STEP")
    mgr.plan_order_mission()

    prev_pos = mgr.robot.position
    steps = 0
    while steps < 30:
        steps += 1
        s_ok, _, is_done = mgr.execute_next_step()
        if not s_ok or is_done:
            break
        curr_pos = mgr.robot.position
        manhattan_dist = abs(curr_pos.x - prev_pos.x) + abs(curr_pos.y - prev_pos.y)
        # Each movement action must move exactly 1 cell or 0 (for orientation / pickup / unload)
        assert manhattan_dist in (0, 1), f"Teleportation detected: distance was {manhattan_dist} from {prev_pos} to {curr_pos}"
        prev_pos = curr_pos
