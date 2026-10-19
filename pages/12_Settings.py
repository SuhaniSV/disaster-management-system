from __future__ import annotations

import streamlit as st

from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar

page_setup("Settings")

center = get_center()
render_sidebar(center)
render_header(center, "Personalize your command-center experience")

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
st.caption("ResQ-AI is a decision-support prototype. Its demo data may be simulated; route estimates and AI summaries are advisory and must not replace official emergency instructions.")
