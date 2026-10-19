"""Unified global hazard monitoring from connected public feeds."""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from core.gdacs_feed import GDACS_SOURCE_URL, fetch_gdacs_events
from core.live_feeds import USGS_ALL_DAY_URL, fetch_usgs_earthquakes


@st.cache_data(ttl=300, show_spinner=False)
def _cached_gdacs(lookback_days: int) -> dict:
    return fetch_gdacs_events(lookback_days=lookback_days, limit=100)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_usgs() -> dict:
    return fetch_usgs_earthquakes(limit=100)


def render_live_disaster_intelligence() -> None:
    st.markdown('<div class="resq-kicker">RESQ-AI / GLOBAL MONITORING</div>', unsafe_allow_html=True)
    st.title("Live Disaster Intelligence")
    st.caption(
        "A map-first view of source-reported global hazards from GDACS and USGS. "
        "These public feeds do not confirm local damage, casualties, or dispatch requirements."
    )

    controls, refresh_slot = st.columns([4, 1], vertical_alignment="bottom")
    with controls:
        lookback = st.selectbox(
            "GDACS event window", [7, 30, 90], index=1,
            format_func=lambda value: f"Past {value} days",
        )
    with refresh_slot:
        if st.button("Refresh feeds", type="primary", use_container_width=True):
            _cached_gdacs.clear()
            _cached_usgs.clear()
            st.rerun()

    source_rows = []
    events = []
    failures = []
    with st.spinner("Retrieving source-reported hazard events…"):
        try:
            gdacs = _cached_gdacs(lookback)
            source_rows.append({
                "Source": "GDACS",
                "Status": "Connected",
                "Events": gdacs.get("event_count", len(gdacs.get("events", []))),
                "Retrieved (UTC)": gdacs.get("fetched_at_utc", "Not provided"),
                "Official source": GDACS_SOURCE_URL,
            })
            for event in gdacs.get("events", []):
                events.append({
                    "Hazard": event.get("event_type", "Hazard"),
                    "Event": event.get("name", "Name not provided"),
                    "Area": event.get("country", "Not provided"),
                    "Alert / magnitude": event.get("alert_level", "Not reported"),
                    "Event time (UTC)": event.get("started_at_utc") or "Not provided",
                    "Source": "GDACS",
                    "Record": event.get("source_url") or GDACS_SOURCE_URL,
                    "Latitude": event.get("latitude"),
                    "Longitude": event.get("longitude"),
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            failures.append(("GDACS", type(exc).__name__, GDACS_SOURCE_URL))
            source_rows.append({
                "Source": "GDACS", "Status": "Unavailable", "Events": "—",
                "Retrieved (UTC)": "—", "Official source": GDACS_SOURCE_URL,
            })

        try:
            usgs = _cached_usgs()
            source_rows.append({
                "Source": "USGS Earthquake Hazards Program",
                "Status": "Connected",
                "Events": usgs.get("event_count", len(usgs.get("events", []))),
                "Retrieved (UTC)": usgs.get("fetched_at_utc", "Not provided"),
                "Official source": USGS_ALL_DAY_URL,
            })
            for event in usgs.get("events", []):
                magnitude = event.get("magnitude")
                events.append({
                    "Hazard": "Earthquake",
                    "Event": event.get("location", "Location not provided"),
                    "Area": "Not provided",
                    "Alert / magnitude": f"Magnitude {magnitude}" if magnitude is not None else "Not reported",
                    "Event time (UTC)": event.get("time_utc") or "Not provided",
                    "Source": "USGS",
                    "Record": event.get("detail_url") or USGS_ALL_DAY_URL,
                    "Latitude": event.get("latitude"),
                    "Longitude": event.get("longitude"),
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            failures.append(("USGS", type(exc).__name__, USGS_ALL_DAY_URL))
            source_rows.append({
                "Source": "USGS Earthquake Hazards Program", "Status": "Unavailable",
                "Events": "—", "Retrieved (UTC)": "—", "Official source": USGS_ALL_DAY_URL,
            })

    connected = sum(row["Status"] == "Connected" for row in source_rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("Source-reported events", len(events))
    c2.metric("Feeds connected", f"{connected} / {len(source_rows)}")
    c3.metric("Monitoring window", f"{lookback} days + USGS past day")

    with st.expander("Data-source health", expanded=bool(failures)):
        st.dataframe(
            pd.DataFrame(source_rows), use_container_width=True, hide_index=True,
            column_config={"Official source": st.column_config.LinkColumn("Official source", display_text="Open source")},
        )
        for name, reason, url in failures:
            st.warning(f"{name} is unavailable ({reason}). No example events were substituted. [Open official source]({url})")

    if not events:
        if failures:
            st.error("No hazard records could be retrieved from the connected feeds.")
        else:
            st.info("Connected feeds returned no events for these windows.")
        st.caption("Feed retrieval is cached for up to five minutes. Use Refresh feeds to request fresh data.")
        return

    df = pd.DataFrame(events)
    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        hazard_options = ["All hazards"] + sorted(df["Hazard"].dropna().astype(str).unique().tolist())
        selected_hazard = st.selectbox("Hazard type", hazard_options)
    with f2:
        source_options = ["All sources"] + sorted(df["Source"].dropna().astype(str).unique().tolist())
        selected_source = st.selectbox("Data source", source_options)
    with f3:
        query = st.text_input("Search event or location", placeholder="Search event name, area, or alert")

    filtered = df.copy()
    if selected_hazard != "All hazards":
        filtered = filtered[filtered["Hazard"] == selected_hazard]
    if selected_source != "All sources":
        filtered = filtered[filtered["Source"] == selected_source]
    if query.strip():
        term = query.strip().casefold()
        searchable = filtered[["Hazard", "Event", "Area", "Alert / magnitude", "Source"]].fillna("").astype(str)
        filtered = filtered[searchable.apply(lambda col: col.str.casefold().str.contains(term, regex=False)).any(axis=1)]

    map_col, list_col = st.columns([1.5, 1], gap="large")
    with map_col:
        with st.container(border=True):
            st.markdown("### Global hazard map")
            mapped = filtered.dropna(subset=["Latitude", "Longitude"]).copy()
            mapped["Latitude"] = pd.to_numeric(mapped["Latitude"], errors="coerce")
            mapped["Longitude"] = pd.to_numeric(mapped["Longitude"], errors="coerce")
            mapped = mapped.dropna(subset=["Latitude", "Longitude"])
            if not mapped.empty:
                st.map(mapped.rename(columns={"Latitude": "lat", "Longitude": "lon"})[["lat", "lon"]], use_container_width=True)
                st.caption(f"{len(mapped)} filtered events have usable coordinates.")
            else:
                st.info("No mapped events match the current filters.")
    with list_col:
        with st.container(border=True):
            st.markdown(f"### Event stream · {len(filtered)}")
            if filtered.empty:
                st.info("No events match the selected filters.")
            else:
                display = filtered[["Hazard", "Event", "Area", "Alert / magnitude", "Event time (UTC)", "Source", "Record"]]
                st.dataframe(
                    display, use_container_width=True, hide_index=True,
                    column_config={"Record": st.column_config.LinkColumn("Source record", display_text="Verify")},
                    height=520,
                )

    st.markdown("### Coverage and limitations")
    st.caption(
        "GDACS provides multi-hazard global event reporting; USGS provides earthquakes from the past day. "
        "Feed availability and coverage vary by source. Public hazard feeds are not a substitute for official local warnings."
    )
    st.caption(
        "Not connected: live ambulance positions, hospital capacity, shelter occupancy, local dispatch, "
        "verified road closures, or local damage assessments. These are not inferred or filled with fictional records."
    )
