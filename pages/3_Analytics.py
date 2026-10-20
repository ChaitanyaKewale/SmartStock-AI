"""SmartStock AI - Operational Analytics Page.

Visualizes genuine operational data persisted in SQLite and SimulationEngine events:
- Completed, active, blocked, and failed orders
- Total products and cargo weight delivered
- Average movement steps per completed order
- Reflex Agent obstacle detection and GBFS replanning events
- Interactive Plotly operational charts (Order Status, SKU Throughput, Event Breakdown)
- Storage optimization conflict reduction comparison
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from database.db import get_db_connection, init_db, seed_catalog_if_empty
from simulation.engine import SimulationEngine

st.set_page_config(page_title="Analytics | SmartStock AI", layout="wide", page_icon="📊")

st.markdown("""
<style>
    .reportview-container, .main {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .header-box {
        padding: 14px 20px;
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        margin-bottom: 16px;
    }
    .panel-box {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .panel-title {
        font-size: 13px;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        border-bottom: 1px solid #1f2937;
        padding-bottom: 8px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h3 style="margin: 0; color: #f3f4f6; font-size: 18px; font-weight: 600;">OPERATIONAL ANALYTICS & TELEMETRY</h3>
    <div style="color: #9ca3af; font-size: 12px; margin-top: 4px;">
        Warehouse Throughput, Navigation Efficiency, and Autonomous Algorithm Performance Metrics
    </div>
</div>
""", unsafe_allow_html=True)

try:
    conn = get_db_connection()
    init_db(conn)
    seed_catalog_if_empty(conn)
    cursor = conn.cursor()

    # Query Order Statistics from SQLite
    cursor.execute("SELECT id, status, created_at, completed_at, notes FROM orders ORDER BY created_at DESC;")
    all_orders = cursor.fetchall()

    # Query Delivery Confirmations
    cursor.execute("""
        SELECT d.order_id, d.delivered_at, d.total_items, d.total_weight_kg, d.notes
        FROM deliveries d
        ORDER BY d.delivered_at DESC;
    """)
    all_deliveries = cursor.fetchall()

    # Query Delivered Products Breakdown
    cursor.execute("""
        SELECT ol.product_id, p.name, sum(ol.picked_quantity) as total_units,
               sum(ol.picked_quantity * ol.unit_weight_kg) as total_weight
        FROM order_lines ol
        JOIN orders o ON ol.order_id = o.id
        JOIN products p ON ol.product_id = p.id
        WHERE o.status = 'DELIVERED'
        GROUP BY ol.product_id, p.name
        ORDER BY total_units DESC;
    """)
    delivered_products = cursor.fetchall()

    # Access in-memory SimulationEngine events if available
    engine: SimulationEngine = st.session_state.get("engine")
    engine_events = engine.events.events if engine else []

    # Calculate Core Analytics Metrics
    completed_orders = [o for o in all_orders if o["status"] == "DELIVERED"]
    active_orders = [o for o in all_orders if o["status"] in ("READY", "IN_PROGRESS", "PLANNING", "VALIDATED")]
    blocked_failed_orders = [o for o in all_orders if o["status"] in ("BLOCKED", "FAILED", "CANCELLED", "RECOVERY_REQUIRED")]

    total_units_delivered = sum(d["total_items"] for d in all_deliveries)
    total_weight_delivered = sum(d["total_weight_kg"] for d in all_deliveries)

    # Replans and obstacle encounters from events
    replan_count = len([e for e in engine_events if e.action in ("REPLAN", "OBSTACLE_DETECTED") or "replan" in e.explanation.lower()])
    total_steps = engine.robot.distance_travelled if engine else 0
    avg_steps_per_order = (total_steps / len(completed_orders)) if completed_orders else 0.0

    # Top KPI Metrics Row
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Orders Delivered", len(completed_orders), help="Total orders confirmed delivered at Station DS-01")
    k2.metric("Active / Blocked", f"{len(active_orders)} / {len(blocked_failed_orders)}", help="Active missions vs halted/blocked orders")
    k3.metric("Throughput Delivered", f"{total_units_delivered} units", f"{total_weight_delivered:.1f} kg")
    k4.metric("Avg Steps / Order", f"{avg_steps_per_order:.1f} cells", f"Replans: {replan_count}")

    if not all_orders:
        st.info("ℹ️ No order operations recorded yet. Analytics will populate automatically as customer orders are validated and fulfilled.")
    else:
        # Plotly Operational Charts
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title">Throughput & Fulfillment Distribution</div>
        </div>
        """, unsafe_allow_html=True)

        chart_c1, chart_c2 = st.columns(2)

        # 1. Order Status Distribution Donut Chart
        with chart_c1:
            status_counts = {}
            for o in all_orders:
                st_val = o["status"]
                status_counts[st_val] = status_counts.get(st_val, 0) + 1

            labels = list(status_counts.keys())
            values = list(status_counts.values())

            color_map = {
                "DELIVERED": "#10b981",
                "VALIDATED": "#38bdf8",
                "READY": "#60a5fa",
                "IN_PROGRESS": "#a78bfa",
                "BLOCKED": "#ef4444",
                "CANCELLED": "#f59e0b",
                "RECOVERY_REQUIRED": "#dc2626"
            }
            colors = [color_map.get(lbl, "#94a3b8") for lbl in labels]

            fig_status = go.Figure(data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.55,
                    marker=dict(colors=colors, line=dict(color="#0b0f19", width=2)),
                    textinfo="label+value"
                )
            ])
            fig_status.update_layout(
                title="Order Status Breakdown",
                title_font=dict(color="#f3f4f6", size=13),
                paper_bgcolor="#111827",
                plot_bgcolor="#111827",
                font=dict(color="#9ca3af"),
                margin=dict(l=20, r=20, t=40, b=20),
                height=260,
                showlegend=False
            )
            st.plotly_chart(fig_status, use_container_width=True)

        # 2. Delivered Products Breakdown Chart
        with chart_c2:
            if delivered_products:
                prod_names = [f"{r['name']} ({r['product_id']})" for r in delivered_products]
                prod_units = [r["total_units"] for r in delivered_products]

                fig_prod = go.Figure(data=[
                    go.Bar(
                        x=prod_units,
                        y=prod_names,
                        orientation="h",
                        marker=dict(color="#38bdf8", line=dict(color="#0284c7", width=1))
                    )
                ])
                fig_prod.update_layout(
                    title="Products Delivered (Units by SKU)",
                    title_font=dict(color="#f3f4f6", size=13),
                    paper_bgcolor="#111827",
                    plot_bgcolor="#111827",
                    font=dict(color="#9ca3af"),
                    xaxis=dict(gridcolor="#1f2937", title="Units Delivered"),
                    yaxis=dict(autorange="reversed"),
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=260
                )
                st.plotly_chart(fig_prod, use_container_width=True)
            else:
                st.markdown("""
                <div style="background:#080d1a; border:1px solid #1a2234; border-radius:4px; padding:40px; text-align:center; color:#64748b; font-size:12px; height:260px; display:flex; align-items:center; justify-content:center;">
                    No delivered cargo items yet. Complete an order to populate product throughput charts.
                </div>
                """, unsafe_allow_html=True)

        # 3. Decision Event Activity Breakdown
        if engine_events:
            st.markdown("""
            <div class="panel-box">
                <div class="panel-title">AI Algorithm Activity Telemetry (Event Breakdown)</div>
            </div>
            """, unsafe_allow_html=True)

            cat_counts = {}
            for ev in engine_events:
                cat_counts[ev.category] = cat_counts.get(ev.category, 0) + 1

            cat_labels = list(cat_counts.keys())
            cat_values = list(cat_counts.values())

            fig_events = go.Figure(data=[
                go.Bar(
                    x=cat_labels,
                    y=cat_values,
                    marker=dict(color=["#38bdf8", "#10b981", "#a78bfa", "#fbbf24", "#ec4899", "#60a5fa", "#ef4444"][:len(cat_labels)])
                )
            ])
            fig_events.update_layout(
                title=f"Recorded Simulation Events by Category (Total: {len(engine_events)})",
                title_font=dict(color="#f3f4f6", size=13),
                paper_bgcolor="#111827",
                plot_bgcolor="#111827",
                font=dict(color="#9ca3af"),
                yaxis=dict(gridcolor="#1f2937", title="Event Count"),
                xaxis=dict(gridcolor="#1f2937"),
                margin=dict(l=20, r=20, t=40, b=20),
                height=220
            )
            st.plotly_chart(fig_events, use_container_width=True)

        # 4. Completed Order Audit Table
        st.markdown("""
        <div class="panel-box">
            <div class="panel-title">Delivered Orders Audit History</div>
        </div>
        """, unsafe_allow_html=True)

        if all_deliveries:
            deliv_rows = [
                {
                    "Order ID": d["order_id"],
                    "Delivered Timestamp": d["delivered_at"],
                    "Items Delivered": d["total_items"],
                    "Total Weight (kg)": d["total_weight_kg"],
                    "Notes": d["notes"] or "Confirmed Unload at DS-01"
                }
                for d in all_deliveries
            ]
            st.dataframe(deliv_rows, use_container_width=True, height=160)
        else:
            st.caption("No deliveries confirmed yet.")

except Exception as err:
    st.error(f"Analytics query notice: {err}")
