"""SmartStock AI - AI Laboratory Page.

Interactive algorithm demonstration lab providing live inspection and real execution
of the six Artificial Intelligence syllabus concepts:
1. Logical Predicate Unification
2. Propositional Logic Rules
3. Min-Conflicts Local Search
4. Greedy Best-First Search (GBFS)
5. Forward State-Space Search
6. Simple Reflex Agent
"""

from __future__ import annotations

import streamlit as st
from simulation.models import Position, RobotDirection
from simulation.warehouse import get_default_warehouse

# AI Modules
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
from ai.greedy_best_first import greedy_best_first_search
from ai.forward_search import forward_state_space_search
from ai.reflex_agent import SimpleReflexAgent, Percept

st.set_page_config(page_title="AI Laboratory | SmartStock AI", layout="wide", page_icon="🧪")

st.markdown("""
<style>
    .reportview-container, .main {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .header-box {
        padding: 12px 18px;
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        margin-bottom: 20px;
    }
    .lab-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .result-box {
        background: #080d1a;
        border: 1px solid #1a2234;
        border-radius: 4px;
        padding: 10px 14px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
        font-size: 12px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h3 style="margin: 0; color: #f3f4f6; font-size: 18px; font-weight: 600;">AI LABORATORY</h3>
    <div style="color: #9ca3af; font-size: 12px; margin-top: 4px;">
        Live interactive testbed executing the six core Artificial Intelligence algorithms in real-time
    </div>
</div>
""", unsafe_allow_html=True)

warehouse = get_default_warehouse()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Unification",
    "2. Propositional Logic",
    "3. Min-Conflicts",
    "4. Greedy Best-First Search",
    "5. Forward Search",
    "6. Reflex Agent"
])

# -----------------------------------------------------------------------------
# Tab 1: Unification
# -----------------------------------------------------------------------------
with tab1:
    st.markdown("#### 1. Logical Predicate Unification (`ai/unification.py`)")
    st.caption("First-order logic term unification with variable bindings, occur-checks, and catalog fact resolution.")

    # Construct KB from real warehouse products
    catalog_facts = [
        Predicate("Item", (Constant(p.id), Constant(p.category), Constant(p.shelf_id)))
        for p in list(warehouse.products_by_id.values())[:10]
    ]

    st.markdown("**Catalog Facts (Knowledge Base):**")
    kb_str = "\n".join([str(f) for f in catalog_facts[:6]])
    st.code(kb_str, language="prolog")

    col_u1, col_u2 = st.columns(2)
    with col_u1:
        query_prod_id = st.selectbox("Select Target Product ID", ["PROD-001", "PROD-004", "PROD-007", "PROD-NONEXISTENT"])
    with col_u2:
        query_pred = Predicate("Item", (Constant(query_prod_id), Variable("?cat"), Variable("?shelf")))
        st.write(f"**Generated Query:** `{query_pred}`")

    if st.button("Execute Unification Query", key="btn_unify"):
        res = resolve_product_predicate(query_pred, catalog_facts)
        if res.success:
            st.success(res.explanation)
            st.json(res.substitution)
        else:
            st.error(res.explanation)

