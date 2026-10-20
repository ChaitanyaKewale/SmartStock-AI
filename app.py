"""SmartStock AI - Warehouse Operations Dashboard

Phase 1 Application Skeleton and Layout Foundation.
Implements the dark industrial control-room visual design system,
compact KPI row, map viewport, order creation panel, robot telemetry,
order lifecycle progress bar, and live AI decision log.
"""

from __future__ import annotations

import streamlit as st
from datetime import datetime
from utils.config import (
    load_warehouse_config,
    load_products_config,
    ConfigurationError,
    WarehouseConfig,
    ProductConfig
)

# 1. Page Configuration
st.set_page_config(
    page_title="SmartStock AI | Warehouse Operations",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Industrial Control-Room Design System CSS
st.markdown("""
<style>
    /* Dark industrial palette */
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

    /* Overall background */
    .stApp {
        background-color: var(--bg-main);
        color: var(--text-primary);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Top Header Bar */
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
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .brand-sub {
        font-size: 12px;
        color: var(--text-muted);
        font-weight: 400;
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

    /* KPI Metrics Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 14px;
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

    /* Panel Card */
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

    /* Map Placeholder Viewport */
    .map-placeholder {
        background: #080d1a;
        border: 1px dashed var(--border-panel);
        border-radius: 6px;
        min-height: 440px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--text-muted);
        text-align: center;
        padding: 24px;
    }

    .map-meta {
        font-size: 12px;
        color: #64748b;
        margin-top: 8px;
    }

    /* Telemetry row */
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

    /* Lifecycle Steps */
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

    /* Event Log Table */
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

# 3. Load Configurations with Clean Error Catching
config_error: str | None = None
warehouse_cfg: WarehouseConfig | None = None
products_cfg: list[ProductConfig] = []

try:
    warehouse_cfg = load_warehouse_config()
    products_cfg = load_products_config()
except ConfigurationError as exc:
    config_error = str(exc)

# 4. Header Section
status_text = "SYSTEM ONLINE" if config_error is None else "CONFIG ERROR"
status_class = "status-badge" if config_error is None else "status-badge"

st.markdown(f"""
<div class="header-bar">
    <div>
        <span class="brand-title">SMARTSTOCK AI</span>
        <span class="brand-sub"> / Warehouse Operations & Fulfillment</span>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 12px; color: #9ca3af;">Layout: {warehouse_cfg.grid.width if warehouse_cfg else 16}×{warehouse_cfg.grid.height if warehouse_cfg else 12}</span>
        <span class="{status_class}">{status_text}</span>
    </div>
</div>
""", unsafe_allow_html=True)

if config_error:
    st.error(f"Configuration Initialization Alert: {config_error}")
    st.stop()

# 5. Compact KPI Row (Actual Data - No Fake Metrics)
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
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Completed Orders</div>
        <div class="kpi-value">0</div>
    </div>
    """, unsafe_allow_html=True)

with col_k4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Robot Status</div>
        <div class="kpi-value" style="color: #10b981; font-size: 16px; line-height: 28px;">IDLE / STATION</div>
    </div>
    """, unsafe_allow_html=True)

# 6. Main Dashboard Layout (68% Map/Progress, 32% Side Controls/Telemetry)
main_col, side_col = st.columns([0.68, 0.32], gap="small")

with main_col:
    # Warehouse Map Area
    st.markdown(f"""
    <div class="panel-box">
        <div class="panel-title">
            <span>Live Warehouse Map (16 × 12 Grid)</span>
            <span style="color: #64748b; font-size: 11px;">Authoritative SVG Component</span>
        </div>
        <div class="map-placeholder">
            <div style="font-weight: 600; font-size: 14px; color: #e2e8f0; margin-bottom: 6px;">
                WAREHOUSE GRID INITIALIZED
            </div>
            <div style="font-size: 12px; color: #94a3b8; max-width: 440px;">
                Racks: {len(warehouse_cfg.racks)} | Obstacles: {len(warehouse_cfg.fixed_obstacles)} | 
                Station: ({warehouse_cfg.distribution_station.x}, {warehouse_cfg.distribution_station.y}) |
                Robot Start: ({warehouse_cfg.robot_initial.x}, {warehouse_cfg.robot_initial.y})
            </div>
            <div class="map-meta">
                Interactive SVG rendering engine will connect in Phase 2
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
        <div style="background: #080d1a; border-radius: 4px; padding: 4px 8px; min-height: 140px;">
            <div class="log-entry">
                <span class="log-time">00:00:00</span>
                <span class="log-cat">SYSTEM</span>
                <span class="log-msg">SmartStock AI system initialized. Configuration loaded successfully.</span>
            </div>
            <div class="log-entry">
                <span class="log-time">00:00:00</span>
                <span class="log-cat">ROBOT</span>
                <span class="log-msg">ROBOT-ALPHA placed at initial position (0, 1), status IDLE.</span>
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
        active_products = [p for p in products_cfg if p.active]
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
    robot = warehouse_cfg.robot_initial
    st.markdown(f"""
    <div class="panel-box" style="margin-top: 14px;">
        <div class="panel-title">Robot Telemetry</div>
        <div class="telemetry-row">
            <span class="telemetry-label">Robot Unit</span>
            <span class="telemetry-val">{robot.id}</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Status</span>
            <span class="telemetry-val" style="color: #10b981;">IDLE</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Position</span>
            <span class="telemetry-val">({robot.x}, {robot.y})</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Orientation</span>
            <span class="telemetry-val">{robot.facing}</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Payload Capacity</span>
            <span class="telemetry-val">0.0 / {robot.max_capacity_kg} kg</span>
        </div>
        <div class="telemetry-row">
            <span class="telemetry-label">Active Target</span>
            <span class="telemetry-val">NONE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
