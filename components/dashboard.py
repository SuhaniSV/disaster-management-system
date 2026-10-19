
from __future__ import annotations

import streamlit as st

from components.alerts import attention_banner, render_event_log
from components.incident_table import priority_queue, score_breakdown
from components.map import render_map
from components.metrics import metric_cards
from components.session import get_center
from components.theme import render_header, render_sidebar
from utils.validation import as_bool


def render_command_center() -> None:
    center = get_center()

    render_sidebar(center)
    render_header(
        center,
        "Emergency response intelligence · simulated Pune-area prototype",
    )

    attention_banner(center)
    metric_cards(center.metrics())

    left, right = st.columns([1.35, 1])

    with left:
        st.markdown("**Incident map**")
        render_map(center)

    with right:
        st.markdown("**Priority incident queue**")
        selected = priority_queue(center)

        if selected:
            incident = next(
                (
                    item
                    for item in center.incidents
                    if item.get("id") == selected
                ),
                None,
            )

            assignment = center.assignment_for(selected)

            if incident:
                st.markdown(f"### {incident.get('id')}")

                st.markdown(
                    f"**{incident.get('disaster_type')}** · "
                    f"{incident.get('urgency')} · "
                    f"Status: {incident.get('status')}"
                )

                score_breakdown(incident)

                st.write(
                    f"People affected: "
                    f"**{incident.get('people_affected')}**"
                )

                st.write(
                    f"Medical emergency: "
                    f"**{'YES' if as_bool(incident.get('medical_emergency')) else 'NO'}**"
                )

                st.write(
                    f"Accessibility: "
                    f"**{incident.get('accessibility')}**"
                )

                st.write(
                    incident.get("recommended_action") or ""
                )

                if assignment:
                    st.markdown("**Recommended response**")

                    st.write(
                        f"Assigned resource: "
                        f"**{assignment.get('resource_id') or 'None available'}**"
                    )

                    if assignment.get("distance_km") is not None:
                        st.caption(
                            f"Prototype distance: "
                            f"{assignment['distance_km']} km"
                        )

                    st.write(
                        f"Nearest hospital: "
                        f"**{assignment.get('hospital_id') or 'None'}**"
                    )

                    st.write(
                        f"Nearest shelter: "
                        f"**{assignment.get('shelter_id') or 'None'}**"
                    )

                st.caption(
                    incident.get("summary")
                    or incident.get("description")
                    or ""
                )

    st.divider()

    st.markdown("### Recent activity")
    render_event_log(center, limit=8)

    st.caption(
        "Resource pairings and hospital/shelter capacity are available "
        "on the Resources page. Recommendations require human review."
    )
