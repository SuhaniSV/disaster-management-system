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
    "Assess reported emergencies and review resource readiness using records actually available to ResQ-AI",
)

st.caption(
    "This page uses operator-submitted incidents only. It does not create sample incidents or treat "
    "unverified assets as real. An assessment is not a dispatch confirmation."
)

# Make the persistence state visible so operators know whether reports survive a new session.
if st.session_state.get("incident_store_error"):
    st.error(str(st.session_state["incident_store_error"]))
elif st.session_state.get("incident_store_configured"):
    st.success("Incident database: configured for permanent storage.")
else:
    st.warning("Incident database: not connected. Reports may exist only in this browser session.")

active_incidents = [
    incident for incident in center.incidents
    if str(incident.get("status") or "").strip().lower() != "resolved"
]

if not active_incidents:
    st.info(
        "No incidents reported yet. Submit an incident through Report Incident to generate an assessment. "
        "No incident, distance, rescue team, hospital, or recommendation will be invented."
    )
    st.stop()

incident_labels = {
    str(item.get("id")): (
        f'{item.get("id")} · {item.get("disaster_type") or "Unclassified"} · '
        f'{item.get("people_affected") or 0:,} people affected'
    )
    for item in active_incidents
    if item.get("id")
}
incident_ids = list(incident_labels)
if not incident_ids:
    st.warning("Incident records were loaded, but none has a usable ID. Please review the saved report.")
    st.stop()

st.markdown("### Reported incident")
selected_id = st.selectbox(
    "Choose a reported incident",
    incident_ids,
    format_func=lambda value: incident_labels[value],
)
incident = next((item for item in active_incidents if str(item.get("id")) == selected_id), {})

raw_type = str(incident.get("disaster_type") or "").strip()
is_unclassified = not raw_type or raw_type.lower() in {"unknown", "unclassified", "none", "null"}
incident_type = "Unclassified — review the report details" if is_unclassified else raw_type
people = incident.get("people_affected")
try:
    people_label = f"{int(people):,}" if people is not None and str(people).strip() else "Not provided"
except (TypeError, ValueError):
    people_label = str(people or "Not provided")
lat, lon = incident.get("lat"), incident.get("lon")
location = (
    f"{lat}, {lon}"
    if lat is not None and lon is not None
    else "Location coordinates not available"
)

a, b, c, d = st.columns(4)
score = incident.get("priority_score")
a.metric("Priority score", f"{score}/100" if score is not None else "Not calculated")
b.metric("People affected", people_label)
c.metric("Incident type", incident_type)
d.metric("Status", str(incident.get("status") or "Active"))

st.markdown("**Reported description**")
description = str(incident.get("description") or incident.get("summary") or "").strip()
if description:
    st.write(description)
else:
    st.warning("This saved incident has no description. Review the original report; the hazard type cannot be verified from this record.")

detail_left, detail_right = st.columns(2)
with detail_left:
    st.markdown("**Reported location**")
    st.write(location)
with detail_right:
    st.markdown("**Reported at**")
    st.write(str(incident.get("reported_at") or "Timestamp not available"))

if is_unclassified:
    st.warning(
        "The saved report is not classified as a known hazard. ResQ-AI will not guess the incident type. "
        "Review or resubmit the report with the hazard and location clearly described."
    )

st.markdown("### General response guidance")
action = str(incident.get("recommended_action") or "").strip()
if action:
    st.info(action.replace("Recommended action:", "Suggested guidance:", 1))
    st.caption("Guidance only — this does not confirm a dispatch or verify on-scene conditions.")
else:
    st.info("No response guidance has been generated for this report yet.")

assignment = center.assignment_for(selected_id)
if assignment and assignment.get("reason"):
    st.caption(str(assignment["reason"]))

st.markdown("### Resource readiness")
st.caption(
    "Incident assessment and resource availability are separate. A priority score can be calculated "
    "without a verified rescue-team, hospital, medicine, or shelter inventory."
)

counts = {
    "Active reported incidents": len(active_incidents),
    "Verified resource records loaded": len(center.resources),
    "Hospital records loaded": len(center.hospitals),
    "Shelter records loaded": len(center.shelters),
}
cols = st.columns(len(counts))
for col, (label, count) in zip(cols, counts.items()):
    col.metric(label, count)

if not center.resources:
    st.error(
        "Resource allocation unavailable: no verified rescue-team inventory is connected. "
        "No team name, distance, ambulance, or medication availability can be recommended until "
        "real resource records or a trusted live feed is configured."
    )
elif not assignment or not assignment.get("resource_id"):
    st.warning(
        "No eligible nearby resource has been assigned from the currently loaded records. "
        "Check verified resource coordinates, capabilities, capacity, and current availability."
    )
else:
    resource_id = assignment.get("resource_id")
    resource_name = assignment.get("resource_name")
    distance = assignment.get("distance_km")
    if resource_id and resource_name and isinstance(distance, (int, float)):
        st.success(f"Candidate resource: {resource_name} ({resource_id}) · {distance:.2f} km")
        st.caption("This is a decision-support candidate, not a confirmed dispatch.")

if not center.hospitals:
    st.warning(
        "No verified hospital inventory is connected. Hospital capacity, ambulance destination, "
        "and medicine stock cannot be confirmed from the current data."
    )
elif assignment and (assignment.get("hospital_name") or assignment.get("hospital_id")):
    st.write("**Hospital candidate:** " + str(assignment.get("hospital_name") or assignment.get("hospital_id")))
else:
    st.info("No hospital recommendation is available from the currently loaded records.")

if center.shelters and assignment and (assignment.get("shelter_name") or assignment.get("shelter_id")):
    st.write("**Shelter candidate:** " + str(assignment.get("shelter_name") or assignment.get("shelter_id")))
elif not center.shelters:
    st.caption("No verified shelter inventory is connected.")
