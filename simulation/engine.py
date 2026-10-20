"""Authoritative simulation coordinator for SmartStock AI.

Owns the warehouse grid, robot, event system, and action executor.
Enforces tick advancement, idempotency, and Streamlit rerun action deduplication.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from simulation.models import (
    Position,
    Robot,
    RobotDirection,
    RobotState,
    Order,
    OrderState
)
from simulation.warehouse import WarehouseGrid, get_default_warehouse
from simulation.state_machine import RobotStateMachine, OrderStateMachine
from simulation.events import EventManager
from simulation.actions import ActionExecutor


class SimulationEngine:
    """Coordinates simulation ticks, authoritative updates, and action deduplication."""

    def __init__(self, warehouse: Optional[WarehouseGrid] = None):
        self.warehouse = warehouse or get_default_warehouse()
        self.events = EventManager()

        # Robot clone initialized from warehouse start
        init_r = self.warehouse.robot_initial
        self.robot = Robot(
            id=init_r.id,
            name=init_r.name,
            position=Position(x=init_r.position.x, y=init_r.position.y),
            facing=init_r.facing,
            max_capacity_kg=init_r.max_capacity_kg,
            state=RobotState.IDLE
        )

        self.robot_sm = RobotStateMachine(initial_state=RobotState.IDLE)
        self.order_sm = OrderStateMachine(initial_state=OrderState.DRAFT)
        self.active_order: Optional[Order] = None

        self.executor = ActionExecutor(
            grid=self.warehouse,
            robot=self.robot,
            event_manager=self.events,
            robot_sm=self.robot_sm,
            order_sm=self.order_sm
        )

        self.tick: int = 0
        # Idempotency token cache: action_token -> (success, message)
        self._processed_tokens: Dict[str, Tuple[bool, str]] = {}

        # Initial startup log
        self.events.log(
            "SYSTEM",
            "INITIALIZE",
            "SUCCESS",
            f"SimulationEngine online. Robot {self.robot.id} stationed at ({self.robot.position.x}, {self.robot.position.y}).",
            position=self.robot.position
        )

    # -------------------------------------------------------------------------
    # Idempotent Execution Wrapper (Duplicate Rerun Protection)
    # -------------------------------------------------------------------------

    def _execute_idempotent(
        self,
        token: Optional[str],
        action_name: str,
        func,
        *args,
        **kwargs
    ) -> Tuple[bool, str]:
        """Execute action once; if token is seen again, return cached result to prevent duplicate rerun side effects."""
        if token and token in self._processed_tokens:
            cached_result = self._processed_tokens[token]
            return cached_result

        success, msg = func(*args, **kwargs)
        self.tick += 1

        if token:
            self._processed_tokens[token] = (success, msg)
        return success, msg

    # -------------------------------------------------------------------------
    # High-level Operations
    # -------------------------------------------------------------------------

    def move(self, direction: RobotDirection, action_token: Optional[str] = None) -> Tuple[bool, str]:
        """Move robot one cell in the specified direction."""
        return self._execute_idempotent(
            action_token,
            f"MOVE_{direction.value}",
            self.executor.move_step,
            direction
        )

    def step_towards(self, target: Position, action_token: Optional[str] = None) -> Tuple[bool, str]:
        """Step one adjacent cell towards target position."""
        return self._execute_idempotent(
            action_token,
            "STEP_TOWARDS",
            self.executor.step_towards,
            target
        )

    def pickup(
        self,
        shelf_id: str,
        product_id: str,
        quantity: int = 1,
        action_token: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Perform validated item pickup at current location."""
        return self._execute_idempotent(
            action_token,
            "PICKUP",
            self.executor.execute_pickup,
            shelf_id,
            product_id,
            quantity
        )

    def unload(self, action_token: Optional[str] = None) -> Tuple[bool, str]:
        """Perform cargo unloading at distribution station."""
        return self._execute_idempotent(
            action_token,
            "UNLOAD",
            self.executor.execute_unload
        )

    def pause(self) -> Tuple[bool, str]:
        """Pause active operations."""
        return self.executor.pause()

    def resume(self) -> Tuple[bool, str]:
        """Resume active operations."""
        return self.executor.resume()

    def reset(self, confirm: bool = False) -> Tuple[bool, str]:
        """Reset robot and simulation state."""
        success, msg = self.executor.reset(confirm=confirm)
        if success:
            self.tick = 0
            self._processed_tokens.clear()
        return success, msg
