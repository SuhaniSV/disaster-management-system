
from __future__ import annotations

import streamlit as st

from components.resource_cards import render_resources
from components.session import get_center, persist
from components.theme import page_setup, render_header, render_sidebar

page_setup("Resources")

center = get_center()

render_sidebar(center)
render_header(
    center,
    "Verified operational inventory is not connected. No live unit status is available yet.",
)

# Field resources
st.markdown("### Field resources")
render_resources(center)

st.divider()

# Update resource operational status
st.markdown("### Update resource status")
st.caption(
    "Changes recalculate the recommended response plan. "
    "Recommendations must be reviewed by a human coordinator."
)

ids = [r.get("id") for r in center.resources if r.get("id")]

if ids:
    col1, col2, col3 = st.columns(3)

    with col1:
        rid = st.selectbox("Resource", ids)

    with col2:
        new_status = st.selectbox(
            "Status",
            ["Available", "Unavailable"],
        )

    with col3:
        st.write("")
        st.write("")
        if st.button("Update resource", use_container_width=True):
            center.set_resource_status(rid, new_status)
            persist(center)
            st.success(
                f"{rid} set to {new_status}. "
                "The response plan has been recalculated."
            )
            st.rerun()
else:
    st.info("No field resources are currently available to manage.")
