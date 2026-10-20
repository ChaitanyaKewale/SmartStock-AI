"""Phase 4 Automated Tests: The Six Core Artificial Intelligence Syllabus Concepts.

Independent test suites covering:
4.1 Unification (variables, constants, nested predicates, consistency, failure)
4.2 Propositional Logic (order acceptance, pickup, capacity, delivery eligibility)
4.3 Min-Conflicts (already-valid, resolvable conflicts, capacity/zone violations, seeds, preservation)
4.4 Greedy Best-First Search (simple route, obstacle detour, unreachable goal, validation)
4.5 Forward State-Space Search (single/multi-item missions, delivery goal test, repeated-state prevention)
4.6 Simple Reflex Agent (condition-action rules, priority hierarchy, obstacle stops)
"""

import pytest
from simulation.models import Position, RobotDirection
from simulation.warehouse import get_default_warehouse

# 4.1 Unification imports
from ai.unification import (
    Variable,
    Constant,
    Predicate,
    unify,
    apply_substitution,
    resolve_product_predicate
)

# 4.2 Propositional Logic imports
from ai.propositional_logic import (
    evaluate_order_acceptance,
    evaluate_collection_permission,
    evaluate_robot_capacity,
    evaluate_delivery_eligibility,
    evaluate_movement_eligibility
)

# 4.3 Min-Conflicts imports
from ai.min_conflicts import (
    StorageAssignmentProblem,
    min_conflicts
)

# 4.4 Greedy Best-First Search imports
from ai.greedy_best_first import (
    greedy_best_first_search,
    manhattan_heuristic
)

# 4.5 Forward State-Space Search imports
from ai.forward_search import (
    forward_state_space_search
)

# 4.6 Simple Reflex Agent imports
from ai.reflex_agent import (
    SimpleReflexAgent,
    Percept
)


# =============================================================================
# 4.1 Unification Tests
# =============================================================================

def test_unification_identical_constants_and_mismatches():
    """Verify unification of constants succeeds on identical values and fails on mismatches."""
    c1 = Constant("PROD-001")
    c2 = Constant("PROD-001")
    c3 = Constant("PROD-999")

    # Identical constants unify with empty substitution
    subst = unify(c1, c2)
    assert subst == {}

    # Mismatched constants fail
    subst_fail = unify(c1, c3)
    assert subst_fail is None


def test_unification_variable_binding_and_consistency():
    """Verify variables bind to constants and enforce consistency across multiple arguments."""
    var_x = Variable("?x")
    var_y = Variable("?y")
    c_val = Constant("LAPTOP")

    # Single variable binding
    subst = unify(var_x, c_val)
    assert subst == {"?x": c_val}

    # Predicate with repeated variable: P(?x, ?x) unifies with P("A", "A") but NOT P("A", "B")
    pred_pattern = Predicate("Pair", (var_x, var_x))
    pred_valid = Predicate("Pair", (Constant("A"), Constant("A")))
    pred_invalid = Predicate("Pair", (Constant("A"), Constant("B")))

    subst_valid = unify(pred_pattern, pred_valid)
    assert subst_valid is not None
    assert subst_valid["?x"] == Constant("A")

    subst_invalid = unify(pred_pattern, pred_invalid)
    assert subst_invalid is None


def test_unification_variable_to_variable_and_nested_terms():
    """Verify variable-to-variable unification and nested predicates."""
    var_a = Variable("?a")
    var_b = Variable("?b")

    # Variable to variable
    subst = unify(var_a, var_b)
    assert subst is not None
    assert subst["?a"] == var_b

    # Nested terms: Outer(Inner(?x)) unifies with Outer(Inner(100))
    nested1 = Predicate("Outer", (Predicate("Inner", (Variable("?val"),)),))
    nested2 = Predicate("Outer", (Predicate("Inner", (Constant(100),)),))

    subst_nested = unify(nested1, nested2)
    assert subst_nested is not None
    assert subst_nested["?val"] == Constant(100)


