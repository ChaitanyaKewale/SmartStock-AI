"""Propositional Logic Rule Evaluation Engine for SmartStock AI.

Evaluates explicit boolean clauses and logical rules for:
- Order acceptance
- Product collection permissions
- Robot payload capacity
- Delivery eligibility
- Movement safety
Returns granular condition breakdowns and human-readable explanations.
"""

from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field


class LogicEvaluationResult(BaseModel):
    """Structured report of a propositional rule evaluation."""
    rule_name: str
    result: bool
    conditions: Dict[str, bool] = Field(default_factory=dict)
    failed_conditions: List[str] = Field(default_factory=list)
    explanation: str = ""


# -----------------------------------------------------------------------------
# 1. Order Acceptance Rule
# -----------------------------------------------------------------------------

def evaluate_order_acceptance(
    has_items: bool,
    items_active: bool,
    stock_sufficient: bool,
    valid_quantities: bool
) -> LogicEvaluationResult:
    """Evaluate whether a submitted customer order satisfies acceptance constraints."""
    conditions = {
        "order_contains_items": has_items,
        "all_products_active": items_active,
        "stock_is_sufficient": stock_sufficient,
        "quantities_positive_and_valid": valid_quantities
    }

    failed = [clause for clause, val in conditions.items() if not val]
    allowed = len(failed) == 0

    if allowed:
        explanation = "Order accepted: All catalog, active status, stock, and quantity conditions satisfied."
    else:
        explanation = f"Order rejected: Failed propositional clauses: {', '.join(failed)}."

    return LogicEvaluationResult(
        rule_name="ORDER_ACCEPTANCE",
        result=allowed,
        conditions=conditions,
        failed_conditions=failed,
        explanation=explanation
    )


# -----------------------------------------------------------------------------
# 2. Product Collection Permission Rule
# -----------------------------------------------------------------------------

def evaluate_collection_permission(
    at_designated_pickup_bay: bool,
    shelf_has_stock: bool,
    within_payload_capacity: bool,
    product_matches_order: bool
) -> LogicEvaluationResult:
    """Evaluate whether the robot is permitted to collect an item from a shelf."""
    conditions = {
        "robot_at_designated_pickup_bay": at_designated_pickup_bay,
        "shelf_has_available_stock": shelf_has_stock,
        "collection_within_robot_capacity": within_payload_capacity,
        "product_matches_active_order_line": product_matches_order
    }

    failed = [clause for clause, val in conditions.items() if not val]
    allowed = len(failed) == 0

    if allowed:
        explanation = "Collection permitted: Robot positioned at pickup bay with sufficient stock, capacity, and matching order line."
    else:
        explanation = f"Collection denied: Failed clauses: {', '.join(failed)}."

    return LogicEvaluationResult(
        rule_name="COLLECTION_PERMISSION",
        result=allowed,
        conditions=conditions,
        failed_conditions=failed,
        explanation=explanation
    )


# -----------------------------------------------------------------------------
# 3. Robot Capacity Rule
# -----------------------------------------------------------------------------

def evaluate_robot_capacity(
    current_load_kg: float,
    additional_weight_kg: float,
    max_capacity_kg: float
) -> LogicEvaluationResult:
    """Evaluate whether adding items respects the physical robot weight limit."""
    new_total = current_load_kg + additional_weight_kg
    within_capacity = new_total <= max_capacity_kg

    conditions = {
        f"payload_under_limit_{max_capacity_kg}kg": within_capacity
    }

    failed = [c for c, val in conditions.items() if not val]

    if within_capacity:
        explanation = f"Capacity check passed: {new_total:.2f} kg <= {max_capacity_kg:.1f} kg limit."
    else:
        explanation = f"Capacity exceeded: {new_total:.2f} kg exceeds robot maximum of {max_capacity_kg:.1f} kg."

    return LogicEvaluationResult(
        rule_name="ROBOT_CAPACITY",
        result=within_capacity,
        conditions=conditions,
        failed_conditions=failed,
        explanation=explanation
    )


# -----------------------------------------------------------------------------
# 4. Delivery Eligibility Rule
# -----------------------------------------------------------------------------

def evaluate_delivery_eligibility(
    at_distribution_station: bool,
    all_order_items_collected: bool,
    order_in_progress: bool
) -> LogicEvaluationResult:
    """Evaluate whether delivery can be confirmed and unloaded.

    Critical invariant: Delivery cannot be confirmed merely because products
    were collected; robot MUST be at the distribution station with all items.
    """
    conditions = {
        "robot_at_distribution_station": at_distribution_station,
        "all_required_items_collected": all_order_items_collected,
        "order_state_in_progress": order_in_progress
    }

    failed = [clause for clause, val in conditions.items() if not val]
    allowed = len(failed) == 0

    if allowed:
        explanation = "Delivery confirmed: Robot at station with all required order items. Unload approved."
    else:
        explanation = f"Delivery rejected: Preconditions unmet: {', '.join(failed)}."

    return LogicEvaluationResult(
        rule_name="DELIVERY_ELIGIBILITY",
        result=allowed,
        conditions=conditions,
        failed_conditions=failed,
        explanation=explanation
    )


# -----------------------------------------------------------------------------
# 5. Movement Eligibility Rule
# -----------------------------------------------------------------------------

def evaluate_movement_eligibility(
    in_bounds: bool,
    is_walkable: bool,
    not_paused: bool
) -> LogicEvaluationResult:
    """Evaluate whether proposed robot step is permissible."""
    conditions = {
        "target_cell_in_grid_bounds": in_bounds,
        "target_cell_walkable_and_unblocked": is_walkable,
        "robot_simulation_not_paused": not_paused
    }

    failed = [clause for clause, val in conditions.items() if not val]
    allowed = len(failed) == 0

    if allowed:
        explanation = "Movement approved: Target cell is valid, walkable, and simulation is active."
    else:
        explanation = f"Movement disallowed: Failed conditions: {', '.join(failed)}."

    return LogicEvaluationResult(
        rule_name="MOVEMENT_ELIGIBILITY",
        result=allowed,
        conditions=conditions,
        failed_conditions=failed,
        explanation=explanation
    )
