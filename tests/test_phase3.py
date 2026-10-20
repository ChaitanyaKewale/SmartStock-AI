"""Phase 3 Automated Tests: Robot Model, State Machines, Event System, and Action Executor.

Verifies:
- Explicit robot and order state machine transitions and rejection of invalid transitions.
- Cell-by-cell validated movement, boundary collision avoidance, and rack/obstacle collision avoidance.
- Pickup rules (correct pickup bay, capacity limits, stock check).
- Unload rules (must be at distribution station).
- Pause/resume state preservation.
- Reset confirmation enforcement.
- Duplicate action token protection (Streamlit rerun idempotency).
- Monotonic event ordering and event payload consistency.
"""

import pytest
from simulation.models import (
    Position,
    RobotDirection,
    RobotState,
    OrderState
)
from simulation.warehouse import get_default_warehouse
from simulation.state_machine import (
    RobotStateMachine,
    OrderStateMachine,
    InvalidStateTransitionError
)
from simulation.events import EventManager
from simulation.actions import ActionExecutor
from simulation.engine import SimulationEngine


# -----------------------------------------------------------------------------
# 1. State Machine Tests
# -----------------------------------------------------------------------------

def test_robot_state_machine_valid_transitions():
    """Verify standard happy-path lifecycle transitions for RobotState."""
    sm = RobotStateMachine(initial_state=RobotState.IDLE)
    assert sm.current_state == RobotState.IDLE

    sm.transition_to(RobotState.PLANNING)
    assert sm.current_state == RobotState.PLANNING

    sm.transition_to(RobotState.NAVIGATING_TO_PICKUP)
    assert sm.current_state == RobotState.NAVIGATING_TO_PICKUP

    sm.transition_to(RobotState.PICKING)
    assert sm.current_state == RobotState.PICKING

    sm.transition_to(RobotState.NAVIGATING_TO_DISTRIBUTION)
    assert sm.current_state == RobotState.NAVIGATING_TO_DISTRIBUTION

    sm.transition_to(RobotState.UNLOADING)
    assert sm.current_state == RobotState.UNLOADING

    sm.transition_to(RobotState.COMPLETED)
    assert sm.current_state == RobotState.COMPLETED

    sm.transition_to(RobotState.IDLE)
    assert sm.current_state == RobotState.IDLE


def test_robot_state_machine_invalid_transitions():
    """Verify that illegal transitions raise InvalidStateTransitionError and leave state unchanged."""
    sm = RobotStateMachine(initial_state=RobotState.IDLE)

    # Cannot jump directly from IDLE to UNLOADING
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(RobotState.UNLOADING)
    assert sm.current_state == RobotState.IDLE

    # Cannot jump from IDLE to COMPLETED
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(RobotState.COMPLETED)
    assert sm.current_state == RobotState.IDLE


def test_order_state_machine_valid_and_terminal_states():
    """Verify order state machine lifecycle and terminal state enforcement."""
    sm = OrderStateMachine(initial_state=OrderState.DRAFT)

    sm.transition_to(OrderState.VALIDATING)
    sm.transition_to(OrderState.VALIDATED)
    sm.transition_to(OrderState.PLANNING)
    sm.transition_to(OrderState.READY)
    sm.transition_to(OrderState.IN_PROGRESS)
    sm.transition_to(OrderState.COLLECTING)
    sm.transition_to(OrderState.RETURNING_TO_DISTRIBUTION)
    sm.transition_to(OrderState.UNLOADING)
    sm.transition_to(OrderState.DELIVERED)

    assert sm.current_state == OrderState.DELIVERED

    # DELIVERED is a terminal state; cannot transition further
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(OrderState.IN_PROGRESS)
    assert sm.current_state == OrderState.DELIVERED


# -----------------------------------------------------------------------------
# 2. Movement & Collision Avoidance Tests
# -----------------------------------------------------------------------------

