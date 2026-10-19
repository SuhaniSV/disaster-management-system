"""Real-time disaster awareness dashboard.

Operational dispatch data is shown only when entered by an operator or connected
to a verified operational feed. Public hazard feeds are informational.
"""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from components.theme import render_header, render_sidebar
from components.session import get_center
from core.gdacs_feed import GDACS_SOURCE_URL, fetch_gdacs_events
from core.live_feeds import USGS_ALL_DAY_URL, fetch_usgs_earthquakes


@st.cache_data(ttl=300, show_spinner=False)
def _load_gdacs():
    return fetch_gdacs_events(lookback_days=30, limit=100)


@st.cache_data(ttl=300, show_spinner=False)
def _load_usgs():
    return fetch_usgs_earthquakes(limit=100)


def render_command_center() -> None:
    center = get_center()
    render_sidebar(center)
    render_header(center, "Live hazard intelligence from public official sources. Operational dispatch data is kept separate until verified.")
    st.subheader("Live hazard overview")
    st.caption("Feeds refresh on demand and are cached for up to five minutes. Event reports are not proof of local damage or dispatch requirements.")
    if st.button("Refresh all live sources", type="primary"):
        _load_gdacs.clear()
        _load_usgs.clear()
        st.rerun()

    gdacs = None
    usgs = None
    failures = []
    with st.spinner("Retrieving live public hazard feeds…"):
        try:
            gdacs = _load_gdacs()
        except (requests.RequestException, ValueError, TypeError) as exc:
            failures.append(("GDACS", type(exc).__name__, GDACS_SOURCE_URL))
        try:
            usgs = _load_usgs()
        except (requests.RequestException, ValueError, TypeError) as exc:
            failures.append(("USGS earthquakes", type(exc).__name__, USGS_ALL_DAY_URL))

    gdacs_events = (gdacs or {}).get("events", [])
    usgs_events = (usgs or {}).get("events", [])
    c1, c2, c3 = st.columns(3)
    c1.metric("GDACS hazard events", len(gdacs_events) if gdacs is not None else "Unavailable")
    c2.metric("USGS earthquakes · past day", len(usgs_events) if usgs is not None else "Unavailable")
    c3.metric("Operator-reported incidents", len(center.incidents))

    source_rows = []
    if gdacs is not None:
        source_rows.append({"Source": "GDACS", "Status": "Connected", "Events returned": len(gdacs_events), "Retrieved (UTC)": gdacs.get("fetched_at_utc", "Not provided"), "Official source": GDACS_SOURCE_URL})
    else:
        source_rows.append({"Source": "GDACS", "Status": "Unavailable", "Events returned": "—", "Retrieved (UTC)": "—", "Official source": GDACS_SOURCE_URL})
    if usgs is not None:
        source_rows.append({"Source": "USGS Earthquake Hazards Program", "Status": "Connected", "Events returned": len(usgs_events), "Retrieved (UTC)": usgs.get("fetched_at_utc", "Not provided"), "Official source": USGS_ALL_DAY_URL})
    else:
        source_rows.append({"Source": "USGS Earthquake Hazards Program", "Status": "Unavailable", "Events returned": "—", "Retrieved (UTC)": "—", "Official source": USGS_ALL_DAY_URL})
    st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True,
        column_config={"Official source": st.column_config.LinkColumn("Official source", display_text="Open source")})

    if failures:
        for source, reason, url in failures:
            st.warning(f"{source} feed is unavailable ({reason}). No sample events were substituted. [Open official source]({url})")

    rows = []
    for event in gdacs_events:
        rows.append({
            "Hazard": event.get("event_type", "Hazard"),
            "Event / location": event.get("name", "Not reported"),
            "Area": event.get("country", "Not reported"),
            "Alert": event.get("alert_level", "Not reported"),
            "Event time (UTC)": event.get("started_at_utc") or "Not provided",
            "Source": "GDACS",
            "Record": event.get("source_url") or GDACS_SOURCE_URL,
            "Latitude": event.get("latitude"),
            "Longitude": event.get("longitude"),
        })
    for event in usgs_events:
        rows.append({
            "Hazard": "Earthquake",
            "Event / location": event.get("location", "Location not reported"),
            "Area": "Not provided",
            "Alert": f"Magnitude {event['magnitude']}" if event.get("magnitude") is not None else "Not reported",
            "Event time (UTC)": event.get("time_utc") or "Not provided",
            "Source": "USGS",
            "Record": event.get("detail_url") or USGS_ALL_DAY_URL,
            "Latitude": event.get("latitude"),
            "Longitude": event.get("longitude"),
        })
    if rows:
        events_df = pd.DataFrame(rows)
        st.subheader("Latest source-reported events")
        st.dataframe(events_df.drop(columns=["Latitude", "Longitude"]), use_container_width=True, hide_index=True,
            column_config={"Record": st.column_config.LinkColumn("Verify at source", display_text="Open record")})
        located = events_df.dropna(subset=["Latitude", "Longitude"])
        if not located.empty:
            st.subheader("Event locations")
            st.map(located.rename(columns={"Latitude": "lat", "Longitude": "lon"})[["lat", "lon"]])
    elif not failures:
        st.info("The connected sources returned no events for the selected windows. This is an actual empty feed result.")

    st.divider()
    st.subheader("Operational response data")
    st.info("No verified live ambulance, hospital-capacity, shelter-occupancy, traffic-closure, or local emergency-dispatch feed is connected yet. This section will not invent resource counts. Use Report Incident for operator-submitted reports; these are not automatically verified.")
    if center.incidents:
        st.caption("Operator-submitted incidents in this session")
        st.dataframe(pd.DataFrame(center.incidents), use_container_width=True, hide_index=True)
