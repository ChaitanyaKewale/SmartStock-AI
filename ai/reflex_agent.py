"""Simple Reflex Agent for SmartStock AI.

Evaluates immediate sensory percepts against condition-action rules for
live obstacle detection, safety stops, and action validation triggers.
Does not replace the planner or bypass Python simulation validation.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel
from simulation.models import Position, RobotDirection


class Percept(BaseModel):
    """Sensory inputs perceived by the robot at a single simulation tick."""
    current_position: Position
    facing: RobotDirection
    proposed_next_cell: Optional[Position] = None
    is_next_cell_in_bounds: bool = True
    is_next_cell_blocked: bool = False
    at_pickup_location: bool = False
    pickup_preconditions_valid: bool = False
    all_products_collected: bool = False
    at_distribution_station: bool = False
    delivery_preconditions_valid: bool = False


class ReflexAction(BaseModel):
    """Action recommendation and justification emitted by the reflex agent."""
    action: str
    reason: str
    rule_name: str


class SimpleReflexAgent:
    """Condition-action rule engine responding immediately to environmental percepts."""

    def evaluate(self, percept: Percept) -> ReflexAction:
        """Inspect percepts and return the highest-priority triggered condition-action rule."""

        # Rule 1 (Highest Priority - Immediate Safety / Obstacle Collision)
        if percept.proposed_next_cell is not None:
            if not percept.is_next_cell_in_bounds or percept.is_next_cell_blocked:
                return ReflexAction(
                    action="STOP_AND_REPLAN",
                    reason="Proposed next cell is obstructed by obstacle or out-of-bounds. Immediate stop required.",
                    rule_name="RULE_1_OBSTACLE_AVOIDANCE"
                )

        # Rule 2 (Pickup Validation Rejection)
        if percept.at_pickup_location and not percept.pickup_preconditions_valid:
            return ReflexAction(
                action="REJECT_PICKUP",
                reason="Robot is at pickup bay, but preconditions (stock, capacity, or order match) failed.",
                rule_name="RULE_2_PICKUP_REJECT"
            )

        # Rule 3 (Pickup Approval)
        if percept.at_pickup_location and percept.pickup_preconditions_valid:
            return ReflexAction(
                action="REQUEST_PICKUP",
                reason="Robot is at target pickup bay with valid preconditions. Proceed with collection.",
                rule_name="RULE_3_PICKUP_APPROVE"
            )

        # Rule 4 (Delivery Validation Rejection)
        if percept.at_distribution_station and not percept.delivery_preconditions_valid:
            return ReflexAction(
                action="REJECT_DELIVERY",
                reason="Robot is at distribution station, but delivery conditions (missing items or state mismatch) failed.",
                rule_name="RULE_4_DELIVERY_REJECT"
            )

        # Rule 5 (Delivery Approval)
        if percept.at_distribution_station and percept.delivery_preconditions_valid:
            return ReflexAction(
                action="REQUEST_DELIVERY",
                reason="Robot is at distribution station with all required cargo verified. Proceed with delivery.",
                rule_name="RULE_5_DELIVERY_APPROVE"
            )

        # Rule 6 (Return to Distribution Station Trigger)
        if percept.all_products_collected and not percept.at_distribution_station:
            return ReflexAction(
                action="REQUEST_RETURN_TO_STATION",
                reason="All order products collected. Route return to Distribution Station.",
                rule_name="RULE_6_RETURN_TRIGGER"
            )

        # Rule 7 (Clear Movement Approval)
        if percept.proposed_next_cell is not None:
            if percept.is_next_cell_in_bounds and not percept.is_next_cell_blocked:
                return ReflexAction(
                    action="ALLOW_MOVEMENT",
                    reason="Target aisle cell is clear and in-bounds. Movement permitted.",
                    rule_name="RULE_7_MOVEMENT_ALLOW"
                )

        # Default Fallback Rule
        return ReflexAction(
            action="MAINTAIN_STATE",
            reason="No immediate reactive condition triggered. Continue baseline mission execution.",
            rule_name="RULE_DEFAULT_MAINTAIN"
        )