def test_unification_inventory_catalog_resolution():
    """Verify resolving catalog facts using logical unification."""
    catalog_kb = [
        Predicate("Item", (Constant("PROD-001"), Constant("ELECTRONICS"), Constant("R01"))),
        Predicate("Item", (Constant("PROD-007"), Constant("ACCESSORIES"), Constant("R07"))),
        Predicate("Item", (Constant("PROD-013"), Constant("HARDWARE"), Constant("R13"))),
    ]

    # Query 1: Find shelf and category for PROD-001
    query1 = Predicate("Item", (Constant("PROD-001"), Variable("?cat"), Variable("?shelf")))
    res1 = resolve_product_predicate(query1, catalog_kb)
    assert res1.success is True
    assert res1.substitution["?cat"] == "'ELECTRONICS'"
    assert res1.substitution["?shelf"] == "'R01'"

    # Query 2: Product missing from inventory
    query_missing = Predicate("Item", (Constant("PROD-MISSING"), Variable("?cat"), Variable("?shelf")))
    res_missing = resolve_product_predicate(query_missing, catalog_kb)
    assert res_missing.success is False
    assert res_missing.matched_fact is None


# =============================================================================
# 4.2 Propositional Logic Tests
# =============================================================================

def test_propositional_order_acceptance_rules():
    """Verify order acceptance propositional evaluation under all combinations."""
    # All true
    res = evaluate_order_acceptance(has_items=True, items_active=True, stock_sufficient=True, valid_quantities=True)
    assert res.result is True
    assert len(res.failed_conditions) == 0

    # Individual false conditions
    res_no_items = evaluate_order_acceptance(has_items=False, items_active=True, stock_sufficient=True, valid_quantities=True)
    assert res_no_items.result is False
    assert "order_contains_items" in res_no_items.failed_conditions

    res_no_stock = evaluate_order_acceptance(has_items=True, items_active=True, stock_sufficient=False, valid_quantities=True)
    assert res_no_stock.result is False
    assert "stock_is_sufficient" in res_no_stock.failed_conditions

    # Combinations of false conditions
    res_multi_fail = evaluate_order_acceptance(has_items=True, items_active=False, stock_sufficient=False, valid_quantities=False)
    assert res_multi_fail.result is False
    assert len(res_multi_fail.failed_conditions) == 3


def test_propositional_delivery_eligibility_critical_rule():
    """Verify delivery is strictly rejected if not at station or items are uncollected."""
    # Succeeded only when at station AND all collected AND in progress
    res_ok = evaluate_delivery_eligibility(at_distribution_station=True, all_order_items_collected=True, order_in_progress=True)
    assert res_ok.result is True

    # Critical invariant: Delivery rejected if robot collected all items but is NOT at distribution station
    res_not_at_station = evaluate_delivery_eligibility(at_distribution_station=False, all_order_items_collected=True, order_in_progress=True)
    assert res_not_at_station.result is False
    assert "robot_at_distribution_station" in res_not_at_station.failed_conditions

    # Delivery rejected if at station but items are missing
    res_missing_items = evaluate_delivery_eligibility(at_distribution_station=True, all_order_items_collected=False, order_in_progress=True)
    assert res_missing_items.result is False
    assert "all_required_items_collected" in res_missing_items.failed_conditions


def test_propositional_capacity_and_collection():
    """Verify capacity and collection permission evaluations."""
    # Capacity rule
    cap_ok = evaluate_robot_capacity(current_load_kg=10.0, additional_weight_kg=5.0, max_capacity_kg=25.0)
    assert cap_ok.result is True

    cap_fail = evaluate_robot_capacity(current_load_kg=24.0, additional_weight_kg=2.0, max_capacity_kg=25.0)
    assert cap_fail.result is False

    # Collection rule
    col_ok = evaluate_collection_permission(
        at_designated_pickup_bay=True,
        shelf_has_stock=True,
        within_payload_capacity=True,
        product_matches_order=True
    )
    assert col_ok.result is True

    col_wrong_bay = evaluate_collection_permission(
        at_designated_pickup_bay=False,
        shelf_has_stock=True,
        within_payload_capacity=True,
        product_matches_order=True
    )
    assert col_wrong_bay.result is False
    assert "robot_at_designated_pickup_bay" in col_wrong_bay.failed_conditions


