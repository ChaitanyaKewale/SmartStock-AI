"""Inventory page for SmartStock AI.

Connected to SQLite persistence: displays real on-hand, reserved, and available stock.
"""

from __future__ import annotations

import streamlit as st
from database.db import get_db_connection, init_db, seed_catalog_if_empty
from database.repositories import InventoryRepository

st.set_page_config(page_title="Inventory | SmartStock AI", layout="wide", page_icon="📦")

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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h3 style="margin: 0; color: #f3f4f6; font-size: 18px; font-weight: 600;">INVENTORY MANAGEMENT</h3>
    <div style="color: #9ca3af; font-size: 12px; margin-top: 4px;">Live SQLite Inventory: On-Hand, Reserved, and Available Stock Levels</div>
</div>
""", unsafe_allow_html=True)

try:
    conn = get_db_connection()
    init_db(conn)
    seed_catalog_if_empty(conn)
    inv_repo = InventoryRepository(conn)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.name, p.category, p.unit_weight_kg, p.shelf_id, p.active,
               i.on_hand, i.reserved, (i.on_hand - i.reserved) as available
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        ORDER BY p.id;
    """)
    records = cursor.fetchall()

    total_skus = len(records)
    total_on_hand = sum(r["on_hand"] for r in records)
    total_reserved = sum(r["reserved"] for r in records)
    total_available = sum(r["available"] for r in records)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registered SKUs", total_skus)
    col2.metric("Total On-Hand", total_on_hand)
    col3.metric("Total Reserved", total_reserved)
    col4.metric("Total Available", total_available)

    table_data = [
        {
            "SKU ID": r["id"],
            "Product Name": r["name"],
            "Category": r["category"],
            "Shelf": r["shelf_id"],
            "Weight (kg)": r["unit_weight_kg"],
            "On-Hand": r["on_hand"],
            "Reserved": r["reserved"],
            "Available": r["available"],
            "Status": "ACTIVE" if r["active"] else "INACTIVE"
        }
        for r in records
    ]
    st.dataframe(table_data, use_container_width=True)

except Exception as err:
    st.error(f"Inventory database notice: {err}")
