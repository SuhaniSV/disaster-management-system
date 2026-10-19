from __future__ import annotations

import streamlit as st

from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar

page_setup("Settings")

center = get_center()
render_sidebar(center)
render_header(center, "Personalize your command-center experience")

st.markdown("## Data source mode")
st.caption("Live Data is the default. Demo Mode is an explicit opt-in for testing and presentations.")
current_mode = st.session_state.get("resq_data_mode", "Live Data")
selected_mode = st.radio("Operational data", ["Live Data", "Demo Mode"], index=0 if current_mode == "Live Data" else 1, horizontal=True, key="resq_settings_data_mode")
if selected_mode != current_mode:
    st.session_state["resq_data_mode"] = selected_mode
    st.session_state["resq_data_mode_selector"] = selected_mode
    st.session_state.pop("center", None)
    st.session_state.pop("sim_before", None)
    st.session_state.pop("sim_after", None)
    st.session_state.pop("sim_label", None)
    st.rerun()
if selected_mode == "Live Data":
    st.info("Live Data Mode hides simulated incidents and inventories. USGS earthquake observations are public and live; IMD and NDMA feeds require valid official access configuration. Live operational inventories require additional authorized integrations.")
else:
    st.warning("Demo Mode loads simulated Pune-area records. Do not use these records for emergency response.")

st.markdown("## Appearance")
st.caption("Choose the visual theme for ResQ-AI. Your selection is kept for this browser session and applies across the app's pages.")

current_theme = st.session_state.get("resq_theme", "Light")
selected_theme = st.radio(
    "Color theme",
    options=["Light", "Dark"],
    index=0 if current_theme == "Light" else 1,
    horizontal=True,
    key="resq_theme_settings_choice",
    help="Light is optimized for bright environments; Dark is designed for low-light command-center use.",
)

if selected_theme != current_theme:
    st.session_state["resq_theme"] = selected_theme
    st.rerun()

if selected_theme == "Dark":
    st.success("Dark theme is selected.")
else:
    st.success("Light theme is selected.")

st.markdown("### Other settings")
st.info("Government feeds, AI providers, routing, and notification integrations are configured through environment variables or Streamlit secrets. Do not enter API keys into chat or commit them to the repository.")
st.markdown("### Safety and data")
st.caption("ResQ-AI is a decision-support prototype. Verify source, timestamp, location and status with emergency authorities. Live feeds may be incomplete or unavailable; this app does not dispatch responders autonomously.")
