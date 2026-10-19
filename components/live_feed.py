"""Streamlit presentation for the public USGS earthquake feed."""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from core.live_feeds import fetch_usgs_earthquakes


@st.cache_data(ttl=300, show_spinner=False)
def _cached_usgs_snapshot() -> dict:
    """Cache successful feed snapshots for five minutes to avoid excess requests."""
    return fetch_usgs_earthquakes(limit=20)


def render_live_earthquake_feed() -> None:
    st.markdown("### 🌐 Live earthquake intelligence")
    st.caption(
        "Live public USGS data, separate from the simulated incidents used by "
        "the RescueX/ResQ-AI response-planning prototype."
    )

    try:
        with st.spinner("Fetching the latest USGS earthquake feed…"):
            snapshot = _cached_usgs_snapshot()
    except (requests.RequestException, ValueError, TypeError) as exc:
        st.warning(
            "The live USGS feed is temporarily unavailable. The dashboard's "
            "simulated incident data is unchanged; no live events are being shown."
        )
        st.caption(f"Feed status: unavailable ({type(exc).__name__}).")
        if st.button("Retry live feed", key="retry_usgs_feed"):
            _cached_usgs_snapshot.clear()
            st.rerun()
        return

    source_url = snapshot["source_url"]
    st.markdown(f"**Source:** [{snapshot['source_name']}]({source_url})")

    checked = snapshot.get("fetched_at_utc") or "Unknown"
    generated = snapshot.get("feed_generated_at_utc") or "Not provided by source"
    col1, col2, col3 = st.columns(3)
    col1.metric("Events in feed", snapshot["event_count"])
    col2.metric("Last fetched (UTC)", checked.replace("T", " ").replace("+00:00", ""))
    col3.metric(
        "Feed generated (UTC)",
        generated.replace("T", " ").replace("+00:00", "")
        if generated != "Not provided by source"
        else generated,
    )
    st.caption(
        "Coverage: earthquakes from the past 24 hours · Refresh cache: up to 5 minutes · "
        "Times shown in UTC. This feed is informational and does not trigger dispatch."
    )

    events = snapshot["events"]
    if not events:
        st.info("The USGS feed returned no earthquake events for this period.")
        return

    rows = []
    for event in events:
        magnitude = event.get("magnitude")
        depth = event.get("depth_km")
        rows.append(
            {
                "Magnitude": f"{magnitude:.1f}" if magnitude is not None else "—",
                "Location": event["location"],
                "Detected (UTC)": (event.get("time_utc") or "—").replace("T", " ").replace("+00:00", ""),
                "Depth (km)": f"{depth:.1f}" if depth is not None else "—",
                "Tsunami flag": "Check USGS" if event.get("tsunami_warning") else "No flag",
                "Details": event.get("detail_url") or "",
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Details": st.column_config.LinkColumn("USGS event details", display_text="Open event"),
        },
    )
