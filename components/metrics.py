from __future__ import annotations

import streamlit as st


def metric_cards(metrics: dict[str, int]) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    cards = [
        (c1, "ACTIVE INCIDENTS", metrics.get("active_incidents", 0), ""),
        (c2, "CRITICAL", metrics.get("critical_incidents", 0), "critical"),
        (c3, "PEOPLE AFFECTED", metrics.get("people_affected", 0), ""),
        (c4, "AVAILABLE RESOURCES", metrics.get("available_resources", 0), ""),
        (c5, "ASSIGNED RESOURCES", metrics.get("assigned_resources", 0), ""),
        (c6, "MEDICAL EMERGENCIES", metrics.get("medical_emergencies", 0), "medical"),
    ]
    for col, label, value, kind in cards:
        extra = f" {kind}" if kind else ""
        col.markdown(
            f'<div class="metric-card{extra}"><div class="label">{label}</div>'
            f'<div class="value">{value}</div></div>',
            unsafe_allow_html=True,
        )
