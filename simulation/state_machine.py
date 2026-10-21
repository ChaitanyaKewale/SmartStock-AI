"""State machines and allowed transition rules for SmartStock AI.

Enforces explicit, valid state transitions for both RobotState and OrderState,
preventing invalid transitions, corrupted states, or silent failures.
"""

from __future__ import annotations

from typing import Dict, Set
from simulation.models import RobotState, OrderState


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""
    pass


# Explicit allowed transitions for RobotState
ALLOWED_ROBOT_TRANSITIONS: Dict[RobotState, Set[RobotState]] = {
    RobotState.IDLE: {
        RobotState.PLANNING,
        RobotState.PAUSED,
        RobotState.NAVIGATING_TO_PICKUP,
        RobotState.NAVIGATING_TO_DISTRIBUTION
    },
    RobotState.PLANNING: {
        RobotState.NAVIGATING_TO_PICKUP,
        RobotState.NAVIGATING_TO_DISTRIBUTION,
        RobotState.BLOCKED,
        RobotState.IDLE,
        RobotState.PAUSED
    },
    RobotState.NAVIGATING_TO_PICKUP: {
        RobotState.PICKING,
        RobotState.PAUSED,
        RobotState.BLOCKED,
        RobotState.PLANNING,
        RobotState.IDLE
    },
    RobotState.PICKING: {
        RobotState.PLANNING,
        RobotState.NAVIGATING_TO_PICKUP,
        RobotState.NAVIGATING_TO_DISTRIBUTION,
        RobotState.PAUSED,
        RobotState.BLOCKED,
        RobotState.IDLE
    },
    RobotState.NAVIGATING_TO_DISTRIBUTION: {
        RobotState.UNLOADING,
        RobotState.PAUSED,
        RobotState.BLOCKED,
        RobotState.PLANNING,
        RobotState.IDLE
    },
    RobotState.UNLOADING: {
        RobotState.COMPLETED,
        RobotState.IDLE,
        RobotState.PAUSED,
        RobotState.BLOCKED
    },
    RobotState.PAUSED: {
        RobotState.IDLE,
        RobotState.PLANNING,
        RobotState.NAVIGATING_TO_PICKUP,
        RobotState.PICKING,
        RobotState.NAVIGATING_TO_DISTRIBUTION,
        RobotState.UNLOADING,
        RobotState.BLOCKED
    },
    RobotState.BLOCKED: {
        RobotState.PLANNING,
        RobotState.PAUSED,
        RobotState.IDLE
    },
    RobotState.RECOVERY_REQUIRED: {
        RobotState.IDLE,
        RobotState.PAUSED
    },
    RobotState.COMPLETED: {
        RobotState.IDLE,
        RobotState.PLANNING
    }
}


# Explicit allowed transitions for OrderState
ALLOWED_ORDER_TRANSITIONS: Dict[OrderState, Set[OrderState]] = {
    OrderState.DRAFT: {
        OrderState.VALIDATING,
        OrderState.CANCELLED
    },
    OrderState.VALIDATING: {
        OrderState.VALIDATED,
        OrderState.REJECTED,
        OrderState.FAILED,
        OrderState.CANCELLED
    },
    OrderState.VALIDATED: {
        OrderState.PLANNING,
        OrderState.CANCELLED
    },
    OrderState.PLANNING: {
        OrderState.READY,
        OrderState.BLOCKED,
        OrderState.FAILED,
        OrderState.CANCELLED
    },
    OrderState.READY: {
        OrderState.IN_PROGRESS,
        OrderState.PAUSED,
        OrderState.CANCELLED
    },
    OrderState.IN_PROGRESS: {
        OrderState.COLLECTING,
        OrderState.RETURNING_TO_DISTRIBUTION,
        OrderState.PAUSED,
        OrderState.BLOCKED,
        OrderState.CANCELLED,
        OrderState.FAILED
    },
    OrderState.COLLECTING: {
        OrderState.IN_PROGRESS,
        OrderState.RETURNING_TO_DISTRIBUTION,
        OrderState.PAUSED,
        OrderState.BLOCKED,
        OrderState.CANCELLED,
        OrderState.FAILED
    },
    OrderState.RETURNING_TO_DISTRIBUTION: {
        OrderState.UNLOADING,
        OrderState.PAUSED,
        OrderState.BLOCKED,
        OrderState.CANCELLED,
        OrderState.FAILED
    },
    OrderState.UNLOADING: {
        OrderState.DELIVERED,
        OrderState.FAILED,
        OrderState.PAUSED
    },
    OrderState.DELIVERED: set(),  # Terminal state
    OrderState.REJECTED: {
        OrderState.DRAFT  # Allow editing rejected order
    },
    OrderState.BLOCKED: {
        OrderState.PLANNING,  # Allow replanning
        OrderState.PAUSED,
        OrderState.CANCELLED,
        OrderState.FAILED
    },
    OrderState.PAUSED: {
        OrderState.IN_PROGRESS,
        OrderState.COLLECTING,
        OrderState.RETURNING_TO_DISTRIBUTION,
        OrderState.UNLOADING,
        OrderState.CANCELLED
    },
    OrderState.FAILED: {
        OrderState.DRAFT,
        OrderState.RECOVERY_REQUIRED
    },
    OrderState.CANCELLED: set(),  # Terminal state
    OrderState.RECOVERY_REQUIRED: {
        OrderState.PAUSED,
        OrderState.CANCELLED,
        OrderState.DRAFT
    }
}


class RobotStateMachine:
    """Manages the robot lifecycle and enforces valid state transitions."""

    def __init__(self, initial_state: RobotState = RobotState.IDLE):
        self._current_state = initial_state
        self._previous_state = initial_state

    @property
    def current_state(self) -> RobotState:
        return self._current_state

    @property
    def previous_state(self) -> RobotState:
        return self._previous_state

    def can_transition_to(self, new_state: RobotState) -> bool:
        """Check if transition to new_state is permissible."""
        if self._current_state == new_state:
            return True
        allowed = ALLOWED_ROBOT_TRANSITIONS.get(self._current_state, set())
        return new_state in allowed

    def transition_to(self, new_state: RobotState) -> None:
        """Transition robot to new_state or raise InvalidStateTransitionError."""
        if self._current_state == new_state:
            return
        if not self.can_transition_to(new_state):
            raise InvalidStateTransitionError(
                f"Illegal robot state transition: {self._current_state.value} -> {new_state.value}"
            )
        self._previous_state = self._current_state
        self._current_state = new_state


class OrderStateMachine:
    """Manages the order lifecycle and enforces valid state transitions."""

    def __init__(self, initial_state: OrderState = OrderState.DRAFT):
        self._current_state = initial_state
        self._previous_state = initial_state

    @property
    def current_state(self) -> OrderState:
        return self._current_state

    @property
    def previous_state(self) -> OrderState:
        return self._previous_state

    def can_transition_to(self, new_state: OrderState) -> bool:
        """Check if transition to new_state is permissible."""
        if self._current_state == new_state:
            return True
        allowed = ALLOWED_ORDER_TRANSITIONS.get(self._current_state, set())
        return new_state in allowed

    def transition_to(self, new_state: OrderState) -> None:
        """Transition order to new_state or raise InvalidStateTransitionError."""
        if self._current_state == new_state:
            return
        if not self.can_transition_to(new_state):
            raise InvalidStateTransitionError(
                f"Illegal order state transition: {self._current_state.value} -> {new_state.value}"
            )
        self._previous_state = self._current_state
        self._current_state = new_state
