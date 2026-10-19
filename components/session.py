"""Shared Streamlit session helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from core.llm_client import llm_configured
from core.state import CommandCenter


def get_center() -> CommandCenter:
    if "center" not in st.session_state:
        st.session_state.center = CommandCenter(bundle={"incidents": [], "resources": [], "hospitals": [], "shelters": [], "roads": [], "events": []})
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
