"""Validated action executor for SmartStock AI robot and order operations.

Guarantees:
- Cell-by-cell validated movement
- Rejection of moves into blocked cells, racks, obstacles, or boundaries
- Atomic pickup, unloading, pause, resume, and cancellation actions
- Prevention of partial state corruption on failed actions
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple, Any
from simulation.models import (
    Position,
    Robot,
    RobotDirection,
    RobotState,
    Order,
    OrderState
)
from simulation.warehouse import WarehouseGrid
from simulation.state_machine import (
    RobotStateMachine,
    OrderStateMachine,
    InvalidStateTransitionError
)
from simulation.events import EventManager


class ActionExecutor:
    """Executes validated, atomic actions on the robot and warehouse simulation."""

    def __init__(
        self,
        grid: WarehouseGrid,
        robot: Robot,
        event_manager: EventManager,
        robot_sm: RobotStateMachine,
        order_sm: Optional[OrderStateMachine] = None
    ):
        self.grid = grid
        self.robot = robot
        self.events = event_manager
        self.robot_sm = robot_sm
        self.order_sm = order_sm or OrderStateMachine()
        self.traversed_path: list[Position] = [Position(x=robot.position.x, y=robot.position.y)]

    # -------------------------------------------------------------------------
    # Movement Action
    # -------------------------------------------------------------------------

    def move_step(self, direction: RobotDirection) -> Tuple[bool, str]:
        """Move the robot exactly one cell in the specified direction.

        Checks:
        - Target cell must be in bounds.
        - Target cell must be walkable (not a rack, obstacle, or restricted zone).

        Returns:
            (success, explanation_message)
        """
        # Ensure robot is in an active movement state or IDLE/PLANNING
        if self.robot.state == RobotState.PAUSED:
            msg = "Action rejected: Robot is currently PAUSED. Resume to move."
            self.events.log("NAVIGATION", "MOVE_STEP", "REJECTED", msg, position=self.robot.position)
            return False, msg

        dx, dy = direction.delta
        target_x = self.robot.position.x + dx
        target_y = self.robot.position.y + dy

        # Update facing direction regardless of move outcome (robot turns to face direction)
        self.robot.facing = direction

        # 1. Boundary Check
        if not self.grid.in_bounds(target_x, target_y):
            msg = f"Movement blocked: Target ({target_x}, {target_y}) is outside warehouse boundaries."
            self.events.log("NAVIGATION", f"MOVE_{direction.value}", "BLOCKED", msg, position=self.robot.position)
            return False, msg

        target_pos = Position(x=target_x, y=target_y)

        # 2. Obstacle / Rack / Zone Walkability Check
        if not self.grid.is_walkable(target_x, target_y):
            reason = "storage rack" if self.grid.is_rack(target_x, target_y) else "obstacle barrier or hazard"
            msg = f"Movement blocked: Target ({target_x}, {target_y}) is impassable ({reason})."
            self.events.log("NAVIGATION", f"MOVE_{direction.value}", "BLOCKED", msg, position=self.robot.position)
            return False, msg

        # 3. Successful Atomic Move
        prev_pos = self.robot.position
        self.robot.position = target_pos
        self.robot.distance_travelled += 1
        self.traversed_path.append(target_pos)

        msg = f"Robot moved 1 step {direction.value} from ({prev_pos.x}, {prev_pos.y}) to ({target_x}, {target_y})."
        self.events.log("NAVIGATION", f"MOVE_{direction.value}", "SUCCESS", msg, position=target_pos)
        return True, msg

    def step_towards(self, target: Position) -> Tuple[bool, str]:
        """Move exactly one cell towards adjacent target position."""
        if not self.robot.position.is_adjacent_to(target):
            msg = f"Invalid step: Target ({target.x}, {target.y}) is not adjacent to current position ({self.robot.position.x}, {self.robot.position.y})."
            self.events.log("NAVIGATION", "STEP_TOWARDS", "REJECTED", msg, position=self.robot.position)
            return False, msg

        dx = target.x - self.robot.position.x
        dy = target.y - self.robot.position.y

        direction: RobotDirection
        if dx == 1:
            direction = RobotDirection.EAST
        elif dx == -1:
            direction = RobotDirection.WEST
        elif dy == 1:
            direction = RobotDirection.SOUTH
        else:
            direction = RobotDirection.NORTH

        return self.move_step(direction)

    # -------------------------------------------------------------------------
    # Collection / Pickup Action
    # -------------------------------------------------------------------------

    def execute_pickup(self, shelf_id: str, product_id: str, quantity: int = 1) -> Tuple[bool, str]:
        """Pick an item from the shelf while obeying capacity and location rules."""
        shelf = self.grid.get_shelf_by_id(shelf_id)
        if not shelf:
            msg = f"Pickup failed: Shelf {shelf_id} does not exist."
            self.events.log("ACTION", "PICKUP", "FAILED", msg, position=self.robot.position)
            return False, msg

        # Precondition 1: Robot must be at the designated pickup position
        if (self.robot.position.x, self.robot.position.y) != (shelf.pickup_position.x, shelf.pickup_position.y):
            msg = (
                f"Pickup rejected: Robot at ({self.robot.position.x}, {self.robot.position.y}) is not at "
                f"designated pickup position ({shelf.pickup_position.x}, {shelf.pickup_position.y}) for shelf {shelf_id}."
            )
            self.events.log("ACTION", "PICKUP", "REJECTED", msg, position=self.robot.position)
            return False, msg

        # Precondition 2: Product must exist
        prod = self.grid.products_by_id.get(product_id)
        if not prod:
            msg = f"Pickup failed: Product {product_id} is not registered in catalog."
            self.events.log("ACTION", "PICKUP", "FAILED", msg, position=self.robot.position)
            return False, msg

        # Precondition 3: Weight and capacity validation
        item_weight = prod.unit_weight_kg * quantity
        if self.robot.current_load_kg + item_weight > self.robot.max_capacity_kg:
            msg = (
                f"Pickup rejected: Adding {item_weight:.2f} kg exceeds robot capacity "
                f"({self.robot.current_load_kg:.2f} + {item_weight:.2f} > {self.robot.max_capacity_kg:.2f} kg)."
            )
            self.events.log("ACTION", "PICKUP", "REJECTED", msg, position=self.robot.position)
            return False, msg

        # Precondition 4: Stock availability on shelf
        if shelf.current_stock_count < quantity:
            msg = f"Pickup failed: Shelf {shelf_id} has insufficient stock ({shelf.current_stock_count} < {quantity})."
            self.events.log("ACTION", "PICKUP", "FAILED", msg, position=self.robot.position)
            return False, msg

        # Commit Pickup
        shelf.current_stock_count -= quantity
        self.robot.current_load_kg += item_weight
        self.robot.carried_items[product_id] = self.robot.carried_items.get(product_id, 0) + quantity

        msg = f"Collected {quantity}x {prod.name} ({product_id}) from {shelf_id}. Current payload: {self.robot.current_load_kg:.2f} kg."
        self.events.log("ACTION", "PICKUP", "SUCCESS", msg, position=self.robot.position)
        return True, msg

    # -------------------------------------------------------------------------
    # Unloading / Distribution Action
    # -------------------------------------------------------------------------

    def execute_unload(self) -> Tuple[bool, str]:
        """Unload robot payload at the distribution station."""
        ds = self.grid.distribution_station
        if (self.robot.position.x, self.robot.position.y) != (ds.x, ds.y):
            msg = (
                f"Unload rejected: Robot at ({self.robot.position.x}, {self.robot.position.y}) is not at "
                f"the distribution station ({ds.x}, {ds.y})."
            )
            self.events.log("ACTION", "UNLOAD", "REJECTED", msg, position=self.robot.position)
            return False, msg

        if not self.robot.carried_items:
            msg = "Unload notice: Robot cargo bay is already empty."
            self.events.log("ACTION", "UNLOAD", "INFO", msg, position=self.robot.position)
            return True, msg

        total_items = sum(self.robot.carried_items.values())
        unloaded_weight = self.robot.current_load_kg
        self.robot.carried_items.clear()
        self.robot.current_load_kg = 0.0

        msg = f"Successfully unloaded {total_items} items ({unloaded_weight:.2f} kg) at Distribution Station DS-01."
        self.events.log("ACTION", "UNLOAD", "SUCCESS", msg, position=self.robot.position)
        return True, msg

    # -------------------------------------------------------------------------
    # Lifecycle Controls: Pause, Resume, Reset
    # -------------------------------------------------------------------------

    def pause(self) -> Tuple[bool, str]:
        """Pause active operations while preserving robot position, load, and target."""
        if self.robot.state == RobotState.PAUSED:
            return True, "Simulation is already paused."

        try:
            self.robot_sm.transition_to(RobotState.PAUSED)
            self.robot.state = RobotState.PAUSED
            msg = f"Simulation paused at tick position ({self.robot.position.x}, {self.robot.position.y}). State preserved."
            self.events.log("SYSTEM", "PAUSE", "SUCCESS", msg, position=self.robot.position)
            return True, msg
        except InvalidStateTransitionError as err:
            self.events.log("SYSTEM", "PAUSE", "FAILED", str(err), position=self.robot.position)
            return False, str(err)

    def resume(self) -> Tuple[bool, str]:
        """Resume execution from paused state."""
        if self.robot.state != RobotState.PAUSED:
            return True, "Simulation is not paused."

        prev = self.robot_sm.previous_state
        target_state = prev if prev != RobotState.PAUSED else RobotState.IDLE
        try:
            self.robot_sm.transition_to(target_state)
            self.robot.state = target_state
            msg = f"Simulation resumed to state {target_state.value}."
            self.events.log("SYSTEM", "RESUME", "SUCCESS", msg, position=self.robot.position)
            return True, msg
        except InvalidStateTransitionError as err:
            self.events.log("SYSTEM", "RESUME", "FAILED", str(err), position=self.robot.position)
            return False, str(err)

    def reset(self, confirm: bool = False) -> Tuple[bool, str]:
        """Reset robot to home station without destroying persistent order records."""
        if not confirm:
            msg = "Reset rejected: Explicit user confirmation required to reset simulation."
            self.events.log("SYSTEM", "RESET", "REJECTED", msg, position=self.robot.position)
            return False, msg

        # Reset robot properties to home
        init_pos = self.grid.robot_initial.position
        self.robot.position = Position(x=init_pos.x, y=init_pos.y)
        self.robot.facing = self.grid.robot_initial.facing
        self.robot.current_load_kg = 0.0
        self.robot.carried_items.clear()
        self.robot.target = None
        self.robot.route.clear()
        self.robot.route_progress = 0
        self.robot.distance_travelled = 0
        self.traversed_path = [Position(x=init_pos.x, y=init_pos.y)]

        self.robot_sm._current_state = RobotState.IDLE
        self.robot.state = RobotState.IDLE

        msg = f"Simulation reset confirmed. Robot returned to home station ({init_pos.x}, {init_pos.y})."
        self.events.log("SYSTEM", "RESET", "SUCCESS", msg, position=self.robot.position)
        return True, msg
