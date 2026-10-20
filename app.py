"""SmartStock AI - Warehouse Operations Dashboard

Phase 2: Authoritative Warehouse Domain Model, Interactive SVG Map,
Shelf Inspection Engine, and Layout Editing Mode.
"""

from __future__ import annotations

import streamlit as st
from pathlib import Path
from utils.config import ConfigurationError
from simulation.warehouse import WarehouseGrid, get_default_warehouse
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

    .log-entry {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 11px;
        padding: 6px 8px;
        border-bottom: 1px solid #1a2234;
        display: flex;
        gap: 12px;
    }

    .log-time {
        color: #64748b;
        min-width: 65px;
    }

    .log-cat {
        color: var(--accent-blue);
        font-weight: 600;
        min-width: 90px;
    }

    .log-msg {
        color: var(--text-primary);
        flex: 1;
    }
</style>
""", unsafe_allow_html=True)

# 3. Initialize Authoritative Warehouse in Session State
if "warehouse" not in st.session_state:
    try:
        st.session_state.warehouse = get_default_warehouse()
    except ConfigurationError as exc:
        st.error(f"Configuration Initialization Alert: {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"Warehouse Engine Failure: {exc}")
        st.stop()

warehouse: WarehouseGrid = st.session_state.warehouse

# 4. Top Header Bar
st.markdown(f"""
<div class="header-bar">
    <div>
        <span class="brand-title">SMARTSTOCK AI</span>
        <span class="brand-sub"> / Warehouse Operations & Fulfillment</span>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 12px; color: #9ca3af;">Layout: {warehouse.width}×{warehouse.height} Grid</span>
        <span class="status-badge">MAP ENGINE ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. Compact KPI Row
col_k1, col_k2, col_k3, col_k4 = st.columns(4)

with col_k1:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Orders Today</div>
        <div class="kpi-value">0</div>
    </div>
    """, unsafe_allow_html=True)

with col_k2:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Active Orders</div>
        <div class="kpi-value">0</div>
    </div>
    """, unsafe_allow_html=True)

