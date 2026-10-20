"""SmartStock AI - Warehouse Operations Dashboard

Phase 3: Robot Model, Explicit State Machine, Event System,
and Action Executor with Step-by-Step Movement Controls.
"""

from __future__ import annotations

import streamlit as st
from pathlib import Path
from utils.config import ConfigurationError
from simulation.models import RobotDirection, RobotState, Position
from simulation.warehouse import WarehouseGrid
from simulation.engine import SimulationEngine
from frontend.map_renderer import render_warehouse_svg, render_map_fallback

# 1. Page Configuration
st.set_page_config(
    page_title="SmartStock AI | Warehouse Operations",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Industrial Control-Room Design System CSS
st.markdown("""
<style>
    :root {
        --bg-main: #0b0f19;
        --bg-panel: #111827;
        --border-panel: #1f2937;
        --text-primary: #f3f4f6;
        --text-muted: #9ca3af;
        --accent-green: #10b981;
        --accent-amber: #f59e0b;
        --accent-red: #ef4444;
        --accent-blue: #3b82f6;
    }

    .stApp {
        background-color: var(--bg-main);
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: var(--bg-panel);
        border: 1px solid var(--border-panel);
        border-radius: 6px;
        padding: 12px 20px;
        margin-bottom: 12px;
    }

    .brand-title {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0.5px;
        color: var(--text-primary);
    }

    .brand-sub {
        font-size: 12px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .status-badge {
        font-size: 11px;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        letter-spacing: 0.5px;
        background: #064e3b;
        color: #34d399;
        border: 1px solid #059669;
    }

    .kpi-card {
        background: var(--bg-panel);
        border: 1px solid var(--border-panel);
        border-radius: 6px;
        padding: 12px 16px;
    }

    .kpi-label {
        font-size: 11px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }

    .kpi-value {
        font-size: 20px;
        font-weight: 700;
        color: var(--text-primary);
    }

    .panel-box {
        background: var(--bg-panel);
        border: 1px solid var(--border-panel);
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 14px;
    }

    .panel-title {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        border-bottom: 1px solid var(--border-panel);
        padding-bottom: 8px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
    }

    .telemetry-row {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        padding: 6px 0;
        border-bottom: 1px solid #1a2234;
    }

    .telemetry-label {
        color: var(--text-muted);
    }

    .telemetry-val {
        color: var(--text-primary);
        font-weight: 600;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    .progress-bar-shell {
        display: flex;
        justify-content: space-between;
        background: #0d1322;
        border: 1px solid var(--border-panel);
        border-radius: 4px;
        padding: 8px 12px;
        font-size: 11px;
    }

    .prog-step {
        color: var(--text-muted);
        font-weight: 500;
    }

    .prog-step.active {
        color: var(--accent-green);
        font-weight: 700;
    }

    .legend-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 11px;
        color: var(--text-muted);
        background: #0d1322;
        border: 1px solid var(--border-panel);
        border-radius: 4px;
        padding: 8px 14px;
        margin-top: 10px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .legend-swatch {
        width: 14px;
        height: 14px;
        border-radius: 2px;
        border: 1px solid rgba(255,255,255,0.2);
    }

    .log-container {
        background: #080d1a;
        border: 1px solid #1a2234;
        border-radius: 4px;
        padding: 6px;
        max-height: 220px;
        overflow-y: auto;
    }

    .log-entry {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 11px;
        padding: 5px 8px;
        border-bottom: 1px solid #111a2e;
        display: flex;
        align-items: baseline;
        gap: 10px;
    }

    .log-time {
        color: #64748b;
        min-width: 65px;
    }

    .log-cat {
        font-weight: 700;
        min-width: 85px;
    }

    .log-outcome {
        font-weight: 600;
        min-width: 75px;
    }

    .log-msg {
        color: var(--text-primary);
        flex: 1;
    }
</style>
""", unsafe_allow_html=True)

from database.db import get_db_connection, init_db, seed_catalog_if_empty
from database.repositories import OrderRepository

# 3. Initialize Authoritative SimulationEngine and SQLite in Session State
if "engine" not in st.session_state:
    try:
        st.session_state.engine = SimulationEngine()
    except ConfigurationError as exc:
        st.error(f"Configuration Initialization Alert: {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"Engine Initialization Error: {exc}")
        st.stop()

# Startup SQLite recovery check (run once per session)
if "interrupted_orders" not in st.session_state:
    try:
        db_conn = get_db_connection()
        init_db(db_conn)
        seed_catalog_if_empty(db_conn)
        order_repo = OrderRepository(db_conn)
        st.session_state.interrupted_orders = order_repo.flag_interrupted_orders()
    except Exception as db_err:
        st.session_state.interrupted_orders = []

engine: SimulationEngine = st.session_state.engine
warehouse: WarehouseGrid = engine.warehouse
robot = engine.robot

# 4. Top Header Bar
robot_status_color = "#34d399" if robot.state != RobotState.PAUSED else "#fbbf24"
st.markdown(f"""
<div class="header-bar">
    <div>
        <span class="brand-title">SMARTSTOCK AI</span>
        <span class="brand-sub"> / Warehouse Operations & Fulfillment</span>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 12px; color: #9ca3af;">Tick: #{engine.tick} | Grid: {warehouse.width}×{warehouse.height}</span>
        <span class="status-badge" style="color: {robot_status_color};">SIMULATION ENGINE ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Interrupted order recovery alert banner
if st.session_state.get("interrupted_orders"):
    orders_str = ", ".join(st.session_state.interrupted_orders)
    st.warning(
        f"⚠️ Startup Recovery Notice: Order(s) {orders_str} were active when the application was last stopped. "
        "Flagged as RECOVERY_REQUIRED. Reconciliation is required before re-executing."
    )

# 5. Compact KPI Row (Live Persistence Data)
completed_orders_list = fulfillment.order_repo.get_completed_orders()
active_count = 1 if fulfillment.active_order_id else 0

col_k1, col_k2, col_k3, col_k4 = st.columns(4)

with col_k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Completed Orders</div>
        <div class="kpi-value">{len(completed_orders_list)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Active Orders</div>
        <div class="kpi-value" style="color: {'#38bdf8' if active_count > 0 else '#f3f4f6'};">{active_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col_k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Distance Travelled</div>
        <div class="kpi-value">{robot.distance_travelled} <span style="font-size:12px; font-weight:normal; color:#9ca3af;">cells</span></div>
    </div>
    """, unsafe_allow_html=True)

with col_k4:
    status_disp = robot.state.value
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Robot State</div>
        <div class="kpi-value" style="font-size: 16px; line-height: 28px; color: {robot_status_color};">{status_disp}</div>
    </div>
    """, unsafe_allow_html=True)

# 6. Main Dashboard Layout (68% Map/Controls, 32% Side Controls/Telemetry)
main_col, side_col = st.columns([0.68, 0.32], gap="small")

with main_col:
    # Warehouse SVG Map Section
    st.markdown("""
    <div class="panel-box" style="padding-bottom: 10px;">
        <div class="panel-title">
            <span>Authoritative Live Warehouse Map (16 × 12 Grid)</span>
            <span style="color: #10b981; font-size: 11px;">● Synchronized Simulation State</span>
        </div>
    """, unsafe_allow_html=True)

    # Shelf inspection selector
    shelf_ids = sorted(list(warehouse.racks_by_id.keys()))
    inspect_options = ["(None - Overview)"] + [f"{s_id}: {warehouse.racks_by_id[s_id].name}" for s_id in shelf_ids]

    col_sel, col_mode = st.columns([0.65, 0.35])
    with col_sel:
        selected_inspect = st.selectbox(
            "Inspect Shelf Location",
            options=inspect_options,
            index=0,
            help="Select any storage rack to highlight its position and accessible pickup cell"
        )
    with col_mode:
        show_edit_mode = st.toggle("Warehouse Edit Mode", value=False, help="Add or remove obstacles on the layout")

    selected_shelf_id = None
    if selected_inspect != "(None - Overview)":
        selected_shelf_id = selected_inspect.split(":")[0].strip()

    # Render SVG Map with Authoritative Robot and Traversed Route
    try:
        svg_content = render_warehouse_svg(
            warehouse,
            robot=robot,
            selected_shelf_id=selected_shelf_id,
            traversed_route=engine.executor.traversed_path
        )
        st.markdown(svg_content, unsafe_allow_html=True)
    except Exception as map_err:
        st.warning(f"Map renderer notice: {map_err}. Displaying fallback layout.")
        fallback_html = render_map_fallback(warehouse)
        st.markdown(fallback_html, unsafe_allow_html=True)

    # Map Legend
    st.markdown("""
    <div class="legend-bar">
        <div class="legend-item"><div class="legend-swatch" style="background:#0369a1; border-color:#38bdf8;"></div> Station (DS-01)</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#1e293b; border-color:#60a5fa;"></div> Storage Rack</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#0f172a; border:1px dashed #059669;"></div> Pickup Bay</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#334155; border-color:#64748b;"></div> Fixed Pillar</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#d97706; border-color:#f59e0b;"></div> User Barrier</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#7f1d1d; border-color:#dc2626;"></div> Restricted Zone</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#047857; border-color:#34d399; border-radius:50%;"></div> Robot Unit</div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Manual Robot Movement & Simulation Control Pad
    st.markdown("""
    <div class="panel-box">
        <div class="panel-title">Robot Movement & Lifecycle Controls</div>
    </div>
    """, unsafe_allow_html=True)

    ctrl_col1, ctrl_col2 = st.columns([0.45, 0.55])

    with ctrl_col1:
        st.caption("Single-Cell Movement Pad:")
        m_up, m_down, m_left, m_right = st.columns(4)
        with m_up:
            if st.button("▲ N", use_container_width=True, help="Step North (y - 1)"):
                success, msg = engine.move(RobotDirection.NORTH)
                if not success:
                    st.toast(msg, icon="⚠️")
                st.rerun()
        with m_down:
            if st.button("▼ S", use_container_width=True, help="Step South (y + 1)"):
                success, msg = engine.move(RobotDirection.SOUTH)
                if not success:
                    st.toast(msg, icon="⚠️")
                st.rerun()
        with m_left:
            if st.button("◀ W", use_container_width=True, help="Step West (x - 1)"):
                success, msg = engine.move(RobotDirection.WEST)
                if not success:
                    st.toast(msg, icon="⚠️")
                st.rerun()
        with m_right:
            if st.button("▶ E", use_container_width=True, help="Step East (x + 1)"):
                success, msg = engine.move(RobotDirection.EAST)
                if not success:
                    st.toast(msg, icon="⚠️")
                st.rerun()

    with ctrl_col2:
        st.caption("Simulation State Actions:")
        a_pause, a_resume, a_reset = st.columns(3)
        with a_pause:
            if st.button("⏸ Pause", use_container_width=True):
                engine.pause()
                st.rerun()
        with a_resume:
            if st.button("▶ Resume", use_container_width=True):
                engine.resume()
                st.rerun()
        with a_reset:
            confirm_reset = st.checkbox("Confirm Reset", value=False)
            if st.button("↺ Reset", use_container_width=True, type="secondary"):
                if not confirm_reset:
                    st.warning("Please check 'Confirm Reset' first.")
                else:
                    engine.reset(confirm=True)
                    st.success("Simulation reset.")
                    st.rerun()

    # Warehouse Edit Mode Panel
    if show_edit_mode:
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title" style="color: #f59e0b;">Warehouse Edit Mode — Obstacle Management</div>
        </div>
        """, unsafe_allow_html=True)

        c_x, c_y = st.columns(2)
        with c_x:
            edit_x = st.number_input("Coordinate X", min_value=0, max_value=warehouse.width - 1, value=5)
        with c_y:
            edit_y = st.number_input("Coordinate Y", min_value=0, max_value=warehouse.height - 1, value=6)

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Add Obstacle Barrier", use_container_width=True):
                can_add, reason = warehouse.can_place_obstacle(edit_x, edit_y)
                if can_add:
                    warehouse.add_obstacle(edit_x, edit_y)
                    st.success(f"Added barrier at ({edit_x}, {edit_y}).")
                    st.rerun()
                else:
                    st.error(f"Placement rejected: {reason}")
        with b2:
            if st.button("Remove Barrier", use_container_width=True):
                if warehouse.remove_obstacle(edit_x, edit_y):
                    st.success(f"Removed barrier at ({edit_x}, {edit_y}).")
                    st.rerun()
                else:
                    st.warning(f"No removable barrier at ({edit_x}, {edit_y}).")
        with b3:
            if st.button("Discard Edits", use_container_width=True):
                warehouse.discard_edits()
                st.info("Layout restored to default.")
                st.rerun()

    # Shelf Inspection Details Card
    if selected_shelf_id and selected_shelf_id in warehouse.racks_by_id:
        shelf = warehouse.racks_by_id[selected_shelf_id]
        shelf_products = warehouse.get_products_at_shelf(selected_shelf_id)

        st.markdown(f"""
        <div class="panel-box">
            <div class="panel-title">
                <span>Shelf Inspection: {shelf.id} ({shelf.name})</span>
                <span style="color: #60a5fa; font-size: 11px;">Zone: {shelf.zone}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 12px; font-size: 12px;">
                <div><span style="color:#9ca3af;">Shelf Cell:</span> <strong>({shelf.x}, {shelf.y})</strong></div>
                <div><span style="color:#9ca3af;">Pickup Cell:</span> <strong style="color:#10b981;">({shelf.pickup_position.x}, {shelf.pickup_position.y})</strong></div>
                <div><span style="color:#9ca3af;">Capacity:</span> <strong>{shelf.max_capacity} units</strong></div>
                <div><span style="color:#9ca3af;">Stored Count:</span> <strong>{shelf.current_stock_count} units</strong></div>
            </div>
        """, unsafe_allow_html=True)

        if shelf_products:
            prod_table = [
                {
                    "SKU": p.id,
                    "Name": p.name,
                    "Category": p.category,
                    "Unit Weight (kg)": p.unit_weight_kg,
                    "Stock": p.initial_stock,
                    "Status": "ACTIVE" if p.active else "INACTIVE"
                }
                for p in shelf_products
            ]
            st.dataframe(prod_table, use_container_width=True, height=120)
        st.markdown("</div>", unsafe_allow_html=True)

    # Order Lifecycle Progress Indicator
    st.markdown("""
    <div class="panel-box" style="padding: 12px 16px;">
        <div class="panel-title" style="margin-bottom: 8px;">Order Lifecycle Progress</div>
        <div class="progress-bar-shell">
            <span class="prog-step active">1. DRAFT</span>
            <span class="prog-step">2. VALIDATED</span>
            <span class="prog-step">3. PLANNING</span>
            <span class="prog-step">4. IN PROGRESS</span>
            <span class="prog-step">5. RETURNING</span>
            <span class="prog-step">6. DELIVERED</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Live AI Decision Log Panel (Consumes engine.events)
    recent_events = engine.events.get_recent(limit=15)
    st.markdown(f"""
    <div class="panel-box">
        <div class="panel-title">
            <span>Live AI Decision Log</span>
            <span style="color: #64748b; font-size: 11px;">Total Events: {len(engine.events.events)}</span>
        </div>
        <div class="log-container">
    """, unsafe_allow_html=True)

    category_colors = {
        "SYSTEM": "#38bdf8",
        "NAVIGATION": "#10b981",
        "ACTION": "#a78bfa",
        "ROBOT": "#f59e0b",
        "ORDER": "#ec4899",
        "ERROR": "#ef4444"
    }

    outcome_colors = {
        "SUCCESS": "#34d399",
        "BLOCKED": "#f59e0b",
        "REJECTED": "#f87171",
        "FAILED": "#ef4444",
        "INFO": "#94a3b8"
    }

    for ev in recent_events:
        c_color = category_colors.get(ev.category, "#94a3b8")
        o_color = outcome_colors.get(ev.outcome, "#94a3b8")
        st.markdown(f"""
        <div class="log-entry">
            <span class="log-time">[{ev.timestamp}]</span>
            <span class="log-cat" style="color: {c_color};">#{ev.event_id} {ev.category}</span>
            <span class="log-outcome" style="color: {o_color};">[{ev.outcome}]</span>
            <span class="log-msg">{ev.explanation}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

from simulation.fulfillment import OrderFulfillmentManager

# Initialize Fulfillment Manager in Session State
if "fulfillment" not in st.session_state:
    st.session_state.fulfillment = OrderFulfillmentManager(engine)
fulfillment: OrderFulfillmentManager = st.session_state.fulfillment

# Cart state for multi-product orders
if "cart" not in st.session_state:
    st.session_state.cart = []

with side_col:
    # Order Dispatch Panel
    st.markdown("""
    <div class="panel-box">
        <div class="panel-title">Order Fulfillment Control</div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        active_products = [p for p in warehouse.products_by_id.values() if p.active]
        options = {f"{p.name} ({p.id})": p for p in active_products}

        selected_label = st.selectbox(
            "Select Product to Add",
            options=list(options.keys()),
            help="Choose an active product from warehouse catalog"
        )
        selected_prod = options.get(selected_label)

        col_qty, col_stock = st.columns(2)
        with col_qty:
            qty = st.number_input("Quantity", min_value=1, max_value=10, value=1)
        with col_stock:
            rec = fulfillment.inv_repo.get_stock(selected_prod.id) if selected_prod else None
            available_stock = rec.available if rec else 0
            st.metric("Available", available_stock)

        # Cart management
        c_add, c_clear = st.columns(2)
        with c_add:
            if st.button("+ Add to Order", use_container_width=True):
                if selected_prod:
                    st.session_state.cart.append((selected_prod.id, qty, selected_prod.name, selected_prod.unit_weight_kg))
                    st.rerun()
        with c_clear:
            if st.button("Clear Cart", use_container_width=True):
                st.session_state.cart.clear()
                st.rerun()

        # Display current cart
        if st.session_state.cart:
            st.caption(f"Cart: {len(st.session_state.cart)} item(s)")
            cart_display = [
                {"SKU": item[0], "Product": item[2], "Qty": item[1], "Weight (kg)": f"{item[3]*item[1]:.2f}"}
                for item in st.session_state.cart
            ]
            st.dataframe(cart_display, use_container_width=True, height=100)

        # Order creation button
        btn_create = st.button("1. Validate & Reserve Order", use_container_width=True, type="primary")
        if btn_create:
            if not st.session_state.cart:
                # Default to selected product if cart is empty
                items_to_submit = [(selected_prod.id, qty)] if selected_prod else []
            else:
                items_to_submit = [(item[0], item[1]) for item in st.session_state.cart]

            ok, msg, oid = fulfillment.validate_and_create_order(items_to_submit)
            if ok:
                st.session_state.cart.clear()
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        # Mission planning & execution buttons if active order exists
        if fulfillment.active_order_id:
            st.markdown(f"**Active Order:** `{fulfillment.active_order_id}`")
            col_pl1, col_pl2 = st.columns(2)
            with col_pl1:
                if st.button("2. Plan Mission", use_container_width=True):
                    p_ok, p_msg = fulfillment.plan_order_mission()
                    if p_ok:
                        st.success(p_msg)
                        st.rerun()
                    else:
                        st.error(p_msg)

            with col_pl2:
                if st.button("Cancel & Restock", use_container_width=True):
                    c_ok, c_msg = fulfillment.cancel_active_order()
                    if c_ok:
                        st.info(c_msg)
                        st.rerun()

            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                if st.button("Step Next Action", use_container_width=True):
                    s_ok, s_msg, is_done = fulfillment.execute_next_step()
                    if s_ok:
                        st.toast(s_msg, icon="✅")
                    else:
                        st.toast(s_msg, icon="⚠️")
                    st.rerun()

            with col_ex2:
                if st.button("▶ Run Full Mission", use_container_width=True, type="secondary"):
                    report = fulfillment.run_full_mission()
                    if report.status == "DELIVERED":
                        st.success(f"Order {report.order_id} DELIVERED! ({report.items_delivered} items, {report.steps_travelled} steps)")
                    else:
                        st.warning(f"Mission halted with status {report.status}")
                    st.rerun()

    # Live Robot Telemetry Panel
    st.markdown(f"""
    <div class="panel-box" style="margin-top: 14px;">
        <div class="panel-title">Robot Telemetry</div>
        <div class="telemetry-row">
            <span class="telemetry-label">Robot Unit</span>
            <span class="telemetry-val">{robot.id}</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Status</span>
            <span class="telemetry-val" style="color: {robot_status_color};">{robot.state.value}</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Position</span>
            <span class="telemetry-val">({robot.position.x}, {robot.position.y})</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Orientation</span>
            <span class="telemetry-val">{robot.facing.value}</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Payload</span>
            <span class="telemetry-val">{robot.current_load_kg:.2f} / {robot.max_capacity_kg:.1f} kg</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Carried SKUs</span>
            <span class="telemetry-val">{sum(robot.carried_items.values())} items</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Distance Travelled</span>
            <span class="telemetry-val">{robot.distance_travelled} cells</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Active Order</span>
            <span class="telemetry-val">{fulfillment.active_order_id or "NONE"}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
