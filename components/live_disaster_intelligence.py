"""Presentation layer for the official GDACS multi-hazard feed."""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from core.gdacs_feed import GDACS_SOURCE_URL, fetch_gdacs_events


@st.cache_data(ttl=300, show_spinner=False)
def _cached_gdacs_snapshot(lookback_days: int) -> dict:
    return fetch_gdacs_events(lookback_days=lookback_days, limit=100)


def render_live_disaster_intelligence() -> None:
    st.markdown('<div class="resq-kicker">RESQ-AI / LIVE GLOBAL SOURCES</div>', unsafe_allow_html=True)
    st.title("Live Global Disaster Intelligence")
    st.caption(
        "Real source-reported events from GDACS. This feed is separate from response-planning records; "
        "it does not claim to represent verified local incidents or available rescue resources."
    )
    st.warning(
        "Use official alerts as situational awareness, not as a substitute for emergency authorities. "
        "A listed event does not confirm local damage, casualties, or dispatch requirements.",
        icon="⚠️",
    )
    lookback = st.selectbox("Event window", [7, 30, 90], index=1, format_func=lambda value: f"Past {value} days")
    if st.button("Refresh live disaster feed", type="primary"):
        _cached_gdacs_snapshot.clear()
        st.rerun()

    try:
        with st.spinner("Fetching recent events from the official GDACS API…"):
            snapshot = _cached_gdacs_snapshot(lookback)
    except (requests.RequestException, ValueError, TypeError) as exc:
        st.error("The GDACS live feed is unavailable. No sample events have been substituted.")
        st.caption(f"Source status: unavailable ({type(exc).__name__}).")
        st.markdown(f"[Open GDACS official alerts]({GDACS_SOURCE_URL})")
        return

    st.markdown(f"**Source:** [{snapshot['source']}]({snapshot['source_url']})")
    fetched = snapshot.get("fetched_at_utc", "Unknown").replace("T", " ").replace("+00:00", " UTC")
    col1, col2, col3 = st.columns(3)
    col1.metric("Source events returned", snapshot["event_count"])
    col2.metric("Coverage window", f"{snapshot['lookback_days']} days")
    col3.metric("Retrieved (UTC)", fetched)
    st.caption(
        "Hazards covered by this feed: earthquakes, tropical cyclones, floods, volcanoes, forest fires and droughts. "
        "Tsunami-related information may be associated with earthquake events. Coverage and alerting vary by hazard."
    )

    events = snapshot["events"]
    if not events:
        st.info("GDACS returned no events for this time window. This is a real empty result, not demo data.")
        return

    rows = []
    for event in events:
        rows.append({
            "Hazard": event["event_type"],
            "Event": event["name"],
            "Country / area": event["country"],
            "Alert level": event["alert_level"],
            "Severity": event["severity"] or "Not provided",
            "Start (UTC)": (event.get("started_at_utc") or "Not provided").replace("T", " ").replace("+00:00", ""),
            "Last updated (UTC)": (event.get("updated_at_utc") or "Not provided").replace("T", " ").replace("+00:00", ""),
            "Source record": event["source_url"],
        })
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Source record": st.column_config.LinkColumn("Verify at source", display_text="Open GDACS record"),
        },
    )

    located = [event for event in events if event.get("latitude") is not None and event.get("longitude") is not None]
    if located:
        st.markdown("### Mapped event locations")
        st.map(pd.DataFrame([{
            "lat": event["latitude"],
            "lon": event["longitude"],
            "event": event["name"],
            "hazard": event["event_type"],
        } for event in located]))
    st.caption(
        "Retrieved from GDACS; each record should be verified at its linked source. "
        "The feed is informational and is not an emergency alert or dispatch service."
    )
