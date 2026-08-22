from __future__ import annotations

import streamlit as st

from core.state import CommandCenter
from utils.logging import format_event
from utils.validation import as_int


def render_event_log(center: CommandCenter, limit: int = 12) -> None:
    st.markdown("**Event log**")
    if not center.events:
        st.caption("No events yet.")
        return
    for event in center.events[:limit]:
        st.markdown(f'<div class="event-line">{format_event(event)}</div>', unsafe_allow_html=True)


def attention_banner(center: CommandCenter) -> None:
    hot = [
        i
        for i in center.incidents
        if str(i.get("status")).lower() != "resolved" and as_int(i.get("priority_score")) >= 85
    ]
    if hot:
        ids = ", ".join(str(i.get("id")) for i in hot[:6])
        st.error(f"Incidents requiring immediate attention: {ids}")
    unassigned = [a for a in center.assignments if not a.get("resource_id")]
    if unassigned:
        st.warning(
            "Recommended allocation has gaps: "
            + ", ".join(str(a.get("incident_id")) for a in unassigned[:8])
        )
