"""Operational command workspace: triage, response tasks, and activity.

Public hazard feeds belong on Live Disaster Intelligence. This page focuses on
operator-submitted reports and operational records only.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.session import get_center
from components.theme import render_header, render_sidebar


def _priority_label(incident: dict) -> str:
    try:
        score = int(float(incident.get("priority_score") or 0))
    except (TypeError, ValueError):
        score = 0
    if score >= 85:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 35:
        return "Moderate"
    return "Low"


def render_command_center() -> None:
    center = get_center()
    render_sidebar(center)
    render_header(
        center,
        "Operational triage and response coordination. Global hazard monitoring lives in Live Disaster Intelligence.",
    )

    incidents = [
        row for row in center.incidents
        if str(row.get("status", "Active")).casefold() != "resolved"
    ]
    critical = [row for row in incidents if _priority_label(row) == "Critical"]
    assignments = [
        row for row in getattr(center, "assignments", [])
        if row.get("resource_id")
    ]
    recent_events = list(getattr(center, "events", []))[:6]

    st.markdown("### Operations at a glance")
    c1, c2, c3 = st.columns(3)
    c1.metric("Open reported incidents", len(incidents))
    c2.metric("Critical priority", len(critical))
    c3.metric("Resource assignments", len(assignments) if center.resources else "Not connected")

    left, right = st.columns([1.65, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### Attention & triage")
            st.caption(
                "Operator-submitted reports only. Priority is a decision-support estimate, "
                "not an official emergency classification."
            )
            if incidents:
                rows = []
                for incident in sorted(
                    incidents,
                    key=lambda item: float(item.get("priority_score") or 0),
                    reverse=True,
                ):
                    rows.append({
                        "ID": incident.get("id", "—"),
                        "Incident": incident.get("disaster_type", "Unclassified"),
                        "Report / location": incident.get("description") or "Location not described",
                        "Priority": _priority_label(incident),
                        "Score": incident.get("priority_score", "—"),
                        "Status": incident.get("status", "Active"),
                        "Reported (UTC)": incident.get("reported_at", "Not provided"),
                    })
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(
                    "No operator-submitted incidents are currently recorded in this session. "
                    "No sample incidents are loaded."
                )
            st.page_link(
                "pages/2_Report_Incident.py",
                label="Report an incident",
                icon="📝",
                use_container_width=True,
            )

        with st.container(border=True):
            st.markdown("### Response readiness")
            if center.resources:
                resource_rows = []
                for resource in center.resources:
                    resource_rows.append({
                        "Resource": resource.get("name") or resource.get("id", "Unnamed resource"),
                        "Type": resource.get("type", "Not specified"),
                        "Status": resource.get("status", "Not specified"),
                    })
                st.dataframe(pd.DataFrame(resource_rows), use_container_width=True, hide_index=True)
                st.caption("Loaded inventory records; operational freshness is not independently verified.")
            else:
                st.info(
                    "No verified operational resource inventory is connected. Live ambulance positions, "
                    "hospital capacity, shelter occupancy, and dispatch status are unavailable."
                )
                st.page_link("pages/3_Resources.py", label="Open resource inventory", icon="📦")

    with right:
        with st.container(border=True):
            st.markdown("### Pending response actions")
            if assignments:
                assignment_rows = []
                for assignment in assignments:
                    assignment_rows.append({
                        "Incident": assignment.get("incident_id", "—"),
                        "Suggested resource": assignment.get("resource_id", "—"),
                        "Distance (km)": assignment.get("distance_km", "Not provided"),
                    })
                st.dataframe(pd.DataFrame(assignment_rows), use_container_width=True, hide_index=True)
                st.caption("Allocation suggestions require human review before operational use.")
            else:
                st.info(
                    "No resource assignments are available. Assignments appear only when incident reports "
                    "and an operational resource inventory are present."
                )

        with st.container(border=True):
            st.markdown("### Recent activity")
            if recent_events:
                for event in recent_events:
                    message = event.get("message", "Activity recorded")
                    timestamp = event.get("timestamp") or event.get("created_at") or "Time not provided"
                    category = str(event.get("category", "activity")).replace("_", " ").title()
                    st.markdown(f"**{category}** · {message}")
                    st.caption(str(timestamp))
                    st.divider()
            else:
                st.caption("No activity has been recorded yet.")

    st.caption(
        "ResQ-AI is decision-support software, not an emergency dispatch service. "
        "Public hazard reports are monitored separately and do not automatically become verified incidents."
    )
