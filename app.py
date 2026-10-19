from components.theme import page_setup

page_setup("Live Disaster Intelligence")

import streamlit as st

from components.live_disaster_intelligence import render_live_disaster_intelligence

st.sidebar.markdown("### RESQ-AI")
st.sidebar.caption("Live Disaster Intelligence")
st.sidebar.divider()

render_live_disaster_intelligence()
