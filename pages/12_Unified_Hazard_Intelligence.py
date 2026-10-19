"""Unified live hazard and incident intelligence across connected official feeds."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from components.theme import page_setup
from core.gdacs_feed import GDACS_SOURCE_URL, fetch_gdacs_events
from core.live_feeds import USGS_ALL_DAY_URL, fetch_usgs_earthquakes

page_setup("Unified Hazard Intelligence")

st.markdown('<div class="resq-kicker">RESQ-AI / CROSS-SOURCE MONITOR</div>', unsafe_allow_html=True)
st.title("Unified Hazard Intelligence")
st.caption(
    "One searchable view combining records from connected official live feeds. "
    "Every row retains its source; events are not fabricated or converted into verified rescue incidents."
)
st.warning(
    "This page currently combines live GDACS multi-hazard events and the USGS past-day earthquake feed. "
    "Building collapse, road accidents, medical emergencies, gas leaks and local fire incidents need separate "
    "authorized government/emergency-service feeds or verified operator reports; they are not invented when feeds are absent.",
    icon="⚠️",
)

col_a, col_b = st.columns([1, 1])
with col_a:
    window = st.selectbox("GDACS time window", [7, 30, 90], index=1, format_func=lambda n: f"Past {n} days")
with col_b:
    if st.button("Refresh all connected sources", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

@st.cache_data(ttl=300, show_spinner=False)
def get_gdacs(days: int) -> dict:
    return fetch_gdacs_events(lookback_days=days, limit=100)

@st.cache_data(ttl=300, show_spinner=False)
def get_usgs() -> dict:
    return fetch_usgs_earthquakes(limit=100)

records: list[dict] = []
source_status: list[dict] = []

try:
    gdacs = get_gdacs(window)
    source_status.append({
        "Source": "GDACS",
        "Status": "Connected",
        "Records returned": gdacs["event_count"],
        "Last retrieved (UTC)": gdacs["fetched_at_utc"],
        "Official source": GDACS_SOURCE_URL,
    })
    for event in gdacs["events"]:
        records.append({
            "Event ID": event["id"],
            "Hazard": event["event_type"],
            "Event / location": event["name"],
            "Country / area": event["country"],
            "Alert level": event["alert_level"],
            "Magnitude": None,
            "Event time (UTC)": event.get("started_at_utc") or "",
            "Latitude": event.get("latitude"),
            "Longitude": event.get("longitude"),
            "Source": "GDACS",
            "Source record": event["source_url"],
            "Source updated (UTC)": event.get("updated_at_utc") or "",
        })
except (requests.RequestException, ValueError, TypeError) as exc:
    source_status.append({
        "Source": "GDACS",
        "Status": f"Unavailable ({type(exc).__name__})",
        "Records returned": 0,
        "Last retrieved (UTC)": "—",
        "Official source": GDACS_SOURCE_URL,
    })

try:
    usgs = get_usgs()
    source_status.append({
        "Source": "USGS",
        "Status": "Connected",
        "Records returned": usgs["event_count"],
        "Last retrieved (UTC)": usgs["fetched_at_utc"],
        "Official source": USGS_ALL_DAY_URL,
    })
    for event in usgs["events"]:
        records.append({
            "Event ID": event["id"],
            "Hazard": "Earthquake",
            "Event / location": event["location"],
            "Country / area": "Not provided by USGS feed",
            "Alert level": "See source",
            "Magnitude": event.get("magnitude"),
            "Event time (UTC)": event.get("time_utc") or "",
            "Latitude": event.get("latitude"),
            "Longitude": event.get("longitude"),
            "Source": "USGS",
            "Source record": event.get("detail_url") or USGS_ALL_DAY_URL,
            "Source updated (UTC)": "",
        })
except (requests.RequestException, ValueError, TypeError) as exc:
    source_status.append({
        "Source": "USGS",
        "Status": f"Unavailable ({type(exc).__name__})",
        "Records returned": 0,
        "Last retrieved (UTC)": "—",
        "Official source": USGS_ALL_DAY_URL,
    })

status_df = pd.DataFrame(source_status)
st.markdown("### Connected source status")
st.dataframe(
    status_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Official source": st.column_config.LinkColumn("Official source", display_text="Open source"),
    },
)

if not records:
    st.error("No connected source returned records. No demo incidents have been substituted.")
    st.info("Check the source status above and retry when the official feeds are reachable.")
    st.stop()

df = pd.DataFrame(records)
df["Event time (UTC)"] = df["Event time (UTC)"].fillna("")
df["Hazard"] = df["Hazard"].fillna("Other / unclassified")
df["Source"] = df["Source"].fillna("Unknown")

st.markdown("### Combined live records")
st.caption("This table merges source records into one view; it does not merge duplicate events or claim that different feeds have identical coverage.")

hazards = sorted(df["Hazard"].dropna().unique().tolist())
chosen_hazards = st.multiselect("Filter hazard types", hazards, default=hazards)
chosen_sources = st.multiselect("Filter official sources", sorted(df["Source"].unique()), default=sorted(df["Source"].unique()))
search_text = st.text_input("Search event, location or country", placeholder="e.g. earthquake, flood, India")

filtered = df[df["Hazard"].isin(chosen_hazards) & df["Source"].isin(chosen_sources)].copy()
if search_text.strip():
    mask = filtered[["Event / location", "Country / area", "Hazard"]].fillna("").astype(str).apply(
        lambda col: col.str.contains(search_text.strip(), case=False, regex=False)
    ).any(axis=1)
    filtered = filtered[mask]

col1, col2, col3 = st.columns(3)
col1.metric("Live records shown", len(filtered))
col2.metric("Hazard types", filtered["Hazard"].nunique())
col3.metric("Official sources online", sum(item["Status"] == "Connected" for item in source_status))

if filtered.empty:
    st.info("No source records match these filters. No demo rows have been added.")
else:
    display_cols = [
        "Hazard", "Event / location", "Country / area", "Alert level", "Magnitude",
        "Event time (UTC)", "Source", "Source record",
    ]
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Source record": st.column_config.LinkColumn("Verify at source", display_text="Open official record"),
            "Magnitude": st.column_config.NumberColumn("Magnitude", format="%.1f"),
        },
    )

    mapped = filtered.dropna(subset=["Latitude", "Longitude"])
    if not mapped.empty:
        st.markdown("### Event locations")
        st.map(mapped.rename(columns={"Latitude": "lat", "Longitude": "lon"})[["lat", "lon"]])

st.markdown("### Hazard coverage still requiring connectors")
st.caption(
    "These categories are part of the ResQ-AI hazard taxonomy, but are shown here as coverage gaps until "
    "a reliable official feed or verified incident-report workflow is connected. They are not counted as live events."
)
coverage = pd.DataFrame([
    {"Hazard category": "Building collapse", "Data requirement": "Verified fire/rescue, municipal, or disaster-management incident feed"},
    {"Hazard category": "Road accident / road incident", "Data requirement": "Authorized traffic police, highway authority, or emergency dispatch feed"},
    {"Hazard category": "Medical emergency", "Data requirement": "Authorized ambulance / emergency dispatch integration or verified operator report"},
    {"Hazard category": "Urban fire", "Data requirement": "Official fire service incident feed"},
    {"Hazard category": "Gas leak / hazardous materials", "Data requirement": "Fire service, industrial safety, or authorized emergency authority feed"},
    {"Hazard category": "Landslide", "Data requirement": "Official geological / disaster authority alert feed"},
    {"Hazard category": "Tsunami warning", "Data requirement": "Official tsunami warning centre / national warning feed"},
    {"Hazard category": "Dam / river flooding", "Data requirement": "Authorized hydrological / flood forecasting and river-gauge feed"},
])
st.dataframe(coverage, use_container_width=True, hide_index=True)
st.caption(
    "Feed retrieval is cached for up to five minutes. A source being connected means the API returned a valid response, "
    "not that every event worldwide is covered. ResQ-AI is informational and is not an emergency dispatch service."
)
