from __future__ import annotations

import streamlit as st

from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar

page_setup("Settings")

center = get_center()
render_sidebar(center)
render_header(center, "Personalize your command-center experience")

st.markdown("### Other settings")
st.info("Government feeds, AI providers, routing, and notification integrations are configured through environment variables or Streamlit secrets. Do not enter API keys into chat or commit them to the repository.")
st.markdown("### Safety and data")
st.caption("ResQ-AI is a decision-support prototype. Its demo data may be simulated; route estimates and AI summaries are advisory and must not replace official emergency instructions.")