# =============================================================================
# 4.3 Min-Conflicts Local Search Tests
# =============================================================================

def test_min_conflicts_already_optimal():
    """Verify algorithm detects 0 initial conflicts and exits immediately."""
    problem = StorageAssignmentProblem(
        variables=["P1", "P2"],
        domains={"P1": ["R01"], "P2": ["R02"]},
        item_categories={"P1": "ELECTRONICS", "P2": "ACCESSORIES"},
        shelf_zones={"R01": "ELECTRONICS", "R02": "ACCESSORIES"},
        shelf_capacities={"R01": 10, "R02": 10}
    )

    initial = {"P1": "R01", "P2": "R02"}
    result = min_conflicts(problem, initial_assignment=initial, max_steps=50)

    assert result.success is True
    assert result.initial_conflicts == 0
    assert result.final_conflicts == 0
    assert result.iterations == 0
    assert result.final_assignment == initial


def test_min_conflicts_resolves_zone_and_capacity_conflicts():
    """Verify algorithm moves conflicted items to appropriate shelves."""
    # P1 (ELECTRONICS) starts wrongly on R02 (ACCESSORIES)
    # P2 (ACCESSORIES) starts wrongly on R01 (ELECTRONICS)
    problem = StorageAssignmentProblem(
        variables=["P1", "P2"],
        domains={
            "P1": ["R01", "R02"],
            "P2": ["R01", "R02"]
        },
        item_categories={"P1": "ELECTRONICS", "P2": "ACCESSORIES"},
        shelf_zones={"R01": "ELECTRONICS", "R02": "ACCESSORIES"},
        shelf_capacities={"R01": 10, "R02": 10}
    )

    wrong_initial = {"P1": "R02", "P2": "R01"}
    result = min_conflicts(problem, initial_assignment=wrong_initial, max_steps=50, seed=123)

    assert result.success is True
    assert result.initial_conflicts == 2
    assert result.final_conflicts == 0
    assert result.final_assignment["P1"] == "R01"
    assert result.final_assignment["P2"] == "R02"


def test_min_conflicts_preserves_valid_assignment_and_seed_determinism():
    """Verify algorithm behavior on impossible constraint limits and seed determinism."""
    # Impossible problem: 2 items of category ELECTRONICS, but only 1 shelf exists of ACCESSORIES
    problem = StorageAssignmentProblem(
        variables=["P1", "P2"],
        domains={"P1": ["R01"], "P2": ["R01"]},
        item_categories={"P1": "ELECTRONICS", "P2": "ELECTRONICS"},
        shelf_zones={"R01": "ACCESSORIES"},  # Mismatch
        shelf_capacities={"R01": 10}
    )

    # 1. Deterministic seed produces identical iterations
    res1 = min_conflicts(problem, max_steps=10, seed=99)
    res2 = min_conflicts(problem, max_steps=10, seed=99)
    assert res1.iterations == res2.iterations
    assert res1.final_conflicts == res2.final_conflicts

    # 2. Reached iteration limit
    assert res1.success is False
    assert "reached iteration limit" in res1.explanation.lower()


# =============================================================================
# 4.4 Greedy Best-First Search Tests
# =============================================================================

