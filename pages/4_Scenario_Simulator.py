from __future__ import annotations

import pandas as pd
import streamlit as st

from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar

page_setup("Scenario Simulator")

center = get_center()
render_sidebar(center)
render_header(
    center,
    "Review response recommendations generated only from reported incidents and available records",
)

st.caption(
    "Recommendations use records currently loaded by ResQ-AI. Resource locations, availability, "
    "hospital capacity and road status must be verified; this page does not confirm dispatch."
)

# Never seed the simulator with CSV fixtures, fabricated incidents, or example inventory.
active_incidents = [
    incident for incident in center.incidents
    if str(incident.get("status") or "").strip().lower() != "resolved"
]

if not active_incidents:
    st.info(
        "No incidents reported yet. Submit an incident through Report Incident to see "
        "a response assessment here. No incident, distance, team, or recommendation will be invented."
    )
    st.stop()

st.markdown("### Reported incidents")
incident_labels = {
    str(item.get("id")): (
        f'{item.get("id")} · {item.get("disaster_type") or "Incident"} · '
        f'{item.get("people_affected") or 0} people affected'
    )
    for item in active_incidents
    if item.get("id")
}
incident_ids = list(incident_labels)
if not incident_ids:
    st.info("Reported incidents do not have usable incident IDs, so recommendations cannot be displayed.")
    st.stop()

selected_id = st.selectbox(
    "Choose a reported incident",
    incident_ids,
    format_func=lambda value: incident_labels[value],
)
incident = next((item for item in active_incidents if str(item.get("id")) == selected_id), {})
assignment = center.assignment_for(selected_id)

left, right = st.columns(2)
with left:
    st.metric("Priority", incident.get("priority_score", "Not calculated"))
    st.metric("People affected", incident.get("people_affected") or 0)
with right:
    st.metric("Incident type", incident.get("disaster_type") or "Not classified")
    st.metric("Status", incident.get("status") or "Active")

st.markdown("### Response recommendation")
if not assignment:
    st.warning("No allocation recommendation is available for this reported incident yet.")
else:
    resource_id = assignment.get("resource_id")
    resource_name = assignment.get("resource_name")
    distance = assignment.get("distance_km")
    if resource_id and resource_name and isinstance(distance, (int, float)):
        st.success(f"Suggested resource: {resource_name} ({resource_id}) · {distance:.2f} km")
    else:
        st.warning(
            assignment.get("reason")
            or "No suitable verified resource can currently be recommended. Check the available resource records."
        )

    if assignment.get("hospital_name") or assignment.get("hospital_id"):
        st.write(
            "**Hospital recommendation:** "
            + str(assignment.get("hospital_name") or assignment.get("hospital_id"))
            + (
                f' · {assignment.get("hospital_km"):.2f} km'
                if isinstance(assignment.get("hospital_km"), (int, float))
                else ""
            )
        )
    elif incident.get("medical_emergency"):
        st.info("Medical assistance is indicated, but no verified hospital recommendation is available in the loaded records.")

    if assignment.get("shelter_name") or assignment.get("shelter_id"):
        st.write(
            "**Shelter recommendation:** "
            + str(assignment.get("shelter_name") or assignment.get("shelter_id"))
            + (
                f' · {assignment.get("shelter_km"):.2f} km'
                if isinstance(assignment.get("shelter_km"), (int, float))
                else ""
            )
        )

st.markdown("### Available operational records")
st.caption("Only records actually loaded into the operational session are shown. Empty inventory is not replaced with sample teams.")
counts = {
    "Reported incidents": len(active_incidents),
    "Resource records": len(center.resources),
    "Hospital records": len(center.hospitals),
    "Shelter records": len(center.shelters),
    "Road records": len(center.roads),
}
cols = st.columns(len(counts))
for col, (label, count) in zip(cols, counts.items()):
    col.metric(label, count)

if not center.resources:
    st.warning(
        "No resource inventory is connected to the operational session. ResQ-AI will not invent "
        "a rescue team or distance. Connect verified resource records with coordinates, capabilities, "
        "capacity and current availability to enable real resource recommendations."
    )
if incident.get("medical_emergency") and not center.hospitals:
    st.warning(
        "This incident indicates a medical need, but no hospital inventory is connected. "
        "No hospital will be fabricated."
    )

if center.resources:
    resource_rows = []
    for resource in center.resources:
        resource_rows.append({
            "Resource": resource.get("name") or resource.get("id") or "Unnamed",
            "Type": resource.get("type") or "Unknown",
            "Status": resource.get("status") or "Unknown",
            "Latitude": resource.get("lat"),
            "Longitude": resource.get("lon"),
        })
    st.dataframe(pd.DataFrame(resource_rows), use_container_width=True, hide_index=True)
