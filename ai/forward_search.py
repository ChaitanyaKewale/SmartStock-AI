"""Forward State-Space Search Planner for SmartStock AI.

Plans high-level mission action sequences (Navigate -> Collect -> Return -> Deliver)
using explicit state representations, goal testing, and visited-state tracking.
Does not mutate the live simulation state.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from simulation.models import Position
from simulation.warehouse import WarehouseGrid


class HighLevelAction(BaseModel):
    """An individual discrete step in the high-level fulfillment mission plan."""
    action_type: str  # NAVIGATE_TO_PICKUP, COLLECT_PRODUCT, NAVIGATE_TO_STATION, DELIVER_ORDER
    target_pos: Position
    shelf_id: Optional[str] = None
    product_id: Optional[str] = None
    quantity: int = 0
    description: str = ""


class ForwardSearchResult(BaseModel):
    """Structured report returned by the forward state-space mission planner."""
    success: bool
    plan: List[HighLevelAction] = Field(default_factory=list)
    expanded_states: int = 0
    explanation: str = ""


class PlannerState:
    """Immutable, hashable representation of the high-level mission state."""

    def __init__(
        self,
        robot_coord: Tuple[int, int],
        remaining_items: Tuple[Tuple[str, int], ...],
        delivered: bool
    ):
        self.robot_coord = robot_coord
        self.remaining_items = remaining_items
        self.delivered = delivered

    def __hash__(self) -> int:
        return hash((self.robot_coord, self.remaining_items, self.delivered))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PlannerState):
            return False
        return (
            self.robot_coord == other.robot_coord
            and self.remaining_items == other.remaining_items
            and self.delivered == other.delivered
        )


def forward_state_space_search(
    grid: WarehouseGrid,
    initial_robot_pos: Position,
    order_items: Dict[str, int],  # product_id -> quantity
    max_expansions: int = 500
) -> ForwardSearchResult:
    """Synthesize a complete mission plan from initial state to confirmed delivery.

    Goal Requirements:
    - All requested order items must be collected.
    - Robot must return to the Distribution Station.
    - Final delivery action must be executed at the station.
    """
    # 1. Edge Case: Empty order
    if not order_items:
        return ForwardSearchResult(
            success=False,
            explanation="Forward search rejected: Order contains zero items to plan for."
        )

    station_coord = (grid.distribution_station.x, grid.distribution_station.y)

    # Validate that all items exist in catalog and have accessible pickup positions
    item_shelves: Dict[str, str] = {}
    item_pickups: Dict[str, Tuple[int, int]] = {}

    for prod_id, qty in order_items.items():
        if qty <= 0:
            return ForwardSearchResult(
                success=False,
                explanation=f"Forward search rejected: Invalid quantity ({qty}) for product {prod_id}."
            )
        prod = grid.products_by_id.get(prod_id)
        if not prod:
            return ForwardSearchResult(
                success=False,
                explanation=f"Forward search failed: Product {prod_id} not found in catalog."
            )
        shelf = grid.get_shelf_by_id(prod.shelf_id)
        if not shelf:
            return ForwardSearchResult(
                success=False,
                explanation=f"Forward search failed: Storage shelf {prod.shelf_id} not found for {prod_id}."
            )
        pp = shelf.pickup_position
        if not grid.is_walkable(pp.x, pp.y):
            return ForwardSearchResult(
                success=False,
                explanation=f"Forward search failed: Pickup bay ({pp.x}, {pp.y}) for shelf {shelf.id} is blocked."
            )
        item_shelves[prod_id] = shelf.id
        item_pickups[prod_id] = (pp.x, pp.y)

    # Initial State setup
    init_remaining = tuple(sorted(order_items.items()))
    init_state = PlannerState(
        robot_coord=(initial_robot_pos.x, initial_robot_pos.y),
        remaining_items=init_remaining,
        delivered=False
    )

    # Queue of (state, action_history)
    queue: deque[Tuple[PlannerState, List[HighLevelAction]]] = deque([(init_state, [])])
    visited: Set[PlannerState] = set([init_state])
    expanded_count = 0

    # 2. Forward Progression Search Loop
    while queue and expanded_count < max_expansions:
        state, plan = queue.popleft()
        expanded_count += 1

        # Goal test: All items collected AND at distribution station AND delivered == True
        if len(state.remaining_items) == 0 and state.robot_coord == station_coord and state.delivered:
            return ForwardSearchResult(
                success=True,
                plan=plan,
                expanded_states=expanded_count,
                explanation=(
                    f"Synthesized high-level plan with {len(plan)} actions: "
                    f"collected {len(order_items)} items, returned to station, and confirmed delivery."
                )
            )

        # Successor generation
        # Case A: There are remaining items to collect
        if state.remaining_items:
            for prod_id, qty in state.remaining_items:
                target_pickup = item_pickups[prod_id]
                shelf_id = item_shelves[prod_id]

                # If robot is not yet at pickup bay -> action: NAVIGATE_TO_PICKUP
                if state.robot_coord != target_pickup:
                    nav_action = HighLevelAction(
                        action_type="NAVIGATE_TO_PICKUP",
                        target_pos=Position(x=target_pickup[0], y=target_pickup[1]),
                        shelf_id=shelf_id,
                        product_id=prod_id,
                        description=f"Navigate to {shelf_id} pickup bay at ({target_pickup[0]}, {target_pickup[1]})."
                    )
                    next_state = PlannerState(
                        robot_coord=target_pickup,
                        remaining_items=state.remaining_items,
                        delivered=False
                    )
                    if next_state not in visited:
                        visited.add(next_state)
                        queue.append((next_state, plan + [nav_action]))

                # If robot IS at pickup bay -> action: COLLECT_PRODUCT
                else:
                    collect_action = HighLevelAction(
                        action_type="COLLECT_PRODUCT",
                        target_pos=Position(x=target_pickup[0], y=target_pickup[1]),
                        shelf_id=shelf_id,
                        product_id=prod_id,
                        quantity=qty,
                        description=f"Collect {qty}x {prod_id} from shelf {shelf_id}."
                    )
                    # Remove collected product from remaining
                    new_remaining = tuple(item for item in state.remaining_items if item[0] != prod_id)
                    next_state = PlannerState(
                        robot_coord=target_pickup,
                        remaining_items=new_remaining,
                        delivered=False
                    )
                    if next_state not in visited:
                        visited.add(next_state)
                        queue.append((next_state, plan + [collect_action]))

        # Case B: All items collected; navigate to Distribution Station
        elif state.robot_coord != station_coord:
            return_action = HighLevelAction(
                action_type="NAVIGATE_TO_STATION",
                target_pos=Position(x=station_coord[0], y=station_coord[1]),
                shelf_id=None,
                description=f"Return to Distribution Station at ({station_coord[0]}, {station_coord[1]})."
            )
            next_state = PlannerState(
                robot_coord=station_coord,
                remaining_items=tuple(),
                delivered=False
            )
            if next_state not in visited:
                visited.add(next_state)
                queue.append((next_state, plan + [return_action]))

        # Case C: At distribution station with all items -> action: DELIVER_ORDER
        elif not state.delivered:
            deliver_action = HighLevelAction(
                action_type="DELIVER_ORDER",
                target_pos=Position(x=station_coord[0], y=station_coord[1]),
                description="Unload cargo and confirm delivery transaction at Distribution Station."
            )
            next_state = PlannerState(
                robot_coord=station_coord,
                remaining_items=tuple(),
                delivered=True
            )
            if next_state not in visited:
                visited.add(next_state)
                queue.append((next_state, plan + [deliver_action]))

    return ForwardSearchResult(
        success=False,
        plan=[],
        expanded_states=expanded_count,
        explanation=f"Forward state-space search exceeded search boundary ({max_expansions} states) without finding a complete plan."
    )