def test_valid_step_movement():
    """Verify that moving into an open cell updates position, facing direction, and distance."""
    engine = SimulationEngine()
    robot = engine.robot
    assert (robot.position.x, robot.position.y) == (0, 1)
    assert robot.distance_travelled == 0

    # Step South into (0, 2)
    success, msg = engine.move(RobotDirection.SOUTH)
    assert success is True
    assert (robot.position.x, robot.position.y) == (0, 2)
    assert robot.facing == RobotDirection.SOUTH
    assert robot.distance_travelled == 1

    # Step East into (1, 2)
    success, msg = engine.move(RobotDirection.EAST)
    assert success is True
    assert (robot.position.x, robot.position.y) == (1, 2)
    assert robot.facing == RobotDirection.EAST
    assert robot.distance_travelled == 2


def test_boundary_collision_rejected():
    """Verify that moving outside the 16x12 grid is rejected without corrupting position."""
    engine = SimulationEngine()
    # Move robot to (0, 0)
    engine.move(RobotDirection.NORTH)
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 0)

    # Attempt to move West out-of-bounds (x = -1)
    dist_before = engine.robot.distance_travelled
    success, msg = engine.move(RobotDirection.WEST)
    assert success is False
    assert "outside" in msg.lower()
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 0)
    assert engine.robot.distance_travelled == dist_before

    # Attempt to move North out-of-bounds (y = -1)
    success, msg = engine.move(RobotDirection.NORTH)
    assert success is False
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 0)


def test_rack_and_obstacle_collision_rejected():
    """Verify that attempting to move into a physical storage rack or pillar is rejected."""
    engine = SimulationEngine()
    # Move robot to (2, 1), which is the pickup position for Rack R01 at (2, 2)
    engine.move(RobotDirection.EAST)  # (1, 1)
    engine.move(RobotDirection.EAST)  # (2, 1)
    assert (engine.robot.position.x, engine.robot.position.y) == (2, 1)

    # Attempt to step South directly into rack cell (2, 2)
    dist_before = engine.robot.distance_travelled
    success, msg = engine.move(RobotDirection.SOUTH)
    assert success is False
    assert "impassable" in msg.lower() or "storage rack" in msg.lower()
    assert (engine.robot.position.x, engine.robot.position.y) == (2, 1)
    assert engine.robot.distance_travelled == dist_before

    # Now test fixed pillar at (5, 5). Move robot to (5, 4)
    # Clear route from (2, 1) to (5, 4):
    engine.move(RobotDirection.EAST)  # (3, 1)
    engine.move(RobotDirection.EAST)  # (4, 1)
    engine.move(RobotDirection.EAST)  # (5, 1)
    engine.move(RobotDirection.SOUTH) # (5, 2)
    engine.move(RobotDirection.SOUTH) # (5, 3)
    engine.move(RobotDirection.SOUTH) # (5, 4)
    assert (engine.robot.position.x, engine.robot.position.y) == (5, 4)

    # Attempt to step South directly into pillar (5, 5)
    success, msg = engine.move(RobotDirection.SOUTH)
    assert success is False
    assert (engine.robot.position.x, engine.robot.position.y) == (5, 4)


# -----------------------------------------------------------------------------
# 3. Pickup and Unload Action Tests
# -----------------------------------------------------------------------------

def test_pickup_requires_correct_pickup_position():
    """Verify collection is rejected if the robot is not at the shelf's designated pickup position."""
    engine = SimulationEngine()
    # Robot is at (0, 1). Shelf R01's pickup position is (2, 1).
    success, msg = engine.pickup(shelf_id="R01", product_id="PROD-001", quantity=1)
    assert success is False
    assert "not at designated pickup position" in msg.lower()
    assert engine.robot.current_load_kg == 0.0


def test_pickup_capacity_and_success():
    """Verify successful pickup and capacity limit rejection."""
    engine = SimulationEngine()
    # Navigate to R01's pickup position at (2, 1)
    engine.move(RobotDirection.EAST)  # (1, 1)
    engine.move(RobotDirection.EAST)  # (2, 1)

    # PROD-001 unit weight is 1.8 kg
    success, msg = engine.pickup(shelf_id="R01", product_id="PROD-001", quantity=1)
    assert success is True
    assert engine.robot.current_load_kg == pytest.approx(1.8)
    assert engine.robot.carried_items.get("PROD-001") == 1

    # Attempt to pick 20 more units (20 * 1.8 = 36 kg, total = 37.8 > 25 kg capacity)
    success, msg = engine.pickup(shelf_id="R01", product_id="PROD-001", quantity=20)
    assert success is False
    assert "capacity" in msg.lower()
    assert engine.robot.current_load_kg == pytest.approx(1.8)