# -----------------------------------------------------------------------------
# Tab 2: Propositional Logic
# -----------------------------------------------------------------------------
with tab2:
    st.markdown("#### 2. Propositional Logic Rule Evaluator (`ai/propositional_logic.py`)")
    st.caption("Explicit evaluation of propositional clauses for acceptance, pickup, capacity, and delivery.")

    c_rule = st.selectbox("Select Rule to Evaluate", ["Order Acceptance", "Delivery Eligibility", "Robot Capacity Check"])

    if c_rule == "Order Acceptance":
        c1, c2, c3, c4 = st.columns(4)
        has_items = c1.checkbox("Has Items", value=True)
        items_active = c2.checkbox("All Active", value=True)
        stock_ok = c3.checkbox("Stock Sufficient", value=True)
        valid_qty = c4.checkbox("Valid Quantities", value=True)

        res = evaluate_order_acceptance(has_items, items_active, stock_ok, valid_qty)
        if res.result:
            st.success(res.explanation)
        else:
            st.error(res.explanation)
        st.json(res.conditions)

    elif c_rule == "Delivery Eligibility":
        c1, c2, c3 = st.columns(3)
        at_station = c1.checkbox("At Station (0, 0)", value=True)
        all_picked = c2.checkbox("All Required Picked", value=False)
        in_prog = c3.checkbox("Order In Progress", value=True)

        res = evaluate_delivery_eligibility(at_station, all_picked, in_prog)
        if res.result:
            st.success(res.explanation)
        else:
            st.error(res.explanation)
        st.json(res.conditions)

    elif c_rule == "Robot Capacity Check":
        cur_load = st.slider("Current Payload (kg)", 0.0, 30.0, 18.0)
        item_wt = st.slider("Additional Item Weight (kg)", 0.0, 15.0, 4.0)
        res = evaluate_robot_capacity(cur_load, item_wt, 25.0)
        if res.result:
            st.success(res.explanation)
        else:
            st.error(res.explanation)
        st.json(res.conditions)

# -----------------------------------------------------------------------------
# Tab 3: Min-Conflicts
# -----------------------------------------------------------------------------
with tab3:
    st.markdown("#### 3. Min-Conflicts Local Search (`ai/min_conflicts.py`)")
    st.caption("CSP local search optimizer resolving shelf zone mismatches and capacity limits.")

    items = ["PROD-01 (Electronics)", "PROD-02 (Electronics)", "PROD-07 (Accessories)", "PROD-08 (Accessories)"]
    st.write("Variables: 4 products with strict category requirements (2 Electronics, 2 Accessories).")

    shelf_domains = {
        "PROD-01": ["R01 (Elec)", "R07 (Acc)"],
        "PROD-02": ["R01 (Elec)", "R07 (Acc)"],
        "PROD-07": ["R01 (Elec)", "R07 (Acc)"],
        "PROD-08": ["R01 (Elec)", "R07 (Acc)"]
    }
    item_cats = {
        "PROD-01": "ELECTRONICS",
        "PROD-02": "ELECTRONICS",
        "PROD-07": "ACCESSORIES",
        "PROD-08": "ACCESSORIES"
    }
    shelf_zones = {
        "R01 (Elec)": "ELECTRONICS",
        "R07 (Acc)": "ACCESSORIES"
    }
    shelf_caps = {"R01 (Elec)": 2, "R07 (Acc)": 2}

    # Deliberately conflicting initial assignment: all products assigned to R07 (Acc)
    wrong_init = {
        "PROD-01": "R07 (Acc)",
        "PROD-02": "R07 (Acc)",
        "PROD-07": "R07 (Acc)",
        "PROD-08": "R07 (Acc)"
    }
    st.write("**Conflicted Initial Assignment (All on R07 - Zone Mismatch & Overloaded):**")
    st.json(wrong_init)

    steps = st.slider("Max Iteration Steps", 10, 100, 30)

    if st.button("Run Min-Conflicts Optimization", key="btn_mc"):
        problem = StorageAssignmentProblem(
            variables=["PROD-01", "PROD-02", "PROD-07", "PROD-08"],
            domains=shelf_domains,
            item_categories=item_cats,
            shelf_zones=shelf_zones,
            shelf_capacities=shelf_caps
        )
        res = min_conflicts(problem, initial_assignment=wrong_init, max_steps=steps, seed=42)
        if res.success:
            st.success(res.explanation)
        else:
            st.warning(res.explanation)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Initial Conflicts", res.initial_conflicts)
        with col_m2:
            st.metric("Final Conflicts", res.final_conflicts)
        st.write("**Optimized Final Assignment:**")
        st.json(res.final_assignment)

