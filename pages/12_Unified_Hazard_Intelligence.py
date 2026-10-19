"""Unified live hazard intelligence from connected official sources."""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from components.theme import page_setup
from core.gdacs_feed import GDACS_SOURCE_URL, fetch_gdacs_events
from core.live_feeds import USGS_ALL_DAY_URL, fetch_usgs_earthquakes

page_setup("Unified Hazard Intelligence")


@st.cache_data(ttl=300, show_spinner=False)
def load_gdacs(days: int):
    return fetch_gdacs_events(lookback_days=days, limit=100)


@st.cache_data(ttl=300, show_spinner=False)
def load_usgs():
    return fetch_usgs_earthquakes(limit=100)


st.markdown('<div class="resq-kicker">RESQ-AI / CONNECTED OFFICIAL SOURCES</div>', unsafe_allow_html=True)
st.title("Unified Hazard Intelligence")
st.caption("A single view of source-reported global hazards. Public feeds do not confirm local damage, verified rescue incidents, or dispatch availability.")
days = st.selectbox("GDACS event window", [7, 30, 90], index=1, format_func=lambda n: f"Past {n} days")
if st.button("Refresh live data", type="primary"):
    load_gdacs.clear()
    load_usgs.clear()
    st.rerun()

sources = []
events = []
failures = []
with st.spinner("Fetching current source data…"):
    try:
        gdacs = load_gdacs(days)
        sources.append({"Source": "GDACS", "Status": "Connected", "Events": gdacs["event_count"], "Retrieved (UTC)": gdacs["fetched_at_utc"], "Official source": GDACS_SOURCE_URL})
        for event in gdacs["events"]:
            events.append({"Hazard": event.get("event_type"), "Event": event.get("name"), "Area": event.get("country"), "Alert": event.get("alert_level"), "Event time (UTC)": event.get("started_at_utc"), "Source": "GDACS", "Record": event.get("source_url"), "Latitude": event.get("latitude"), "Longitude": event.get("longitude")})
    except (requests.RequestException, ValueError, TypeError) as exc:
        failures.append(("GDACS", type(exc).__name__, GDACS_SOURCE_URL))
        sources.append({"Source": "GDACS", "Status": "Unavailable", "Events": "—", "Retrieved (UTC)": "—", "Official source": GDACS_SOURCE_URL})
    try:
        usgs = load_usgs()
        sources.append({"Source": "USGS Earthquake Hazards Program", "Status": "Connected", "Events": usgs["event_count"], "Retrieved (UTC)": usgs["fetched_at_utc"], "Official source": USGS_ALL_DAY_URL})
        for event in usgs["events"]:
            magnitude = event.get("magnitude")
            events.append({"Hazard": "Earthquake", "Event": event.get("location"), "Area": "Not provided", "Alert": f"Magnitude {magnitude}" if magnitude is not None else "Not reported", "Event time (UTC)": event.get("time_utc"), "Source": "USGS", "Record": event.get("detail_url") or USGS_ALL_DAY_URL, "Latitude": event.get("latitude"), "Longitude": event.get("longitude")})
    except (requests.RequestException, ValueError, TypeError) as exc:
        failures.append(("USGS", type(exc).__name__, USGS_ALL_DAY_URL))
        sources.append({"Source": "USGS Earthquake Hazards Program", "Status": "Unavailable", "Events": "—", "Retrieved (UTC)": "—", "Official source": USGS_ALL_DAY_URL})

st.subheader("Source status")
st.dataframe(pd.DataFrame(sources), use_container_width=True, hide_index=True, column_config={"Official source": st.column_config.LinkColumn("Official source", display_text="Open source")})
for name, error, url in failures:
    st.error(f"{name} could not be retrieved ({error}). No example events have been substituted. [Open official source]({url})")

if events:
    df = pd.DataFrame(events)
    hazard_types = ["All hazards"] + sorted(df["Hazard"].dropna().astype(str).unique().tolist())
    selected_hazard = st.selectbox("Filter by hazard", hazard_types)
    search = st.text_input("Search events or locations", placeholder="Search country, event name, hazard…")
    filtered = df.copy()
    if selected_hazard != "All hazards":
        filtered = filtered[filtered["Hazard"] == selected_hazard]
    if search.strip():
        query = search.strip().casefold()
        mask = filtered[["Hazard", "Event", "Area", "Alert", "Source"]].fillna("").astype(str).apply(lambda col: col.str.casefold().str.contains(query, regex=False)).any(axis=1)
        filtered = filtered[mask]
    st.subheader(f"Events ({len(filtered)})")
    st.dataframe(filtered.drop(columns=["Latitude", "Longitude"]), use_container_width=True, hide_index=True, column_config={"Record": st.column_config.LinkColumn("Verify at source", display_text="Open source record")})
    mapped = filtered.dropna(subset=["Latitude", "Longitude"])
    if not mapped.empty:
        st.subheader("Mapped events")
        st.map(mapped.rename(columns={"Latitude": "lat", "Longitude": "lon"})[["lat", "lon"]])
elif not failures:
    st.info("Connected feeds returned no events for this period.")

st.divider()
st.subheader("Coverage and data integrity")
st.write("Connected now: GDACS global events (earthquakes, tropical cyclones, floods, volcanoes, forest fires, droughts) and USGS earthquakes from the past day.")
st.write("Not yet connected: verified local building collapses, road crashes, gas leaks, medical emergencies, local fire dispatch, landslide reports, tsunami warning-centre bulletins, live hospital capacity, ambulance positions, shelter occupancy, and road closures.")
st.caption("These categories are not filled with invented records. They require an official source integration or an operator-submitted report with a clearly marked verification status.")