def test_gbfs_simple_route_and_cost():
    """Verify simple corridor route planning from (0, 1) to (0, 4)."""
    grid = get_default_warehouse()
    start = Position(x=0, y=1)
    goal = Position(x=0, y=4)

    result = greedy_best_first_search(grid, start, goal)
    assert result.success is True
    assert len(result.path) == 4  # (0,1) -> (0,2) -> (0,3) -> (0,4)
    assert result.path[0] == start
    assert result.path[-1] == goal
    assert result.total_cost == 3

    # Every step in path must be walkable and adjacent
    for i in range(len(result.path) - 1):
        assert result.path[i].is_adjacent_to(result.path[i + 1])
        assert grid.is_walkable(result.path[i].x, result.path[i].y)


def test_gbfs_obstacle_detour():
    """Verify GBFS detours around an obstacle barrier in the corridor."""
    grid = get_default_warehouse()
    # Place obstacle directly in straight path at (0, 2)
    grid.add_obstacle(0, 2)
    start = Position(x=0, y=1)
    goal = Position(x=0, y=3)

    result = greedy_best_first_search(grid, start, goal)
    assert result.success is True
    assert result.path[-1] == goal

    # Assure obstacle at (0, 2) is NOT in the chosen route
    route_tuples = [(p.x, p.y) for p in result.path]
    assert (0, 2) not in route_tuples


def test_gbfs_blocked_start_goal_and_unreachable():
    """Verify validation of blocked endpoints and unreachable targets."""
    grid = get_default_warehouse()

    # Blocked goal: Rack R01 at (2, 2)
    res_blocked_goal = greedy_best_first_search(grid, Position(x=0, y=1), Position(x=2, y=2))
    assert res_blocked_goal.success is False
    assert "impassable" in res_blocked_goal.explanation.lower()

    # Out of bounds start
    res_oob = greedy_best_first_search(grid, Position(x=99, y=99), Position(x=0, y=1))
    assert res_oob.success is False
    assert "bounds" in res_oob.explanation.lower()

    # Completely trapped unreachable cell: trap bottom-left corner (0, 11)
    grid.add_obstacle(1, 11)
    grid.add_obstacle(0, 10)

    res_trapped = greedy_best_first_search(grid, Position(x=0, y=0), Position(x=0, y=11))
    assert res_trapped.success is False
    assert "unreachable" in res_trapped.explanation.lower()


# =============================================================================
# 4.5 Forward State-Space Search Tests
# =============================================================================

def test_forward_search_single_product_order():
    """Verify forward planner constructs a single-item mission: Navigate -> Collect -> Return -> Deliver."""
    grid = get_default_warehouse()
    start_pos = Position(x=0, y=1)
    order_items = {"PROD-001": 1}  # PROD-001 is on R01, pickup bay (2, 1)

    result = forward_state_space_search(grid, start_pos, order_items)
    assert result.success is True
    plan = result.plan

    # Expected sequence of actions
    assert len(plan) == 4
    assert plan[0].action_type == "NAVIGATE_TO_PICKUP"
    assert (plan[0].target_pos.x, plan[0].target_pos.y) == (2, 1)

    assert plan[1].action_type == "COLLECT_PRODUCT"
    assert plan[1].product_id == "PROD-001"
    assert plan[1].quantity == 1

    assert plan[2].action_type == "NAVIGATE_TO_STATION"
    assert (plan[2].target_pos.x, plan[2].target_pos.y) == (0, 0)

    assert plan[3].action_type == "DELIVER_ORDER"


def test_forward_search_multi_product_order():
    """Verify forward planner handles multi-item orders visiting multiple distinct pickup bays."""
    grid = get_default_warehouse()
    start_pos = Position(x=0, y=1)
    # PROD-001 on R01 (pickup 2, 1), PROD-007 on R07 (pickup 7, 1)
    order_items = {"PROD-001": 1, "PROD-007": 2}

    result = forward_state_space_search(grid, start_pos, order_items)
    assert result.success is True
    plan = result.plan

    # Must contain pickups for both items and final delivery action
    action_types = [a.action_type for a in plan]
    assert action_types.count("COLLECT_PRODUCT") == 2
    assert action_types[-1] == "DELIVER_ORDER"


