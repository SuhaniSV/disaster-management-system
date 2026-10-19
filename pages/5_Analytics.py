from __future__ import annotations

import streamlit as st

from components.charts import (
    assignment_table,
    hospital_chart,
    incidents_by_severity,
    incidents_by_type,
    people_over_time,
    priority_distribution,
    resource_utilization,
    shelter_chart,
)
from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar

page_setup("Analytics")

center = get_center()
render_sidebar(center)
render_header(center, "Situation analytics · source-verified response records" if not center.demo_mode else "Situation analytics · simulated operational picture")

if not center.demo_mode and not center.incidents and not center.resources and not center.hospitals and not center.shelters:
    st.info("Analytics are unavailable until verified incident reports or live operational datasets are connected. This page will not calculate real-world statistics from sample data.")
    st.markdown("### Live hazard observations")
    from components.live_feed import render_live_earthquake_feed
    render_live_earthquake_feed()
    st.stop()

r1, r2 = st.columns(2)
fig = incidents_by_type(center)
if fig:
    r1.plotly_chart(fig, use_container_width=True)
fig = incidents_by_severity(center)
if fig:
    r2.plotly_chart(fig, use_container_width=True)

r3, r4 = st.columns(2)
fig = people_over_time(center)
if fig:
    r3.plotly_chart(fig, use_container_width=True)
fig = priority_distribution(center)
if fig:
    r4.plotly_chart(fig, use_container_width=True)

r5, r6 = st.columns(2)
fig = resource_utilization(center)
if fig:
    r5.plotly_chart(fig, use_container_width=True)
fig = hospital_chart(center)
if fig:
    r6.plotly_chart(fig, use_container_width=True)

fig = shelter_chart(center)
if fig:
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Response recommendations")
st.dataframe(assignment_table(center), use_container_width=True, hide_index=True)
st.caption("Charts describe current response records. In Demo Mode they are simulated; in Live Data Mode they include only operator-entered/verified records available in this session, not population-wide official statistics.")
