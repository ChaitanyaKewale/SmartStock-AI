"""AI Laboratory page for SmartStock AI."""

import streamlit as st

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
    .algo-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .algo-title {
        font-weight: 600;
        font-size: 14px;
        color: #10b981;
        margin-bottom: 4px;
    }
    .algo-desc {
        font-size: 12px;
        color: #9ca3af;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h3 style="margin: 0; color: #f3f4f6; font-size: 18px; font-weight: 600;">AI LABORATORY</h3>
    <div style="color: #9ca3af; font-size: 12px; margin-top: 4px;">Interactive testbeds and algorithm inspectors for the six syllabus concepts</div>
</div>
""", unsafe_allow_html=True)

st.info("Interactive algorithm inspectors will be activated in Phase 4 and Phase 8.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="algo-card">
        <div class="algo-title">1. LOGICAL UNIFICATION</div>
        <div class="algo-desc">Predicate unification with variable substitutions for catalog item and location resolution.</div>
    </div>
    <div class="algo-card">
        <div class="algo-title">2. PROPOSITIONAL LOGIC</div>
        <div class="algo-desc">Rule verification for order acceptance, pickup permissions, and delivery conditions.</div>
    </div>
    <div class="algo-card">
        <div class="algo-title">3. MIN-CONFLICTS LOCAL SEARCH</div>
        <div class="algo-desc">CSP-based warehouse shelf allocation and category constraint solver.</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="algo-card">
        <div class="algo-title">4. GREEDY BEST-FIRST SEARCH</div>
        <div class="algo-desc">Manhattan heuristic pathfinder for cell-by-cell navigation through walkable aisles.</div>
    </div>
    <div class="algo-card">
        <div class="algo-title">5. FORWARD STATE-SPACE SEARCH</div>
        <div class="algo-desc">High-level mission planning defining sequential pickup and distribution actions.</div>
    </div>
    <div class="algo-card">
        <div class="algo-title">6. SIMPLE REFLEX AGENT</div>
        <div class="algo-desc">Percept-driven condition-action rules for live obstacle handling and safety triggers.</div>
    </div>
    """, unsafe_allow_html=True)
