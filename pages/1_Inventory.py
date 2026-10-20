"""Inventory page for SmartStock AI."""

import streamlit as st
from utils.config import load_products_config, ConfigurationError

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
    <div style="color: #9ca3af; font-size: 12px; margin-top: 4px;">Warehouse SKU catalog, shelf allocations, and real-time stock levels</div>
</div>
""", unsafe_allow_html=True)

try:
    products = load_products_config()
    st.info(f"Catalog loaded: {len(products)} products registered.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total SKUs", len(products))
    col2.metric("Active SKUs", sum(1 for p in products if p.active))
    col3.metric("Total Initial Units", sum(p.initial_stock for p in products))

    table_data = [
        {
            "SKU ID": p.id,
            "Product Name": p.name,
            "Category": p.category,
            "Shelf": p.shelf_id,
            "Unit Weight (kg)": p.unit_weight_kg,
            "Stock": p.initial_stock,
            "Status": "ACTIVE" if p.active else "INACTIVE"
        }
        for p in products
    ]
    st.dataframe(table_data, use_container_width=True)

except ConfigurationError as err:
    st.error(f"Configuration notice: {err}")
