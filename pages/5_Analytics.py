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
render_header(center, "Analytics for operator-submitted incidents and currently available operational records")

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
st.caption("These charts summarize records entered into this session. They are not live government statistics.")
