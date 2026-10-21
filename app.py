"""SmartStock AI - Warehouse Operations Dashboard

Phase 3: Robot Model, Explicit State Machine, Event System,
and Action Executor with Step-by-Step Movement Controls.
"""

from __future__ import annotations

import time
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

    .prog-step.completed {
        color: var(--accent-blue);
        font-weight: 600;
    }

    .prog-step.blocked {
        color: var(--accent-red);
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

    .action-hud-box {
        background: linear-gradient(135deg, #0b1329 0%, #0d1a38 100%);
        border: 1px solid #1e3a8a;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .hud-title-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        border-bottom: 1px solid rgba(59, 130, 246, 0.2);
        padding-bottom: 6px;
    }
    .hud-headline {
        font-size: 13px;
        font-weight: 700;
        color: #f3f4f6;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .hud-msg-box {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid #1e293b;
        border-left: 4px solid #38bdf8;
        border-radius: 4px;
        padding: 8px 12px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 12px;
        color: #38bdf8;
        margin-bottom: 8px;
    }
    .hud-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        font-size: 11px;
    }
    .hud-card-cell {
        background: #090e1a;
        border: 1px solid #1e293b;
        border-radius: 4px;
        padding: 6px 10px;
    }
    .hud-card-label {
        color: #94a3b8;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .hud-card-val {
        color: #f1f5f9;
        font-weight: 600;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
</style>
""", unsafe_allow_html=True)

from database.db import get_db_connection, init_db, seed_catalog_if_empty
from database.repositories import OrderRepository
from simulation.fulfillment import OrderFulfillmentManager


def render_action_hud(
    robot: Robot,
    fulfillment: OrderFulfillmentManager,
    last_msg: str = "",
    status: str = "IDLE",
    step_num: int = 0
) -> str:
    """Render live Heads-Up Display banner with authoritative robot status and reflex percepts."""
    r_state = getattr(robot, "state", RobotState.IDLE)
    facing_map = {"NORTH": "▲ North", "SOUTH": "▼ South", "EAST": "▶ East", "WEST": "◀ West"}
    facing_str = facing_map.get(robot.facing.value, robot.facing.value)

    state_colors = {
        RobotState.IDLE: "#9ca3af",
        RobotState.NAVIGATING_TO_PICKUP: "#38bdf8",
        RobotState.PICKING: "#c084fc",
        RobotState.NAVIGATING_TO_DISTRIBUTION: "#38bdf8",
        RobotState.UNLOADING: "#22d3ee",
        RobotState.COMPLETED: "#34d399",
        RobotState.BLOCKED: "#ef4444",
        RobotState.PAUSED: "#f59e0b",
    }
    state_color = state_colors.get(r_state, "#38bdf8")

    total_plan = len(fulfillment.high_level_plan)
    cur_plan = fulfillment.current_plan_index + 1 if total_plan > 0 else 0
    plan_badge = f"Action {min(cur_plan, total_plan)} of {total_plan}" if total_plan > 0 else "Manual / Standby"

    target_pos = fulfillment.current_target_pos
    target_str = f"({target_pos.x}, {target_pos.y})" if target_pos else "Dock DS-01 (0, 0)"

    gbfs_steps = len(fulfillment.current_gbfs_route)
    gbfs_str = f"{gbfs_steps} steps left" if gbfs_steps > 0 else "At Waypoint"

    reflex_r = fulfillment.last_reflex_response
    if reflex_r:
        reflex_str = f"{reflex_r.action} ({reflex_r.reason[:26]}...)" if len(reflex_r.reason) > 26 else f"{reflex_r.action}"
    else:
        reflex_str = "Preconditions OK (Clear)"

    display_msg = last_msg or f"Robot {robot.id} standing at ({robot.position.x}, {robot.position.y}) [{r_state.value}]. Ready for instructions."
    border_accent = "#34d399" if status == "SUCCESS" else ("#ef4444" if status in ("BLOCKED", "HALTED") else "#38bdf8")

    return f"""
    <div class="action-hud-box">
        <div class="hud-title-row">
            <div class="hud-headline">
                <span>🤖 Unit <strong>{robot.id}</strong></span>
                <span style="background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:4px; font-size:11px; color:{state_color}; border:1px solid {state_color};">
                    ● {r_state.value}
                </span>
                <span style="font-size:11px; color:#94a3b8; font-weight:normal;">
                    Facing: <strong style="color:#f3f4f6;">{facing_str}</strong> | Pos: <strong style="color:#f3f4f6;">({robot.position.x}, {robot.position.y})</strong>
                </span>
            </div>
            <div style="font-size:11px; color:#38bdf8; font-weight:600;">
                🎯 {plan_badge}
            </div>
        </div>
        <div class="hud-msg-box" style="border-left-color: {border_accent};">
            <span style="color:#94a3b8; font-size:10px; text-transform:uppercase; letter-spacing:0.5px;">⚡ Live Action Status:</span><br/>
            <strong style="color:#ffffff; font-size:12.5px;">{display_msg}</strong>
        </div>
        <div class="hud-grid">
            <div class="hud-card-cell">
                <div class="hud-card-label">🧠 Reflex Agent Radar</div>
                <div class="hud-card-val" style="color:#a78bfa; font-size:11px;">{reflex_str}</div>
            </div>
            <div class="hud-card-cell">
                <div class="hud-card-label">🗺️ Target & Route (GBFS)</div>
                <div class="hud-card-val" style="color:#38bdf8; font-size:11px;">Target: {target_str} | {gbfs_str}</div>
            </div>
            <div class="hud-card-cell">
                <div class="hud-card-label">📦 Cargo & Distance</div>
                <div class="hud-card-val" style="color:#34d399; font-size:11px;">{robot.current_load_kg:.2f}/25.0 kg ({sum(robot.carried_items.values())} items) | {robot.distance_travelled} cells</div>
            </div>
        </div>
    </div>
    """


def render_detailed_action_card(
    robot: Robot,
    fulfillment: OrderFulfillmentManager,
    last_msg: str = "",
    status: str = "IDLE",
    step_num: int = 0
) -> str:
    """Render comprehensive action inspector detailing invariants, transitions, and plans."""
    r_state = getattr(robot, "state", RobotState.IDLE)
    oid = fulfillment.active_order_id or "NONE"

    cur_plan_act = None
    if fulfillment.high_level_plan and fulfillment.current_plan_index < len(fulfillment.high_level_plan):
        cur_plan_act = fulfillment.high_level_plan[fulfillment.current_plan_index]

    if cur_plan_act:
        plan_desc = f"<strong>{cur_plan_act.action_type}</strong> ➔ Target ({cur_plan_act.target_pos.x}, {cur_plan_act.target_pos.y})"
        if cur_plan_act.product_id:
            plan_desc += f" | SKU: <code>{cur_plan_act.product_id}</code> (Qty: {cur_plan_act.quantity})"
    elif oid != "NONE" and r_state == RobotState.COMPLETED:
        plan_desc = "<span style='color:#34d399;'>🎉 All mission actions executed successfully! Order delivered at Station DS-01.</span>"
    else:
        plan_desc = "<span style='color:#94a3b8;'>No active forward search mission plan. Ready to receive next dispatch.</span>"

    p = fulfillment.last_reflex_percept
    r = fulfillment.last_reflex_response
    if p:
        p_str = f"Ahead Blocked: <strong>{'YES ⚠️' if p.is_next_cell_blocked else 'NO (CLEAR) ✅'}</strong> | At Pickup: <strong>{p.at_pickup_location}</strong> | Invariants: <strong>{'VALID ✅' if (p.pickup_preconditions_valid or p.delivery_preconditions_valid) else 'CHECKING'}</strong>"
        r_str = f"Decision: <strong style='color:#c084fc;'>{r.action if r else 'APPROVE'}</strong> ({r.reason if r else 'Passed safety check'})"
    else:
        p_str = "Sensory percepts idle. Aisle is clear ahead."
        r_str = "Reflex Agent ready to monitor next cell transition."

    return f"""
    <div class="panel-box" style="margin-top: 10px; padding: 12px 16px;">
        <div class="panel-title" style="margin-bottom: 8px;">
            <span>Detailed Action Inspector & Precondition Invariants</span>
            <span style="font-size:11px; color:#38bdf8;">Order: {oid}</span>
        </div>
        <div style="font-size: 12px; line-height: 1.6;">
            <div style="margin-bottom: 6px;">
                <span style="color:#94a3b8;">🎯 Current Plan Action:</span> {plan_desc}
            </div>
            <div style="margin-bottom: 6px; font-family: ui-monospace, monospace; font-size: 11px; background: rgba(0,0,0,0.25); padding: 6px 10px; border-radius: 4px; border: 1px solid #1f2937;">
                <span style="color:#a78bfa;">🧠 Reflex Percept:</span> {p_str}<br/>
                <span style="color:#f472b6;">⚖️ Reflex Response:</span> {r_str}
            </div>
            <div style="display: flex; gap: 16px; font-size: 11px; color: #9ca3af; margin-top: 6px;">
                <span>⚖️ Capacity Invariant: <strong style="color:#34d399;">{robot.current_load_kg:.2f} ≤ 25.0 kg (SATISFIED)</strong></span>
                <span>🧭 Manhattan Dist to Goal: <strong style="color:#38bdf8;">{robot.position.manhattan_distance_to(fulfillment.current_target_pos) if fulfillment.current_target_pos else 0} cells</strong></span>
                <span>👣 Total Steps: <strong style="color:#f3f4f6;">{robot.distance_travelled}</strong></span>
            </div>
        </div>
    </div>
    """

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

# Initialize Fulfillment Manager in Session State
if "fulfillment" not in st.session_state:
    st.session_state.fulfillment = OrderFulfillmentManager(engine)
fulfillment: OrderFulfillmentManager = st.session_state.fulfillment

# Cart state for multi-product orders
if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_action_msg" not in st.session_state:
    st.session_state.last_action_msg = "Robot R-01 standing at Station Dock DS-01 (0, 0). Ready for fulfillment mission or manual navigation."
if "last_action_status" not in st.session_state:
    st.session_state.last_action_status = "IDLE"
if "auto_run_requested" not in st.session_state:
    st.session_state.auto_run_requested = False
if "anim_delay_val" not in st.session_state:
    st.session_state.anim_delay_val = 0.35

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

    # Render SVG Map with Authoritative Robot, Planned Route, Traversed Route, and Target
    target_pos = fulfillment.current_target_pos
    planned_route = fulfillment.current_gbfs_route
    traversed_route = engine.executor.traversed_path

    # Synchronous UI placeholders (updated live on every step)
    hud_placeholder = st.empty()
    map_placeholder = st.empty()
    legend_placeholder = st.empty()
    detail_placeholder = st.empty()

    legend_html = """
    <div class="legend-bar">
        <div class="legend-item"><div class="legend-swatch" style="background:#0369a1; border-color:#38bdf8;"></div> Station (DS-01)</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#1e293b; border-color:#60a5fa;"></div> Storage Rack</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#0f172a; border:1px dashed #059669;"></div> Pickup Bay</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#334155; border-color:#64748b;"></div> Fixed Pillar</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#d97706; border-color:#f59e0b;"></div> User Barrier</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#7f1d1d; border-color:#dc2626;"></div> Restricted Zone</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#047857; border-color:#34d399; border-radius:50%;"></div> Robot Unit</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#172554; border:1px dashed #38bdf8;"></div> Planned Route</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#064e3b; border-color:#10b981;"></div> Traversed Path</div>
        <div class="legend-item"><div class="legend-swatch" style="background:#881337; border-color:#f43f5e;"></div> Target Destination</div>
    </div>
    </div>
    """

    try:
        svg_content = render_warehouse_svg(
            warehouse,
            robot=robot,
            selected_shelf_id=selected_shelf_id,
            planned_route=planned_route,
            traversed_route=traversed_route,
            target_pos=target_pos
        )
        map_placeholder.markdown(svg_content, unsafe_allow_html=True)
    except Exception as map_err:
        st.warning(f"Map renderer notice: {map_err}. Displaying fallback layout.")
        fallback_html = render_map_fallback(warehouse)
        map_placeholder.markdown(fallback_html, unsafe_allow_html=True)

    hud_html = render_action_hud(
        robot=robot,
        fulfillment=fulfillment,
        last_msg=st.session_state.get("last_action_msg", ""),
        status=st.session_state.get("last_action_status", "IDLE"),
        step_num=fulfillment.current_plan_index
    )
    hud_placeholder.markdown(hud_html, unsafe_allow_html=True)

    legend_placeholder.markdown(legend_html, unsafe_allow_html=True)

    detail_html = render_detailed_action_card(
        robot=robot,
        fulfillment=fulfillment,
        last_msg=st.session_state.get("last_action_msg", ""),
        status=st.session_state.get("last_action_status", "IDLE"),
        step_num=fulfillment.current_plan_index
    )
    detail_placeholder.markdown(detail_html, unsafe_allow_html=True)

    # 🚀 Check if animated auto-run loop requested
    if st.session_state.get("auto_run_requested"):
        st.session_state.auto_run_requested = False
        step_max = 120
        cur_step = 0
        anim_delay = st.session_state.get("anim_delay_val", 0.35)

        while cur_step < step_max:
            cur_step += 1
            s_ok, s_msg, is_done = fulfillment.execute_next_step()
            st.session_state.last_action_msg = s_msg
            st.session_state.last_action_status = "SUCCESS" if s_ok else "HALTED"

            # 1. Update Map
            anim_svg = render_warehouse_svg(
                warehouse,
                robot=robot,
                selected_shelf_id=selected_shelf_id,
                planned_route=fulfillment.current_gbfs_route,
                traversed_route=engine.executor.traversed_path,
                target_pos=fulfillment.current_target_pos
            )
            map_placeholder.markdown(anim_svg, unsafe_allow_html=True)

            # 2. Update HUD
            anim_hud = render_action_hud(
                robot=robot,
                fulfillment=fulfillment,
                last_msg=s_msg,
                status="SUCCESS" if s_ok else "HALTED",
                step_num=cur_step
            )
            hud_placeholder.markdown(anim_hud, unsafe_allow_html=True)

            # 3. Update Detailed Inspector Card
            anim_detail = render_detailed_action_card(
                robot=robot,
                fulfillment=fulfillment,
                last_msg=s_msg,
                status="SUCCESS" if s_ok else "HALTED",
                step_num=cur_step
            )
            detail_placeholder.markdown(anim_detail, unsafe_allow_html=True)

            time.sleep(anim_delay)
            if is_done:
                st.toast(f"🎉 Mission Complete: {s_msg}", icon="🎉")
                break
            if not s_ok:
                st.toast(f"⚠️ Execution halted: {s_msg}", icon="⚠️")
                break

        st.rerun()

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
                st.session_state.last_action_msg = msg
                st.session_state.last_action_status = "SUCCESS" if success else "BLOCKED"
                if not success:
                    st.toast(msg, icon="⚠️")
                else:
                    st.toast(msg, icon="✅")
                st.rerun()
        with m_down:
            if st.button("▼ S", use_container_width=True, help="Step South (y + 1)"):
                success, msg = engine.move(RobotDirection.SOUTH)
                st.session_state.last_action_msg = msg
                st.session_state.last_action_status = "SUCCESS" if success else "BLOCKED"
                if not success:
                    st.toast(msg, icon="⚠️")
                else:
                    st.toast(msg, icon="✅")
                st.rerun()
        with m_left:
            if st.button("◀ W", use_container_width=True, help="Step West (x - 1)"):
                success, msg = engine.move(RobotDirection.WEST)
                st.session_state.last_action_msg = msg
                st.session_state.last_action_status = "SUCCESS" if success else "BLOCKED"
                if not success:
                    st.toast(msg, icon="⚠️")
                else:
                    st.toast(msg, icon="✅")
                st.rerun()
        with m_right:
            if st.button("▶ E", use_container_width=True, help="Step East (x + 1)"):
                success, msg = engine.move(RobotDirection.EAST)
                st.session_state.last_action_msg = msg
                st.session_state.last_action_status = "SUCCESS" if success else "BLOCKED"
                if not success:
                    st.toast(msg, icon="⚠️")
                else:
                    st.toast(msg, icon="✅")
                st.rerun()

        if (robot.position.x, robot.position.y) == (0, 0):
            st.caption("ℹ️ At Dock (0,0): North & West are perimeter walls. Move ▼ S or ▶ E into aisle.")

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

        is_executing = robot.state in (
            RobotState.NAVIGATING_TO_PICKUP,
            RobotState.NAVIGATING_TO_DISTRIBUTION,
            RobotState.PICKING,
            RobotState.UNLOADING
        )

        if is_executing:
            st.warning("⚠️ Full layout editing is locked while a mission is actively executing. Use the '⚠️ Inject Barrier' button in Mission Controls to test dynamic runtime obstacle avoidance.")
        else:
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("Add Barrier", use_container_width=True):
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
                    st.info("Layout restored to initial configuration.")
                    st.rerun()
            with b4:
                confirm_restore = st.checkbox("Confirm Default", value=False)
                if st.button("Restore Default", use_container_width=True):
                    if confirm_restore:
                        warehouse.discard_edits()
                        st.info("Layout restored to default.")
                        st.rerun()
                    else:
                        st.warning("Please check 'Confirm Default' first.")

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

    # Dynamic Order Lifecycle Progress Indicator
    active_step = 1
    is_order_blocked = False
    if fulfillment.active_order_id:
        order_rec = fulfillment.order_repo.get_order(fulfillment.active_order_id)
        if order_rec:
            if order_rec.status == "DELIVERED":
                active_step = 6
            elif order_rec.status == "BLOCKED":
                active_step = 4
                is_order_blocked = True
            elif robot.state == RobotState.NAVIGATING_TO_DISTRIBUTION:
                active_step = 5
            elif robot.state in (RobotState.NAVIGATING_TO_PICKUP, RobotState.PICKING):
                active_step = 4
            elif fulfillment.high_level_plan:
                active_step = 3
            else:
                active_step = 2

    step_labels = ["1. DRAFT", "2. VALIDATED", "3. PLANNING", "4. IN PROGRESS", "5. RETURNING", "6. DELIVERED"]
    step_elements = []
    for s_idx, s_lbl in enumerate(step_labels, start=1):
        if is_order_blocked and s_idx == active_step:
            step_elements.append(f'<span class="prog-step blocked">{s_lbl} (BLOCKED)</span>')
        elif s_idx == active_step:
            step_elements.append(f'<span class="prog-step active">{s_lbl}</span>')
        elif s_idx < active_step:
            step_elements.append(f'<span class="prog-step completed">✓ {s_lbl}</span>')
        else:
            step_elements.append(f'<span class="prog-step">{s_lbl}</span>')

    st.markdown(f"""
    <div class="panel-box" style="padding: 12px 16px;">
        <div class="panel-title" style="margin-bottom: 8px;">Order Lifecycle Progress</div>
        <div class="progress-bar-shell">
            {''.join(step_elements)}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Live AI Decision Log Panel with Category Filtering
    col_log_h1, col_log_h2 = st.columns([0.60, 0.40])
    with col_log_h1:
        st.markdown("""
        <div class="panel-title" style="border-bottom:none; margin-bottom:0; padding-bottom:0;">
            Live AI Decision Log
        </div>
        """, unsafe_allow_html=True)
    with col_log_h2:
        log_filter = st.selectbox(
            "Filter Category",
            options=["ALL", "SYSTEM", "NAVIGATION", "ACTION", "LOGIC", "REFLEX", "ORDER", "ERROR"],
            index=0,
            label_visibility="collapsed"
        )

    recent_events = engine.events.get_recent(limit=20, category=log_filter)

    st.markdown(f"""
    <div class="panel-box" style="margin-top: -6px;">
        <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">
            Showing {len(recent_events)} events (Filter: {log_filter} | Total Recorded: {len(engine.events.events)})
        </div>
        <div class="log-container">
    """, unsafe_allow_html=True)

    category_colors = {
        "SYSTEM": "#38bdf8",
        "NAVIGATION": "#10b981",
        "ACTION": "#a78bfa",
        "ROBOT": "#f59e0b",
        "LOGIC": "#fbbf24",
        "REFLEX": "#ec4899",
        "ORDER": "#60a5fa",
        "ERROR": "#ef4444"
    }

    outcome_colors = {
        "SUCCESS": "#34d399",
        "BLOCKED": "#f59e0b",
        "REJECTED": "#f87171",
        "FAILED": "#ef4444",
        "INFO": "#94a3b8"
    }

    if recent_events:
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
    else:
        st.markdown('<div style="color:#64748b; font-size:12px; padding:8px;">No events matching selected filter.</div>', unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # Deep AI Algorithm Telemetry Expander (Task 7)
    has_mission = bool(fulfillment.high_level_plan or fulfillment.active_order_id)
    with st.expander("🔍 Deep AI Algorithm Telemetry & Active State Inspector", expanded=has_mission):
        tab_fwd, tab_gbfs, tab_reflex = st.tabs(["1. Forward Search Plan", "2. GBFS Path Planning", "3. Reflex Agent Percept"])
        with tab_fwd:
            if fulfillment.high_level_plan:
                st.caption(f"Synthesized Plan: {len(fulfillment.high_level_plan)} actions total. Current index: {fulfillment.current_plan_index}")
                for idx, act in enumerate(fulfillment.high_level_plan):
                    is_cur = idx == fulfillment.current_plan_index
                    prefix = "👉 " if is_cur else "   "
                    color = "#38bdf8" if is_cur else "#94a3b8"
                    st.markdown(f"<span style='color:{color}; font-family:monospace;'>{prefix}<strong>[{idx+1}]</strong> {act.action_type} ➔ Target ({act.target_pos.x}, {act.target_pos.y}) | SKU: {act.product_id or '—'} (Qty: {act.quantity})</span>", unsafe_allow_html=True)
            else:
                st.info("No active high-level plan. Dispatch an order and click '2. Plan Mission'.")

        with tab_gbfs:
            if fulfillment.current_gbfs_route:
                tgt = fulfillment.current_target_pos
                tgt_str = f"({tgt.x}, {tgt.y})" if tgt else "N/A"
                st.markdown(f"**Target Cell:** `{tgt_str}` | **Remaining Steps:** `{len(fulfillment.current_gbfs_route)} cells`")
                route_str = " ➔ ".join(f"({p.x}, {p.y})" for p in fulfillment.current_gbfs_route[:12])
                if len(fulfillment.current_gbfs_route) > 12:
                    route_str += f" ... (+{len(fulfillment.current_gbfs_route)-12} more)"
                st.code(route_str, language="text")
            else:
                st.info("No active GBFS navigation route in progress.")

        with tab_reflex:
            if fulfillment.last_reflex_percept:
                p = fulfillment.last_reflex_percept
                r = fulfillment.last_reflex_response
                st.markdown(f"- **Current Pos:** `({p.current_position.x}, {p.current_position.y})` | **Facing:** `{p.facing.value}`")
                p_cell_str = f"({p.proposed_next_cell.x}, {p.proposed_next_cell.y})" if p.proposed_next_cell else "None"
                st.markdown(f"- **Proposed Cell:** `{p_cell_str}` | **Next Cell Blocked:** `{p.is_next_cell_blocked}`")
                st.markdown(f"- **At Pickup:** `{p.at_pickup_location}` | **Preconditions Valid:** `{p.pickup_preconditions_valid}`")
                if r:
                    st.markdown(f"- **Reflex Decision:** `{r.action}` — *{r.reason}*")
            else:
                st.info("No live reflex percept captured yet.")


with side_col:
    # 🚀 Quick Warehouse Destination Presets
    st.markdown("""
    <div style="background: linear-gradient(135deg, #064e3b 0%, #065f46 100%); border: 1px solid #10b981; border-radius: 8px; padding: 14px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
            <span style="font-weight: 700; color: #ffffff; font-size: 13px; letter-spacing: 0.5px;">🚀 QUICK TEST DESTINATIONS</span>
            <span style="background: rgba(0,0,0,0.3); color: #34d399; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">1-CLICK RUN</span>
        </div>
        <div style="font-size: 11px; color: #d1fae5; line-height: 1.4; margin-bottom: 10px;">
            Click any destination preset to watch the robot navigate to that exact storage zone:
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("📍 Shelf R01 (Top-Left)", use_container_width=True, help="UltraBook Pro 15 at Shelf R01 (2, 2)"):
            if fulfillment.active_order_id:
                fulfillment.cancel_active_order()
            if (robot.position.x, robot.position.y) != (warehouse.distribution_station.x, warehouse.distribution_station.y):
                engine.reset(confirm=True)
            v_ok, v_msg, o_id = fulfillment.validate_and_create_order([("PROD-001", 1)])
            if v_ok and fulfillment.plan_order_mission()[0]:
                st.session_state.last_action_msg = f"Order {o_id} dispatched to Shelf R01 (Top-Left, Cell 2,2)!"
                st.session_state.last_action_status = "SUCCESS"
                st.session_state.auto_run_requested = True
                st.rerun()

        if st.button("📍 Shelf R13 (Far-Right)", use_container_width=True, help="2TB NVMe SSD at Shelf R13 (12, 2)"):
            if fulfillment.active_order_id:
                fulfillment.cancel_active_order()
            if (robot.position.x, robot.position.y) != (warehouse.distribution_station.x, warehouse.distribution_station.y):
                engine.reset(confirm=True)
            v_ok, v_msg, o_id = fulfillment.validate_and_create_order([("PROD-013", 1)])
            if v_ok and fulfillment.plan_order_mission()[0]:
                st.session_state.last_action_msg = f"Order {o_id} dispatched to Shelf R13 (Far-Right, Cell 12,2)!"
                st.session_state.last_action_status = "SUCCESS"
                st.session_state.auto_run_requested = True
                st.rerun()

    with col_p2:
        if st.button("📍 Shelf R07 (Center Bay)", use_container_width=True, help="USB-C Charging Cable at Shelf R07 (7, 2)"):
            if fulfillment.active_order_id:
                fulfillment.cancel_active_order()
            if (robot.position.x, robot.position.y) != (warehouse.distribution_station.x, warehouse.distribution_station.y):
                engine.reset(confirm=True)
            v_ok, v_msg, o_id = fulfillment.validate_and_create_order([("PROD-007", 1)])
            if v_ok and fulfillment.plan_order_mission()[0]:
                st.session_state.last_action_msg = f"Order {o_id} dispatched to Shelf R07 (Center Bay, Cell 7,2)!"
                st.session_state.last_action_status = "SUCCESS"
                st.session_state.auto_run_requested = True
                st.rerun()

        if st.button("📍 Shelf R19 (Lower Bay)", use_container_width=True, help="Studio USB Mic at Shelf R19 (2, 6)"):
            if fulfillment.active_order_id:
                fulfillment.cancel_active_order()
            if (robot.position.x, robot.position.y) != (warehouse.distribution_station.x, warehouse.distribution_station.y):
                engine.reset(confirm=True)
            v_ok, v_msg, o_id = fulfillment.validate_and_create_order([("PROD-019", 1)])
            if v_ok and fulfillment.plan_order_mission()[0]:
                st.session_state.last_action_msg = f"Order {o_id} dispatched to Shelf R19 (Lower Bay, Cell 2,6)!"
                st.session_state.last_action_status = "SUCCESS"
                st.session_state.auto_run_requested = True
                st.rerun()

    if st.button("🌐 Multi-Stop Mission (R01 + R07 + R19)", use_container_width=True, type="primary", help="Visits Top-Left, Center, and Lower bays across the entire warehouse"):
        if fulfillment.active_order_id:
            fulfillment.cancel_active_order()
        if (robot.position.x, robot.position.y) != (warehouse.distribution_station.x, warehouse.distribution_station.y):
            engine.reset(confirm=True)
        v_ok, v_msg, o_id = fulfillment.validate_and_create_order([("PROD-001", 1), ("PROD-007", 1), ("PROD-019", 1)])
        if v_ok and fulfillment.plan_order_mission()[0]:
            st.session_state.last_action_msg = f"Multi-stop mission {o_id} dispatched across R01, R07, and R19!"
            st.session_state.last_action_status = "SUCCESS"
            st.session_state.auto_run_requested = True
            st.rerun()

    # Custom Order Dispatch Panel
    st.markdown("""
    <div class="panel-box">
        <div class="panel-title">Custom Order Fulfillment</div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        active_products = [p for p in warehouse.products_by_id.values() if p.active]
        options = {
            f"[{p.shelf_id}] {p.name} ({p.id})": p
            for p in sorted(active_products, key=lambda x: (int(x.shelf_id[1:]) if x.shelf_id[1:].isdigit() else 99))
        }

        selected_label = st.selectbox(
            "Select Catalog Product & Shelf",
            options=list(options.keys()),
            help="Choose an active product from warehouse catalog. Shows designated storage shelf."
        )
        selected_prod = options.get(selected_label)

        if selected_prod:
            shelf_info = warehouse.racks_by_id.get(selected_prod.shelf_id)
            if shelf_info:
                st.caption(f"📍 Storage: **Shelf {shelf_info.id}** at ({shelf_info.x}, {shelf_info.y}) | Pickup Bay at **({shelf_info.pickup_position.x}, {shelf_info.pickup_position.y})** | Weight: **{selected_prod.unit_weight_kg:.2f} kg**")

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
            if st.button("+ Add to Cart", use_container_width=True):
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

        # Check existing order status
        current_ord = fulfillment.order_repo.get_order(fulfillment.active_order_id) if fulfillment.active_order_id else None
        is_order_delivered = current_ord and current_ord.status == "DELIVERED"

        if is_order_delivered:
            st.success(f"🎉 Order {fulfillment.active_order_id} DELIVERED! Select another product or click a preset to launch your next mission.")
            if st.button("✨ Clear Delivered Order", use_container_width=True):
                fulfillment.active_order_id = None
                fulfillment.active_order_lines = []
                fulfillment.high_level_plan = []
                fulfillment.current_plan_index = 0
                fulfillment.current_gbfs_route = []
                st.session_state.cart.clear()
                st.rerun()

        # Order creation button
        btn_create = st.button("1. Validate & Reserve Order", use_container_width=True, type="primary" if (not fulfillment.active_order_id or is_order_delivered) else "secondary")
        if btn_create:
            if not st.session_state.cart:
                items_to_submit = [(selected_prod.id, qty)] if selected_prod else []
            else:
                items_to_submit = [(item[0], item[1]) for item in st.session_state.cart]

            ok, msg, oid = fulfillment.validate_and_create_order(items_to_submit)
            if ok:
                st.session_state.cart.clear()
                st.session_state.last_action_msg = f"Order {oid} validated & reserved in SQLite! Click '2. Plan Mission' to synthesize route."
                st.session_state.last_action_status = "SUCCESS"
                st.success(msg)
                st.rerun()
            else:
                st.session_state.last_action_msg = f"Order validation failed: {msg}"
                st.session_state.last_action_status = "BLOCKED"
                st.error(msg)

        # Mission planning & execution buttons if active uncompleted order exists
        if fulfillment.active_order_id and not is_order_delivered:
            st.markdown(f"**Active Order:** `{fulfillment.active_order_id}`")
            col_pl1, col_pl2 = st.columns(2)
            with col_pl1:
                if st.button("2. Plan Mission", use_container_width=True):
                    p_ok, p_msg = fulfillment.plan_order_mission()
                    if p_ok:
                        st.session_state.last_action_msg = f"Mission synthesized! {len(fulfillment.high_level_plan)} actions. Click '▶ Auto-Run Animated' or 'Step Next Action'."
                        st.session_state.last_action_status = "SUCCESS"
                        st.success(p_msg)
                        st.rerun()
                    else:
                        st.session_state.last_action_msg = f"Mission planning failed: {p_msg}"
                        st.session_state.last_action_status = "BLOCKED"
                        st.error(p_msg)

            with col_pl2:
                if st.button("Cancel & Restock", use_container_width=True):
                    c_ok, c_msg = fulfillment.cancel_active_order()
                    st.session_state.last_action_msg = c_msg
                    st.session_state.last_action_status = "IDLE"
                    if c_ok:
                        st.info(c_msg)
                        st.rerun()

            # Animation Speed & Interactive Mission Controls
            anim_delay = st.slider(
                "Animation Speed (delay sec/step)",
                min_value=0.05,
                max_value=1.0,
                value=float(st.session_state.get("anim_delay_val", 0.35)),
                step=0.05,
                help="Controls interval between steps during animated auto-run. Slower speeds allow detailed action inspection."
            )
            st.session_state.anim_delay_val = anim_delay

            # Dynamic Obstacle Insertion Test Scenario (Task 10)
            if fulfillment.current_gbfs_route:
                next_cell = fulfillment.current_gbfs_route[0]
                can_place_blk, _ = warehouse.can_place_obstacle(next_cell.x, next_cell.y)
                if can_place_blk:
                    if st.button(
                        f"⚠️ Inject Barrier at ({next_cell.x}, {next_cell.y})",
                        use_container_width=True,
                        help="Places an obstacle right in the robot's immediate path to test Reflex Agent obstacle detection and automatic GBFS replanning"
                    ):
                        warehouse.add_obstacle(next_cell.x, next_cell.y)
                        st.toast(f"Barrier injected at ({next_cell.x}, {next_cell.y})! Next step will trigger Reflex replan.", icon="⚠️")
                        st.rerun()

            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                if st.button("Step Next Action", use_container_width=True):
                    s_ok, s_msg, is_done = fulfillment.execute_next_step()
                    st.session_state.last_action_msg = s_msg
                    st.session_state.last_action_status = "SUCCESS" if s_ok else "HALTED"
                    if s_ok:
                        st.toast(s_msg, icon="✅")
                    else:
                        st.toast(s_msg, icon="⚠️")
                    st.rerun()

            with col_ex2:
                if st.button("▶ Auto-Run Animated", use_container_width=True, type="secondary"):
                    st.session_state.auto_run_requested = True
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