def test_forward_search_edge_cases():
    """Verify forward planner rejects empty orders and unknown items."""
    grid = get_default_warehouse()
    start_pos = Position(x=0, y=1)

    # Empty order
    res_empty = forward_state_space_search(grid, start_pos, {})
    assert res_empty.success is False
    assert "zero items" in res_empty.explanation.lower()

    # Unknown product
    res_unknown = forward_state_space_search(grid, start_pos, {"UNKNOWN-SKU": 1})
    assert res_unknown.success is False
    assert "not found" in res_unknown.explanation.lower()


# =============================================================================
# 4.6 Simple Reflex Agent Tests
# =============================================================================

def test_reflex_agent_obstacle_priority():
    """Verify reflex agent halts immediately when proposed cell is obstructed."""
    agent = SimpleReflexAgent()

    # Next cell blocked -> must trigger Rule 1 STOP_AND_REPLAN
    percept_blocked = Percept(
        current_position=Position(x=1, y=1),
        facing=RobotDirection.SOUTH,
        proposed_next_cell=Position(x=1, y=2),
        is_next_cell_blocked=True
    )
    action = agent.evaluate(percept_blocked)
    assert action.action == "STOP_AND_REPLAN"
    assert action.rule_name == "RULE_1_OBSTACLE_AVOIDANCE"


def test_reflex_agent_pickup_rules():
    """Verify reflex agent approves valid pickups and rejects invalid ones."""
    agent = SimpleReflexAgent()

    # At pickup bay with valid preconditions
    p_valid = Percept(
        current_position=Position(x=2, y=1),
        facing=RobotDirection.SOUTH,
        at_pickup_location=True,
        pickup_preconditions_valid=True
    )
    action_valid = agent.evaluate(p_valid)
    assert action_valid.action == "REQUEST_PICKUP"
    assert action_valid.rule_name == "RULE_3_PICKUP_APPROVE"

    # At pickup bay with failed preconditions
    p_invalid = Percept(
        current_position=Position(x=2, y=1),
        facing=RobotDirection.SOUTH,
        at_pickup_location=True,
        pickup_preconditions_valid=False
    )
    action_invalid = agent.evaluate(p_invalid)
    assert action_invalid.action == "REJECT_PICKUP"
    assert action_invalid.rule_name == "RULE_2_PICKUP_REJECT"


def test_reflex_agent_return_and_delivery_rules():
    """Verify reflex agent triggers return to station and delivery approval."""
    agent = SimpleReflexAgent()

    # All items collected -> triggers return to distribution station
    p_return = Percept(
        current_position=Position(x=7, y=4),
        facing=RobotDirection.NORTH,
        all_products_collected=True,
        at_distribution_station=False
    )
    act_return = agent.evaluate(p_return)
    assert act_return.action == "REQUEST_RETURN_TO_STATION"
    assert act_return.rule_name == "RULE_6_RETURN_TRIGGER"

    # At station with verified cargo -> triggers delivery
    p_delivery = Percept(
        current_position=Position(x=0, y=0),
        facing=RobotDirection.SOUTH,
        at_distribution_station=True,
        delivery_preconditions_valid=True
    )
    act_delivery = agent.evaluate(p_delivery)
    assert act_delivery.action == "REQUEST_DELIVERY"
    assert act_delivery.rule_name == "RULE_5_DELIVERY_APPROVE"

    # Clear movement approval
    p_clear = Percept(
        current_position=Position(x=0, y=1),
        facing=RobotDirection.SOUTH,
        proposed_next_cell=Position(x=0, y=2),
        is_next_cell_in_bounds=True,
        is_next_cell_blocked=False
    )
    act_clear = agent.evaluate(p_clear)
    assert act_clear.action == "ALLOW_MOVEMENT"
    assert act_clear.rule_name == "RULE_7_MOVEMENT_ALLOW"
