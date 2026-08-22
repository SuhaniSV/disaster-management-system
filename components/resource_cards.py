from __future__ import annotations

import streamlit as st

from core.config import RESOURCE_TYPES
from core.state import CommandCenter
from utils.validation import as_int


def render_resources(center: CommandCenter) -> None:
    cols = st.columns(2)
    for idx, resource in enumerate(center.resources):
        with cols[idx % 2]:
            status = str(resource.get("status") or "")
            color = "#7dffa6" if status.lower() == "available" else "#ff8b9a"
            label = RESOURCE_TYPES.get(str(resource.get("type")), resource.get("type"))
            st.markdown(
                f"""
                <div class="panel" style="margin-bottom:10px">
                  <div style="display:flex;justify-content:space-between">
                    <strong>{resource.get('id')} · {resource.get('name')}</strong>
                    <span style="color:{color}">{status}</span>
                  </div>
                  <div style="color:#9db0cc;font-size:13px;margin-top:6px">
                    {label} · capacity {resource.get('capacity')} · {resource.get('capabilities')}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def hospital_shelter_panels(center: CommandCenter) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown("**Hospital capacity (simulated)**")
        for h in center.hospitals:
            total = as_int(h.get("total_beds"))
            avail = as_int(h.get("available_beds"))
            ratio = 0 if total == 0 else min(1.0, avail / total)
            st.caption(f"{h.get('id')} {h.get('name')}: {avail}/{total} beds")
            st.progress(ratio)
    with right:
        st.markdown("**Shelter capacity (simulated)**")
        for s in center.shelters:
            cap = as_int(s.get("capacity"))
            occ = as_int(s.get("occupied"))
            free = max(0, cap - occ)
            ratio = 0 if cap == 0 else min(1.0, free / cap)
            st.caption(f"{s.get('id')} {s.get('name')}: {free} free / {cap}")
            st.progress(ratio)
