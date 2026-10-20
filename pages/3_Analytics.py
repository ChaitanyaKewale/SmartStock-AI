"""Operational Analytics page for SmartStock AI."""

import streamlit as st

st.set_page_config(page_title="Analytics | SmartStock AI", layout="wide", page_icon="📊")

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
    <h3 style="margin: 0; color: #f3f4f6; font-size: 18px; font-weight: 600;">OPERATIONAL ANALYTICS</h3>
    <div style="color: #9ca3af; font-size: 12px; margin-top: 4px;">Warehouse throughput, path efficiency, and algorithm performance telemetry</div>
</div>
""", unsafe_allow_html=True)

st.info("No orders completed yet. Operational analytics will be populated from durable SQLite records once orders are fulfilled.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Orders Completed", "0")
c2.metric("Items Picked", "0")
c3.metric("Avg Movement Steps", "0")
c4.metric("Replans Triggered", "0")
