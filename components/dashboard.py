from __future__ import annotations

import streamlit as st

from components.alerts import attention_banner, render_event_log
from components.incident_table import priority_queue, score_breakdown
from components.map import render_map
from components.metrics import metric_cards
from components.resource_cards import hospital_shelter_panels
from components.session import get_center
from components.theme import render_header, render_sidebar
from components.live_feed import render_live_earthquake_feed
from utils.validation import as_bool


def render_command_center() -> None:
    center = get_center()
    render_sidebar(center)
    subtitle = "Emergency response intelligence · live feeds and operator-entered reports" if not center.demo_mode else "Emergency response intelligence · simulated Pune-area prototype"
    render_header(center, subtitle)
    if center.demo_mode:
        attention_banner(center)
        metric_cards(center.metrics())
    else:
        st.info("Live Data Mode is active. No live incident, responder-location, hospital-bed, shelter-occupancy, or road-closure feed is connected by default. Values for those sources are unavailable—not zero. Only operator-entered reports and verified connected feeds appear here.")
        render_live_earthquake_feed()
        st.page_link("pages/7_Live_Government_Alerts.py", label="Open Live Government Alerts (IMD / NDMA)")

    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("**Incident map**")
        render_map(center)
    with right:
        st.markdown("**Priority incident queue**")
        selected = priority_queue(center)
        if selected:
            incident = next((i for i in center.incidents if i.get("id") == selected), None)
            assignment = center.assignment_for(selected)
            if incident:
                st.markdown(f"### {incident.get('id')}")
                st.markdown(
                    f"**{incident.get('disaster_type')}** · {incident.get('urgency')} · "
                    f"status {incident.get('status')}"
                )
                score_breakdown(incident)
                st.write(f"People affected: **{incident.get('people_affected')}**")
                st.write(f"Medical emergency: **{'YES' if as_bool(incident.get('medical_emergency')) else 'NO'}**")
                st.write(f"Accessibility: **{incident.get('accessibility')}**")
                st.write(incident.get("recommended_action") or "")
                if assignment:
                    st.write(f"Assigned resource: **{assignment.get('resource_id') or 'None available'}**")
                    if assignment.get("distance_km") is not None:
                        st.caption(f"Prototype distance: {assignment['distance_km']} km — {assignment.get('reason')}")
                    st.write(f"Nearest hospital: **{assignment.get('hospital_id') or 'None'}** ({assignment.get('hospital_name') or '—'})")
                    st.write(f"Nearest shelter: **{assignment.get('shelter_id') or 'None'}** ({assignment.get('shelter_name') or '—'})")
                st.caption(incident.get("summary") or incident.get("description") or "")

    st.markdown("**Recommended resource assignments**")
    assign_rows = []
    for a in center.assignments:
        assign_rows.append(
            {
                "Incident": a.get("incident_id"),
                "Resource": a.get("resource_id") or "Unassigned",
                "Team": a.get("resource_name") or "—",
                "Distance km": a.get("distance_km"),
                "Hospital": a.get("hospital_id") or "—",
                "Shelter": a.get("shelter_id") or "—",
                "Reason": a.get("reason"),
            }
        )
    if assign_rows:
        st.dataframe(assign_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No assignments yet.")

    if center.demo_mode:
        hospital_shelter_panels(center)
    else:
        st.markdown("### Resource availability")
        st.info("Live responder locations, hospital bed availability, shelter occupancy, and road closures require authorized real-time integrations. No simulated inventory is shown in Live Data Mode.")
    st.divider()
    render_event_log(center, limit=14)
    st.caption("Recommended allocation only. Coordinators remain responsible for operational decisions.")