# -----------------------------------------------------------------------------
# Tab 4: Greedy Best-First Search
# -----------------------------------------------------------------------------
with tab4:
    st.markdown("#### 4. Greedy Best-First Search Pathfinder (`ai/greedy_best_first.py`)")
    st.caption("Manhattan heuristic pathfinder navigating through walkable warehouse aisles.")

    g_col1, g_col2 = st.columns(2)
    with g_col1:
        s_x = st.number_input("Start X", min_value=0, max_value=15, value=0)
        s_y = st.number_input("Start Y", min_value=0, max_value=11, value=1)
    with g_col2:
        e_x = st.number_input("Goal X", min_value=0, max_value=15, value=7)
        e_y = st.number_input("Goal Y", min_value=0, max_value=11, value=4)

    start_pos = Position(x=s_x, y=s_y)
    goal_pos = Position(x=e_x, y=e_y)

    if st.button("Compute GBFS Route", key="btn_gbfs"):
        res = greedy_best_first_search(warehouse, start_pos, goal_pos)
        if res.success:
            st.success(res.explanation)
            st.metric("Total Steps", res.total_cost)
            st.write(f"**Explored Nodes:** {res.explored_count}")
            route_str = " → ".join([f"({p.x}, {p.y})" for p in res.path])
            st.code(route_str)
        else:
            st.error(res.explanation)

# -----------------------------------------------------------------------------
# Tab 5: Forward Search
# -----------------------------------------------------------------------------
with tab5:
    st.markdown("#### 5. Forward State-Space Search Planner (`ai/forward_search.py`)")
    st.caption("Synthesizes high-level task plans: Navigate to pickups → Collect → Return to Station → Deliver.")

    order_choices = st.multiselect(
        "Choose Products for Mission Plan",
        options=["PROD-001", "PROD-002", "PROD-007", "PROD-013"],
        default=["PROD-001", "PROD-007"]
    )

    if st.button("Generate Mission Plan", key="btn_fwd"):
        order_dict = {pid: 1 for pid in order_choices}
        res = forward_state_space_search(warehouse, Position(x=0, y=1), order_dict)
        if res.success:
            st.success(res.explanation)
            st.metric("Plan Steps", len(res.plan))
            plan_table = [
                {
                    "Step": idx + 1,
                    "Action": a.action_type,
                    "Target": f"({a.target_pos.x}, {a.target_pos.y})",
                    "Details": a.description
                }
                for idx, a in enumerate(res.plan)
            ]
            st.dataframe(plan_table, use_container_width=True)
        else:
            st.error(res.explanation)

# -----------------------------------------------------------------------------
# Tab 6: Simple Reflex Agent
# -----------------------------------------------------------------------------
with tab6:
    st.markdown("#### 6. Simple Reflex Agent (`ai/reflex_agent.py`)")
    st.caption("Percept-driven reactive agent evaluating condition-action rules for obstacle safety and action approval.")

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st_blocked = st.checkbox("Proposed Next Cell Is Blocked / Obstacle", value=False)
        st_pickup = st.checkbox("Robot Stationed at Pickup Location", value=True)
        st_pickup_valid = st.checkbox("Pickup Preconditions Valid", value=True)
    with r_col2:
        st_collected_all = st.checkbox("All Order Items Collected", value=False)
        st_at_station = st.checkbox("Robot At Distribution Station", value=False)
        st_deliv_valid = st.checkbox("Delivery Preconditions Valid", value=False)

    percept = Percept(
        current_position=Position(x=2, y=1),
        facing=RobotDirection.SOUTH,
        proposed_next_cell=Position(x=2, y=2),
        is_next_cell_blocked=st_blocked,
        at_pickup_location=st_pickup,
        pickup_preconditions_valid=st_pickup_valid,
        all_products_collected=st_collected_all,
        at_distribution_station=st_at_station,
        delivery_preconditions_valid=st_deliv_valid
    )

    agent = SimpleReflexAgent()
    action = agent.evaluate(percept)

    st.markdown(f"""
    <div class="result-box">
        <div><strong>TRIGGERED RULE:</strong> <span style="color:#38bdf8;">{action.rule_name}</span></div>
        <div style="margin-top: 4px;"><strong>RECOMMENDED ACTION:</strong> <span style="color:#10b981; font-weight:700;">{action.action}</span></div>
        <div style="margin-top: 4px; color:#9ca3af;"><strong>EXPLANATION:</strong> {action.reason}</div>
    </div>
    """, unsafe_allow_html=True)
