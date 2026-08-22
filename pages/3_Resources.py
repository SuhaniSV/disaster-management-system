from __future__ import annotations

import streamlit as st

from components.resource_cards import hospital_shelter_panels, render_resources
from components.session import get_center, persist
from components.theme import page_setup, render_header, render_sidebar

page_setup("Resources")

center = get_center()
render_sidebar(center)
render_header(center, "Rescue units, hospitals and shelters · simulated inventory")

metrics = center.metrics()
a, b, c, d = st.columns(4)
a.metric("Available resources", metrics["available_resources"])
b.metric("Recommended assignments", metrics["assigned_resources"])
c.metric("Hospital beds free", metrics["hospital_beds_available"])
d.metric("Shelter spaces free", metrics["shelter_spaces_available"])

st.markdown("### Field resources")
render_resources(center)

st.markdown("### Capacity")
hospital_shelter_panels(center)

st.markdown("### Change operational status")
st.caption("These controls feed the same recalculation engine as the Scenario Simulator.")
ids = [r.get("id") for r in center.resources]
col1, col2, col3 = st.columns(3)
with col1:
    rid = st.selectbox("Resource", ids)
with col2:
    new_status = st.selectbox("Status", ["Available", "Unavailable"])
with col3:
    if st.button("Update resource", use_container_width=True):
        center.set_resource_status(rid, new_status)
        persist(center)
        st.success(f"{rid} set to {new_status} and plan recalculated.")
        st.rerun()

st.markdown("### Recommended pairings")
st.dataframe(
    [
        {
            "Incident": a.get("incident_id"),
            "Resource": a.get("resource_id") or "Unassigned",
            "Distance km": a.get("distance_km"),
            "Reason": a.get("reason"),
        }
        for a in center.assignments
    ],
    use_container_width=True,
    hide_index=True,
)