with col_k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Configured Shelves</div>
        <div class="kpi-value">{len(warehouse.racks_by_id)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_k4:
    user_obs_count = len(warehouse.user_added_obstacles)
    obs_label = f"{len(warehouse.fixed_obstacles)} Fixed" + (f" + {user_obs_count} User" if user_obs_count > 0 else "")
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Obstacles</div>
        <div class="kpi-value" style="font-size: 16px; line-height: 28px; color: #f59e0b;">{obs_label}</div>
    </div>
    """, unsafe_allow_html=True)

# 6. Main Dashboard Layout (68% Map/Inspector, 32% Side Controls/Telemetry)
main_col, side_col = st.columns([0.68, 0.32], gap="small")

with main_col:
    # Warehouse SVG Map Section
    st.markdown("""
    <div class="panel-box" style="padding-bottom: 10px;">
        <div class="panel-title">
            <span>Authoritative Live Warehouse Map (16 × 12 Grid)</span>
            <span style="color: #10b981; font-size: 11px;">● SVG Vector Renderer</span>
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

    # Render SVG Map with Fallback
    try:
        svg_content = render_warehouse_svg(warehouse, selected_shelf_id=selected_shelf_id)
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

    # Warehouse Edit Mode Panel
    if show_edit_mode:
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title" style="color: #f59e0b;">Warehouse Edit Mode — Obstacle Management</div>
        </div>
        """, unsafe_allow_html=True)

        c_x, c_y, c_act = st.columns([3, 3, 4])
        with c_x:
            edit_x = st.number_input("Coordinate X", min_value=0, max_value=warehouse.width - 1, value=5)
        with c_y:
            edit_y = st.number_input("Coordinate Y", min_value=0, max_value=warehouse.height - 1, value=6)

        # Inspect cell status
        cell_desc = "Walkable Aisle"
        if warehouse.is_distribution_station(edit_x, edit_y):
            cell_desc = "Distribution Station (Impassable for obstacles)"
        elif warehouse.is_rack(edit_x, edit_y):
            shelf = warehouse.get_shelf_at(edit_x, edit_y)
            cell_desc = f"Rack {shelf.id if shelf else ''} (Cannot place obstacle)"
        elif (edit_x, edit_y) in warehouse.fixed_obstacles:
            cell_desc = "Fixed Structural Pillar"
        elif (edit_x, edit_y) in warehouse.user_added_obstacles:
            cell_desc = "User-Added Barrier (Removable)"
        elif warehouse.is_restricted(edit_x, edit_y):
            cell_desc = "Restricted Zone"

        st.caption(f"Cell ({edit_x}, {edit_y}) Current Status: **{cell_desc}**")

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("Add Obstacle Barrier", use_container_width=True, type="secondary"):
                can_add, reason = warehouse.can_place_obstacle(edit_x, edit_y)
                if can_add:
                    warehouse.add_obstacle(edit_x, edit_y)
                    st.success(f"Added obstacle barrier at ({edit_x}, {edit_y}).")
                    st.rerun()
                else:
                    st.error(f"Cannot place obstacle: {reason}")

        with b2:
            if st.button("Remove Barrier", use_container_width=True):
                if warehouse.remove_obstacle(edit_x, edit_y):
                    st.success(f"Removed barrier from ({edit_x}, {edit_y}).")
                    st.rerun()
                else:
                    st.warning(f"No user-added barrier exists at ({edit_x}, {edit_y}). Fixed pillars cannot be removed.")

        with b3:
            if st.button("Discard All Edits", use_container_width=True):
                warehouse.discard_edits()
                st.info("Discarded user layout modifications. Restored to default.")
                st.rerun()

        with b4:
            if st.button("Save Layout to JSON", use_container_width=True):
                save_path = Path(__file__).resolve().parent / "data" / "warehouse.json"
                try:
                    warehouse.save_layout_to_file(save_path)
                    st.success("Layout successfully persisted to data/warehouse.json.")
                except Exception as save_err:
                    st.error(f"Failed to persist layout: {save_err}")

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
            st.markdown("<div style='font-size: 12px; color: #9ca3af; margin-bottom: 6px;'>Configured Products on this Shelf:</div>", unsafe_allow_html=True)
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
        else:
            st.info("No products configured on this shelf location.")
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

    # Live AI Decision Log Panel
    st.markdown("""
    <div class="panel-box">
        <div class="panel-title">
            <span>Live AI Decision Log</span>
            <span style="color: #64748b; font-size: 11px;">Authoritative Event Feed</span>
        </div>
        <div style="background: #080d1a; border-radius: 4px; padding: 4px 8px; min-height: 120px;">
            <div class="log-entry">
                <span class="log-time">00:00:00</span>
                <span class="log-cat">SYSTEM</span>
                <span class="log-msg">SmartStock AI system initialized. Authoritative WarehouseGrid active.</span>
            </div>
            <div class="log-entry">
                <span class="log-time">00:00:00</span>
                <span class="log-cat">MAP</span>
                <span class="log-msg">16x12 vector SVG grid rendered. All 30 pickup bays verified walkable.</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with side_col:
    # Order Dispatch Panel
    st.markdown("""
    <div class="panel-box">
        <div class="panel-title">Create Order</div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        active_products = [p for p in warehouse.products_by_id.values() if p.active]
        options = {f"{p.name} ({p.id})": p for p in active_products}
        
        selected_label = st.selectbox(
            "Select Product",
            options=list(options.keys()),
            help="Choose an active product from warehouse catalog"
        )
        selected_prod = options.get(selected_label)
        
        col_qty, col_stock = st.columns(2)
        with col_qty:
            qty = st.number_input("Quantity", min_value=1, max_value=10, value=1)
        with col_stock:
            available_stock = selected_prod.initial_stock if selected_prod else 0
            st.metric("In Stock", available_stock)

        btn_create = st.button("Validate & Create Order", use_container_width=True, type="primary")
        if btn_create:
            st.info("Order submission will be processed through the validation engine in Phase 6.")

    # Robot Telemetry Panel
    robot = warehouse.robot_initial
    st.markdown(f"""
    <div class="panel-box" style="margin-top: 14px;">
        <div class="panel-title">Robot Telemetry</div>
        <div class="telemetry-row">
            <span class="telemetry-label">Robot Unit</span>
            <span class="telemetry-val">{robot.id}</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Status</span>
            <span class="telemetry-val" style="color: #10b981;">{robot.state.value}</span>
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
            <span class="telemetry-label">Payload Capacity</span>
            <span class="telemetry-val">{robot.current_load_kg:.1f} / {robot.max_capacity_kg:.1f} kg</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Active Target</span>
            <span class="telemetry-val">NONE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
