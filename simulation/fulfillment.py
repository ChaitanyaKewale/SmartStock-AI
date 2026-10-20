"""End-to-End Order Fulfillment Orchestrator for SmartStock AI.

Integrates all six AI syllabus algorithms with the simulation core and SQLite persistence:
1. Logical Predicate Unification for SKU and storage bay resolution
2. Propositional Logic for order acceptance and action preconditions
3. Min-Conflicts for storage allocation optimization
4. Forward State-Space Search for high-level task planning
5. Greedy Best-First Search for cell-by-cell pathfinding
6. Simple Reflex Agent for live percept inspection and obstacle handling
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

from simulation.models import (
    Position,
    RobotDirection,
    RobotState,
    OrderState
)
from simulation.warehouse import WarehouseGrid
from simulation.engine import SimulationEngine
from database.db import get_db_connection
from database.repositories import (
    InventoryRepository,
    OrderRepository,
    InsufficientStockError,
    DeliveryError
)

# AI Concepts
from ai.unification import (
    Variable,
    Constant,
    Predicate,
    resolve_product_predicate
)
from ai.propositional_logic import (
    evaluate_order_acceptance,
    evaluate_collection_permission,
    evaluate_delivery_eligibility,
    evaluate_robot_capacity
)
from ai.min_conflicts import (
    StorageAssignmentProblem,
    min_conflicts
)
from ai.greedy_best_first import greedy_best_first_search, GBFSResult
from ai.forward_search import forward_state_space_search, HighLevelAction, ForwardSearchResult
from ai.reflex_agent import SimpleReflexAgent, Percept, ReflexAction


class FulfillmentReport(BaseModel):
    """Detailed completion summary of an order fulfillment run."""
    order_id: str
    status: str
    items_delivered: int
    total_weight_kg: float
    steps_travelled: int
    plan_actions_count: int
    replans_triggered: int
    explanation: str


class OrderFulfillmentManager:
    """Orchestrates end-to-end order processing, AI algorithm invocations, and database sync."""

    def __init__(self, engine: SimulationEngine, db_path: Optional[str] = None):
        self.engine = engine
        self.grid = engine.warehouse
        self.robot = engine.robot
        self.events = engine.events
        self.reflex_agent = SimpleReflexAgent()

        # Database connections and repositories
        self.conn = get_db_connection(db_path)
        self.inv_repo = InventoryRepository(self.conn)
        self.order_repo = OrderRepository(self.conn)

        # Active mission state
        self.active_order_id: Optional[str] = None
        self.active_order_lines: List[Dict[str, Any]] = []
        self.high_level_plan: List[HighLevelAction] = []
        self.current_plan_index: int = 0
        self.current_gbfs_route: List[Position] = []
        self.replans_count: int = 0

    # -------------------------------------------------------------------------
    # 1. Validation & Unification & Acceptance
    # -------------------------------------------------------------------------

    def validate_and_create_order(
        self,
        requested_items: List[Tuple[str, int]],  # (product_id, quantity)
        order_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Validate an order request using Unification, Propositional Logic, and SQLite reservations."""
        if not requested_items:
            msg = "Validation rejected: Order cannot be empty."
            self.events.log("ORDER", "VALIDATION", "REJECTED", msg)
            return False, msg, None

        oid = order_id or f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # 1. Unification: Resolve each product to catalog facts and pickup locations
        catalog_facts = [
            Predicate("Item", (Constant(p.id), Constant(p.category), Constant(p.shelf_id)))
            for p in self.grid.products_by_id.values()
        ]

        resolved_lines: List[Dict[str, Any]] = []
        total_weight = 0.0

        for pid, qty in requested_items:
            if qty <= 0:
                msg = f"Validation rejected: Quantity for product {pid} must be positive (got {qty})."
                self.events.log("ORDER", "VALIDATION", "REJECTED", msg, order_id=oid)
                return False, msg, None

            # Formulate logical query
            query = Predicate("Item", (Constant(pid), Variable("?cat"), Variable("?shelf")))
            unif_res = resolve_product_predicate(query, catalog_facts)
            if not unif_res.success:
                msg = f"Validation rejected: Unification failed. Product {pid} is unknown or missing from catalog."
                self.events.log("LOGIC", "UNIFICATION", "FAILED", msg, order_id=oid)
                return False, msg, None

            prod = self.grid.products_by_id[pid]
            if not prod.active:
                msg = f"Validation rejected: Product {prod.name} ({pid}) is inactive."
                self.events.log("ORDER", "VALIDATION", "REJECTED", msg, order_id=oid)
                return False, msg, None

            shelf_id = prod.shelf_id
            shelf = self.grid.get_shelf_by_id(shelf_id)
            if not shelf:
                msg = f"Validation rejected: Shelf {shelf_id} not found."
                self.events.log("ORDER", "VALIDATION", "REJECTED", msg, order_id=oid)
                return False, msg, None

            # Unification success event
            subst_clean = unif_res.substitution
            self.events.log(
                "LOGIC",
                "UNIFICATION",
                "SUCCESS",
                f"Resolved {pid} -> Category: {subst_clean.get('?cat')}, Shelf: {subst_clean.get('?shelf')}.",
                order_id=oid
            )

            line_weight = prod.unit_weight_kg * qty
            total_weight += line_weight
            resolved_lines.append({
                "product_id": pid,
                "quantity": qty,
                "unit_weight_kg": prod.unit_weight_kg,
                "shelf_id": shelf_id
            })

        # 2. Propositional Logic: Verify Acceptance and Capacity
        # Check available stock in SQLite
        stock_sufficient = True
        for line in resolved_lines:
            rec = self.inv_repo.get_stock(line["product_id"])
            if not rec or rec.available < line["quantity"]:
                stock_sufficient = False
                break

        acceptance_eval = evaluate_order_acceptance(
            has_items=len(resolved_lines) > 0,
            items_active=True,
            stock_sufficient=stock_sufficient,
            valid_quantities=True
        )
        if not acceptance_eval.result:
            msg = f"Order rejected: {acceptance_eval.explanation}"
            self.events.log("LOGIC", "ORDER_ACCEPTANCE", "REJECTED", msg, order_id=oid)
            return False, msg, None

        capacity_eval = evaluate_robot_capacity(0.0, total_weight, self.robot.max_capacity_kg)
        if not capacity_eval.result:
            msg = f"Order rejected: {capacity_eval.explanation}"
            self.events.log("LOGIC", "CAPACITY_CHECK", "REJECTED", msg, order_id=oid)
            return False, msg, None

        # 3. SQLite Transactional Reservation
        try:
            self.order_repo.create_order(order_id=oid, lines=resolved_lines, status="VALIDATED")
            items_to_reserve = [(line["product_id"], line["quantity"]) for line in resolved_lines]
            self.inv_repo.reserve_order_stock(order_id=oid, items=items_to_reserve, idempotency_key=f"RES-{oid}")
        except InsufficientStockError as err:
            msg = f"Stock shortage during reservation: {err}"
            self.order_repo.update_status(oid, "REJECTED", notes=str(err))
            self.events.log("ORDER", "RESERVATION", "FAILED", msg, order_id=oid)
            return False, msg, None

        # Set active fulfillment state
        self.active_order_id = oid
        self.active_order_lines = resolved_lines
        self.replans_count = 0

        self.events.log(
            "ORDER",
            "ORDER_VALIDATED",
            "SUCCESS",
            f"Order {oid} validated: {len(resolved_lines)} line items, {total_weight:.2f} kg reserved in SQLite.",
            order_id=oid
        )
        return True, f"Order {oid} validated and stock reserved successfully.", oid

    # -------------------------------------------------------------------------
    # 2. High-Level Forward State-Space Search Planning
    # -------------------------------------------------------------------------

    def plan_order_mission(self) -> Tuple[bool, str]:
        """Synthesize high-level mission plan using forward state-space search."""
        if not self.active_order_id or not self.active_order_lines:
            return False, "Cannot plan mission: No validated active order."

        oid = self.active_order_id
        self.order_repo.update_status(oid, "PLANNING")
        self.engine.robot_sm.transition_to(RobotState.PLANNING)
        self.robot.state = RobotState.PLANNING

        order_dict = {line["product_id"]: line["quantity"] for line in self.active_order_lines}
        plan_result = forward_state_space_search(
            grid=self.grid,
            initial_robot_pos=self.robot.position,
            order_items=order_dict
        )

        if not plan_result.success:
            self.order_repo.update_status(oid, "BLOCKED", notes=plan_result.explanation)
            self.engine.robot_sm.transition_to(RobotState.BLOCKED)
            self.robot.state = RobotState.BLOCKED
            self.events.log("PLANNER", "FORWARD_SEARCH", "FAILED", plan_result.explanation, order_id=oid)
            return False, plan_result.explanation

        self.high_level_plan = plan_result.plan
        self.current_plan_index = 0
        self.current_gbfs_route = []

        self.order_repo.update_status(oid, "READY")
        self.events.log(
            "PLANNER",
            "FORWARD_SEARCH",
            "SUCCESS",
            f"Forward search synthesized {len(self.high_level_plan)} actions. Order {oid} is READY.",
            order_id=oid
        )
        return True, "Mission plan synthesized successfully."

    # -------------------------------------------------------------------------
    # 3. Step-by-Step Execution (GBFS + Reflex Agent + Action Executor)
    # -------------------------------------------------------------------------

    def execute_next_step(self) -> Tuple[bool, str, bool]:
        """Execute the next single atomic step in the mission plan.

        Returns:
            (success: bool, status_message: str, is_complete: bool)
        """
        if not self.active_order_id:
            return False, "No active order to execute.", False

        if self.current_plan_index >= len(self.high_level_plan):
            # All actions completed
            return True, "All planned actions already completed.", True

        oid = self.active_order_id
        action = self.high_level_plan[self.current_plan_index]

        # ---------------------------------------------------------------------
        # Case A: Navigation Actions (NAVIGATE_TO_PICKUP or NAVIGATE_TO_STATION)
        # ---------------------------------------------------------------------
        if action.action_type in ("NAVIGATE_TO_PICKUP", "NAVIGATE_TO_STATION"):
            target_pos = action.target_pos

            # If already at target, advance to next action
            if (self.robot.position.x, self.robot.position.y) == (target_pos.x, target_pos.y):
                self.current_plan_index += 1
                self.current_gbfs_route = []
                return True, f"Arrived at target {target_pos.to_tuple()}.", False

            # Need a route if current route is empty
            if not self.current_gbfs_route:
                gbfs_res = greedy_best_first_search(self.grid, self.robot.position, target_pos)
                if not gbfs_res.success:
                    self.order_repo.update_status(oid, "BLOCKED", notes=gbfs_res.explanation)
                    self.engine.robot_sm.transition_to(RobotState.BLOCKED)
                    self.robot.state = RobotState.BLOCKED
                    self.events.log("NAVIGATION", "GBFS", "BLOCKED", gbfs_res.explanation, order_id=oid)
                    return False, f"Route blocked: {gbfs_res.explanation}", False

                # First element of path is current position; route steps are path[1:]
                self.current_gbfs_route = gbfs_res.path[1:]
                self.events.log(
                    "NAVIGATION",
                    "GBFS",
                    "SUCCESS",
                    f"GBFS computed {len(self.current_gbfs_route)}-step route to {target_pos.to_tuple()}.",
                    order_id=oid
                )

            # Peek next cell in route
            next_cell = self.current_gbfs_route[0]

            # Consult Simple Reflex Agent before movement
            is_blocked = not self.grid.is_walkable(next_cell.x, next_cell.y)
            percept = Percept(
                current_position=self.robot.position,
                facing=self.robot.facing,
                proposed_next_cell=next_cell,
                is_next_cell_in_bounds=self.grid.in_bounds(next_cell.x, next_cell.y),
                is_next_cell_blocked=is_blocked
            )
            reflex_response = self.reflex_agent.evaluate(percept)

            # Reflex Rule 1: Obstacle Avoidance Trigger
            if reflex_response.action == "STOP_AND_REPLAN":
                self.replans_count += 1
                self.current_gbfs_route = []  # Invalidate blocked route
                self.events.log(
                    "REFLEX",
                    "OBSTACLE_DETECTED",
                    "BLOCKED",
                    f"Reflex Agent triggered STOP: Cell {next_cell.to_tuple()} blocked. Invaliding route.",
                    order_id=oid,
                    position=self.robot.position
                )

                # Attempt immediate GBFS replan
                replan_res = greedy_best_first_search(self.grid, self.robot.position, target_pos)
                if not replan_res.success:
                    self.order_repo.update_status(oid, "BLOCKED", notes="Replanning failed: No alternate path exists.")
                    self.engine.robot_sm.transition_to(RobotState.BLOCKED)
                    self.robot.state = RobotState.BLOCKED
                    return False, f"Replanning failed: target {target_pos.to_tuple()} unreachable.", False

                self.current_gbfs_route = replan_res.path[1:]
                self.events.log(
                    "NAVIGATION",
                    "REPLAN",
                    "SUCCESS",
                    f"Replanned route: {len(self.current_gbfs_route)} steps around obstacle.",
                    order_id=oid
                )
                return True, "Obstacle encountered; replanned alternative route.", False

            # Reflex Approved: Execute movement
            if action.action_type == "NAVIGATE_TO_PICKUP":
                target_robot_state = RobotState.NAVIGATING_TO_PICKUP
            else:
                target_robot_state = RobotState.NAVIGATING_TO_DISTRIBUTION

            if self.robot.state != target_robot_state:
                if self.engine.robot_sm.can_transition_to(target_robot_state):
                    self.engine.robot_sm.transition_to(target_robot_state)
                    self.robot.state = target_robot_state

            step_ok, step_msg = self.engine.step_towards(next_cell)
            if step_ok:
                self.current_gbfs_route.pop(0)

                # If reached target destination, advance action
                if (self.robot.position.x, self.robot.position.y) == (target_pos.x, target_pos.y):
                    self.current_plan_index += 1
                    self.current_gbfs_route = []
                return True, step_msg, False
            else:
                return False, step_msg, False

        # ---------------------------------------------------------------------
        # Case B: Collection Action (COLLECT_PRODUCT)
        # ---------------------------------------------------------------------
        elif action.action_type == "COLLECT_PRODUCT":
            pid = action.product_id
            shelf_id = action.shelf_id
            qty = action.quantity

            # Check Reflex Agent pickup preconditions
            is_at_pickup = (self.robot.position.x, self.robot.position.y) == (action.target_pos.x, action.target_pos.y)
            prod = self.grid.products_by_id[pid]
            within_cap = (self.robot.current_load_kg + prod.unit_weight_kg * qty) <= self.robot.max_capacity_kg

            percept = Percept(
                current_position=self.robot.position,
                facing=self.robot.facing,
                at_pickup_location=is_at_pickup,
                pickup_preconditions_valid=is_at_pickup and within_cap
            )
            reflex_response = self.reflex_agent.evaluate(percept)

            if reflex_response.action == "REJECT_PICKUP":
                msg = f"Collection rejected by Reflex Agent: {reflex_response.reason}"
                self.events.log("REFLEX", "PICKUP_CHECK", "REJECTED", msg, order_id=oid, position=self.robot.position)
                return False, msg, False

            # Transition state to PICKING
            if self.engine.robot_sm.can_transition_to(RobotState.PICKING):
                self.engine.robot_sm.transition_to(RobotState.PICKING)
                self.robot.state = RobotState.PICKING

            # Execute simulation pickup
            pickup_ok, pickup_msg = self.engine.executor.execute_pickup(
                shelf_id=shelf_id,
                product_id=pid,
                quantity=qty
            )
            if not pickup_ok:
                return False, pickup_msg, False

            # Sync SQLite pickup transaction
            idemp_key = f"PICK-{oid}-{pid}-{self.current_plan_index}"
            self.inv_repo.record_item_picked(
                order_id=oid,
                product_id=pid,
                quantity=qty,
                idempotency_key=idemp_key
            )

            # Advance to next action
            self.current_plan_index += 1
            return True, pickup_msg, False

        # ---------------------------------------------------------------------
        # Case C: Delivery Confirmation (DELIVER_ORDER)
        # ---------------------------------------------------------------------
        elif action.action_type == "DELIVER_ORDER":
            ds = self.grid.distribution_station
            is_at_station = (self.robot.position.x, self.robot.position.y) == (ds.x, ds.y)

            # Validate all items are carried
            total_ordered = sum(line["quantity"] for line in self.active_order_lines)
            total_carried = sum(self.robot.carried_items.values())
            all_collected = (total_carried == total_ordered)

            percept = Percept(
                current_position=self.robot.position,
                facing=self.robot.facing,
                at_distribution_station=is_at_station,
                delivery_preconditions_valid=is_at_station and all_collected
            )
            reflex_response = self.reflex_agent.evaluate(percept)

            if reflex_response.action == "REJECT_DELIVERY":
                msg = f"Delivery rejected by Reflex Agent: {reflex_response.reason}"
                self.events.log("REFLEX", "DELIVERY_CHECK", "REJECTED", msg, order_id=oid, position=self.robot.position)
                return False, msg, False

            # Transition to UNLOADING
            if self.engine.robot_sm.can_transition_to(RobotState.UNLOADING):
                self.engine.robot_sm.transition_to(RobotState.UNLOADING)
                self.robot.state = RobotState.UNLOADING

            total_weight = self.robot.current_load_kg

            # Execute physical unload
            unload_ok, unload_msg = self.engine.executor.execute_unload()
            if not unload_ok:
                return False, unload_msg, False

            # Commit exactly-once delivery in SQLite
            try:
                self.order_repo.confirm_delivery(
                    order_id=oid,
                    total_items=total_ordered,
                    total_weight_kg=total_weight,
                    idempotency_key=f"DELIV-{oid}"
                )
            except DeliveryError as d_err:
                msg = f"Delivery database confirmation failed: {d_err}"
                self.events.log("ORDER", "DELIVERY", "FAILED", msg, order_id=oid)
                return False, msg, False

            # Final state transitions
            if self.engine.robot_sm.can_transition_to(RobotState.COMPLETED):
                self.engine.robot_sm.transition_to(RobotState.COMPLETED)
                self.robot.state = RobotState.COMPLETED

            self.events.log(
                "ORDER",
                "ORDER_DELIVERED",
                "SUCCESS",
                f"Order {oid} confirmed DELIVERED. {total_ordered} items ({total_weight:.2f} kg) received at Station DS-01.",
                order_id=oid,
                position=self.robot.position
            )

            self.current_plan_index += 1
            return True, f"Order {oid} delivered and committed successfully!", True

        return False, f"Unknown action type: {action.action_type}", False

    # -------------------------------------------------------------------------
    # 4. Autonomous Mission Loop (End-to-End Runner)
    # -------------------------------------------------------------------------

    def run_full_mission(self, max_ticks: int = 500) -> FulfillmentReport:
        """Execute the entire mission from current state until completion or blockage."""
        ticks = 0
        while self.current_plan_index < len(self.high_level_plan) and ticks < max_ticks:
            ticks += 1
            success, msg, is_done = self.execute_next_step()
            if not success:
                break
            if is_done:
                break

        oid = self.active_order_id or "UNKNOWN"
        order_rec = self.order_repo.get_order(oid)
        final_status = order_rec.status if order_rec else "UNKNOWN"
        total_items = sum(line["quantity"] for line in self.active_order_lines)
        total_weight = sum(line["unit_weight_kg"] * line["quantity"] for line in self.active_order_lines)

        return FulfillmentReport(
            order_id=oid,
            status=final_status,
            items_delivered=total_items if final_status == "DELIVERED" else 0,
            total_weight_kg=total_weight if final_status == "DELIVERED" else 0.0,
            steps_travelled=self.robot.distance_travelled,
            plan_actions_count=len(self.high_level_plan),
            replans_triggered=self.replans_count,
            explanation=f"Mission terminated with status {final_status} in {ticks} ticks."
        )

    # -------------------------------------------------------------------------
    # 5. Order Cancellation & Reconciliation
    # -------------------------------------------------------------------------

    def cancel_active_order(self) -> Tuple[bool, str]:
        """Cancel active order, releasing unpicked reservations and returning picked cargo to shelves."""
        if not self.active_order_id:
            return False, "No active order to cancel."

        oid = self.active_order_id
        self.inv_repo.release_and_reconcile_order(oid, reconcile_picked=True)
        self.order_repo.update_status(oid, "CANCELLED", notes="Cancelled by user or operator.")

        # Reset robot cargo and target
        self.robot.current_load_kg = 0.0
        self.robot.carried_items.clear()
        self.robot.target = None
        self.current_gbfs_route = []
        self.high_level_plan = []
        self.current_plan_index = 0

        self.engine.robot_sm._current_state = RobotState.IDLE
        self.robot.state = RobotState.IDLE

        self.events.log(
            "ORDER",
            "ORDER_CANCELLED",
            "SUCCESS",
            f"Order {oid} cancelled. Reservations released and cargo restocked to warehouse shelves.",
            order_id=oid
        )

        self.active_order_id = None
        self.active_order_lines = []
        return True, f"Order {oid} cancelled and reconciled successfully."
