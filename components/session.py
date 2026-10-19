"""Shared Streamlit session helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from core.llm_client import llm_configured
from core.state import CommandCenter, load_demo_disaster


def load_live_center() -> CommandCenter:
    """Start without sample records; only live feeds and operator reports populate live mode."""
    center = CommandCenter(bundle={"incidents": [], "resources": [], "hospitals": [], "shelters": [], "roads": [], "events": []})
    center.demo_mode = False
    center.data_mode = "Live Data"
    center.events = []
    return center


def get_center() -> CommandCenter:
    mode = st.session_state.get("resq_data_mode", "Live Data")
    st.session_state["resq_data_mode"] = mode
    center = st.session_state.get("center")
    if center is None or getattr(center, "data_mode", "Demo Mode") != mode:
        st.session_state.center = load_demo_disaster() if mode == "Demo Mode" else load_live_center()
        if llm_configured():
            st.session_state.center.ai_mode = "AI Mode: Active"
    center: CommandCenter = st.session_state.center
    if llm_configured() and center.ai_mode.startswith("Fallback"):
        center.ai_mode = "AI Mode: Active"
    elif not llm_configured() and str(center.ai_mode).startswith("AI Mode"):
        center.ai_mode = "Fallback Analysis Mode"
    return center


def persist(center: CommandCenter) -> None:
    st.session_state.center = center
