"""SmartStock AI - Inventory Management Page.

Live SQLite Inventory Tracking:
- Search and filter products by SKU, name, category, and stock health.
- Detailed metrics: on-hand, reserved, available, assigned shelf, and shelf capacity.
- Configured low-stock threshold alerts (< 5 units).
- Safe manual stock adjustment / restock form maintaining invariants (0 <= reserved <= on_hand).
"""

from __future__ import annotations

import streamlit as st
from database.db import get_db_connection, init_db, seed_catalog_if_empty
from database.repositories import InventoryRepository
from simulation.warehouse import get_default_warehouse

st.set_page_config(page_title="Inventory | SmartStock AI", layout="wide", page_icon="📦")

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
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h3 style="margin: 0; color: #f3f4f6; font-size: 18px; font-weight: 600;">INVENTORY OPERATIONS & CATALOG</h3>
    <div style="color: #9ca3af; font-size: 12px; margin-top: 4px;">
        Authoritative SQLite Inventory Balances, Storage Allocation, and Safe Stock Adjustments
    </div>
</div>
""", unsafe_allow_html=True)

try:
    conn = get_db_connection()
    init_db(conn)
    seed_catalog_if_empty(conn)
    inv_repo = InventoryRepository(conn)
    warehouse = get_default_warehouse()

    # Query all active product records joined with inventory
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.name, p.category, p.unit_weight_kg, p.shelf_id, p.active,
               i.on_hand, i.reserved, (i.on_hand - i.reserved) as available
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        ORDER BY p.id;
    """)
    records = cursor.fetchall()

    # 1. High-level Inventory KPI Metrics
    total_skus = len(records)
    total_on_hand = sum(r["on_hand"] for r in records)
    total_reserved = sum(r["reserved"] for r in records)
    total_available = sum(r["available"] for r in records)
    low_stock_records = [r for r in records if r["available"] < 5]

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Registered SKUs", total_skus)
    k2.metric("Total On-Hand", f"{total_on_hand} units")
    k3.metric("Total Reserved", f"{total_reserved} units")
    k4.metric("Total Available", f"{total_available} units")
    k5.metric(
        "Low Stock Alerts",
        f"{len(low_stock_records)} SKUs",
        delta=f"-{len(low_stock_records)}" if low_stock_records else "Normal",
        delta_color="inverse"
    )

    # Low Stock Warning Banner
    if low_stock_records:
        low_skus_str = ", ".join(f"{r['name']} ({r['id']}: {r['available']} avail)" for r in low_stock_records)
        st.warning(f"⚠️ **Low Stock Alert (< 5 units available):** {low_skus_str}")

    # 2. Search & Category Filters
    st.markdown("""
    <div class="panel-box">
        <div class="panel-title">Search & Filter Catalog</div>
    </div>
    """, unsafe_allow_html=True)

    col_s1, col_s2, col_s3 = st.columns([0.45, 0.30, 0.25])
    with col_s1:
        search_query = st.text_input("🔍 Search by SKU or Name", value="", placeholder="e.g. Laptop, PROD-001")
    with col_s2:
        categories = ["ALL"] + sorted(list({r["category"] for r in records}))
        selected_category = st.selectbox("Category", options=categories, index=0)
    with col_s3:
        stock_filter = st.selectbox(
            "Stock Health Filter",
            options=["ALL", "Low Stock (< 5)", "Out of Stock (= 0)", "Adequate (>= 5)"],
            index=0
        )

    # Apply filters
    filtered_records = []
    for r in records:
        # Search query match
        q = search_query.strip().lower()
        if q and q not in r["id"].lower() and q not in r["name"].lower():
            continue
        # Category match
        if selected_category != "ALL" and r["category"] != selected_category:
            continue
        # Stock health match
        if stock_filter == "Low Stock (< 5)" and r["available"] >= 5:
            continue
        elif stock_filter == "Out of Stock (= 0)" and r["available"] > 0:
            continue
        elif stock_filter == "Adequate (>= 5)" and r["available"] < 5:
            continue

        filtered_records.append(r)

    # 3. Inventory Data Table
    table_rows = []
    for r in filtered_records:
        shelf = warehouse.racks_by_id.get(r["shelf_id"])
        cap_str = f"{shelf.max_capacity} units" if shelf else "N/A"
        health_badge = "🟢 HEALTHY" if r["available"] >= 5 else ("🔴 OUT" if r["available"] == 0 else "⚠️ LOW")

        table_rows.append({
            "SKU ID": r["id"],
            "Product Name": r["name"],
            "Category": r["category"],
            "Shelf Location": r["shelf_id"],
            "Shelf Cap": cap_str,
            "Unit Wt (kg)": r["unit_weight_kg"],
            "On-Hand": r["on_hand"],
            "Reserved": r["reserved"],
            "Available": r["available"],
            "Health": health_badge,
            "Status": "ACTIVE" if r["active"] else "INACTIVE"
        })

    st.caption(f"Displaying {len(table_rows)} of {len(records)} catalog records")
    st.dataframe(table_rows, use_container_width=True, height=280)

    # 4. Stock Adjustment & Restock Control Form
    st.markdown("""
    <div class="panel-box" style="margin-top: 14px;">
        <div class="panel-title">Safe Stock Adjustment & Restock Console</div>
    </div>
    """, unsafe_allow_html=True)

    c_prod, c_qty, c_reason, c_btn = st.columns([0.35, 0.20, 0.30, 0.15])
    prod_options = {f"{r['name']} ({r['id']}) - Avail: {r['available']}": r for r in records}

    with c_prod:
        sel_label = st.selectbox("Select Product", options=list(prod_options.keys()))
        selected_prod = prod_options[sel_label]
    with c_qty:
        new_on_hand_val = st.number_input(
            "New On-Hand Total",
            min_value=0,
            max_value=500,
            value=int(selected_prod["on_hand"]),
            help="Must be greater than or equal to current active reserved quantity"
        )
    with c_reason:
        adj_reason = st.selectbox("Adjustment Reason", ["WAREHOUSE_RESTOCK", "CYCLE_COUNT_RECONCILIATION", "DAMAGED_DISPOSAL"])
    with c_btn:
        st.write("")
        st.write("")
        if st.button("Apply Adjustment", use_container_width=True, type="primary"):
            try:
                inv_repo.adjust_stock(
                    product_id=selected_prod["id"],
                    new_on_hand=new_on_hand_val,
                    reason=adj_reason
                )
                st.success(f"Stock for {selected_prod['id']} updated to {new_on_hand_val} on-hand.")
                st.rerun()
            except ValueError as val_err:
                st.error(str(val_err))
            except Exception as ex:
                st.error(f"Adjustment failed: {ex}")

except Exception as err:
    st.error(f"Inventory database notice: {err}")
