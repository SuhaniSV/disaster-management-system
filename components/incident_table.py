from __future__ import annotations

import pandas as pd
import streamlit as st

from core.state import CommandCenter
from utils.validation import as_bool, as_int


def _row(incident: dict, assignment: dict | None) -> dict:
    assigned = assignment.get("resource_id") if assignment else None
    return {
        "Incident": incident.get("id"),
        "Type": incident.get("disaster_type"),
        "Priority": as_int(incident.get("priority_score")),
        "Urgency": incident.get("urgency"),
        "Severity": incident.get("severity"),
        "People": as_int(incident.get("people_affected")),
        "Medical": "YES" if as_bool(incident.get("medical_emergency")) else "NO",
        "Accessibility": incident.get("accessibility"),
        "Assigned resource": assigned or "—",
        "Status": incident.get("status"),
    }


def priority_queue(center: CommandCenter) -> str | None:
    rows = []
    for incident in center.incidents:
        rows.append(_row(incident, center.assignment_for(incident.get("id"))))
    if not rows:
        st.info("No incidents in the current dataset.")
        return None
    df = pd.DataFrame(rows).sort_values(["Priority", "People"], ascending=[False, False])
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=420,
    )
    options = df["Incident"].tolist()
    selected = st.selectbox("VIEW DETAILS", options)
    return selected


def score_breakdown(incident: dict) -> None:
    st.markdown(f"**Priority Score: {incident.get('priority_score', 0)}/100**")
    st.caption(incident.get("urgency") or "")
    for item in incident.get("priority_breakdown") or []:
        st.write(f"{item.get('label')}: **+{item.get('points')}** — {item.get('detail')}")
    st.caption(incident.get("formula_note") or "")