def test_unload_requires_distribution_station():
    """Verify unloading is rejected if not at the distribution station."""
    engine = SimulationEngine()
    # Robot at (0, 1), not at station (0, 0)
    success, msg = engine.unload()
    assert success is False
    assert "not at the distribution station" in msg.lower()

    # Move to station (0, 0)
    engine.move(RobotDirection.NORTH)
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 0)
    success, msg = engine.unload()
    assert success is True


# -----------------------------------------------------------------------------
# 4. Lifecycle Controls: Pause, Resume, Reset
# -----------------------------------------------------------------------------

def test_pause_resume_state_preservation():
    """Verify pause preserves position and load, and blocks movement until resumed."""
    engine = SimulationEngine()
    engine.move(RobotDirection.SOUTH)  # (0, 2)
    engine.robot.current_load_kg = 5.5

    # Pause
    success, _ = engine.pause()
    assert success is True
    assert engine.robot.state == RobotState.PAUSED

    # Movement while paused must be rejected
    m_success, m_msg = engine.move(RobotDirection.EAST)
    assert m_success is False
    assert "paused" in m_msg.lower()
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 2)

    # Resume
    r_success, _ = engine.resume()
    assert r_success is True
    assert engine.robot.state != RobotState.PAUSED
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 2)
    assert engine.robot.current_load_kg == 5.5


def test_reset_requires_confirmation():
    """Verify that simulation reset rejects unconfirmed requests and cleanly restores state on confirmation."""
    engine = SimulationEngine()
    engine.move(RobotDirection.SOUTH)
    engine.move(RobotDirection.EAST)
    assert engine.robot.distance_travelled == 2

    # Attempt reset without confirmation
    success, msg = engine.reset(confirm=False)
    assert success is False
    assert "confirmation required" in msg.lower()
    assert engine.robot.distance_travelled == 2

    # Reset with confirmation
    success, msg = engine.reset(confirm=True)
    assert success is True
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 1)
    assert engine.robot.facing == RobotDirection.SOUTH
    assert engine.robot.state == RobotState.IDLE
    assert engine.robot.distance_travelled == 0
    assert engine.robot.current_load_kg == 0.0


# -----------------------------------------------------------------------------
# 5. Rerun Idempotency & Monotonic Events
# -----------------------------------------------------------------------------

def test_action_token_deduplication():
    """Verify that repeated submission of identical action tokens does not duplicate actions."""
    engine = SimulationEngine()
    token = "UI-CLICK-STEP-101"

    # First execution moves robot
    success1, msg1 = engine.move(RobotDirection.SOUTH, action_token=token)
    assert success1 is True
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 2)
    dist_after_first = engine.robot.distance_travelled

    # Second execution with same token (simulating Streamlit widget rerun)
    success2, msg2 = engine.move(RobotDirection.SOUTH, action_token=token)
    assert success2 is True
    assert msg2 == msg1
    # Robot must NOT have moved a second time
    assert (engine.robot.position.x, engine.robot.position.y) == (0, 2)
    assert engine.robot.distance_travelled == dist_after_first


def test_event_monotonicity_and_payload():
    """Verify all events have strictly increasing IDs and complete metadata."""
    engine = SimulationEngine()
    engine.move(RobotDirection.SOUTH)
    engine.move(RobotDirection.EAST)
    engine.pause()
    engine.resume()

    events = engine.events.events
    assert len(events) >= 5

    # Check strictly increasing IDs: 1, 2, 3, ...
    for idx, ev in enumerate(events):
        assert ev.event_id == idx + 1
        assert len(ev.timestamp) > 0
        assert len(ev.category) > 0
        assert len(ev.action) > 0
        assert len(ev.outcome) > 0
        assert len(ev.explanation) > 0
