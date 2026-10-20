from __future__ import annotations

import pandas as pd
import pydeck as pdk
import streamlit as st

from core.config import CITY_LAT, CITY_LON, MAP_ZOOM
from core.geo import DISTANCE_LABEL
from core.state import CommandCenter
from utils.validation import as_bool, as_int


def _urgency_color(incident: dict) -> list[int]:
    status = str(incident.get("status") or "").lower()
    if status == "resolved":
        return [46, 204, 113]
    urgency = str(incident.get("urgency") or "").lower()
    score = as_int(incident.get("priority_score"))
    if urgency == "critical" or score >= 85:
        return [231, 76, 60]
    if urgency == "high" or score >= 70:
        return [230, 126, 34]
    if urgency == "medium" or score >= 45:
        return [241, 196, 15]
    return [52, 152, 219]


def _resource_color(resource: dict) -> list[int]:
    rtype = str(resource.get("type") or "")
    mapping = {
        "rescue_team": [120, 180, 255],
        "medical_rescue": [255, 120, 170],
        "ambulance": [255, 180, 80],
        "fire_response": [255, 80, 80],
    }
    return mapping.get(rtype, [200, 200, 200])


def render_map(center: CommandCenter) -> None:
    incident_rows = []
    for inc in center.incidents:
        try:
            incident_rows.append(
                {
                    "lat": float(inc["lat"]),
                    "lon": float(inc["lon"]),
                    "id": inc.get("id"),
                    "kind": "Incident",
                    "type": inc.get("disaster_type"),
                    "severity": inc.get("severity"),
                    "priority": inc.get("priority_score"),
                    "people": inc.get("people_affected"),
                    "medical": "YES" if as_bool(inc.get("medical_emergency")) else "NO",
                    "status": inc.get("status"),
                    "color": _urgency_color(inc),
                    "radius": 140 if str(inc.get("status")).lower() != "resolved" else 90,
                }
            )
        except (TypeError, ValueError, KeyError):
            continue

    resource_rows = []
    for res in center.resources:
        try:
            resource_rows.append(
                {
                    "lat": float(res["lat"]),
                    "lon": float(res["lon"]),
                    "id": res.get("id"),
                    "kind": str(res.get("type") or "resource").replace("_", " ").title(),
                    "type": res.get("name"),
                    "severity": res.get("status"),
                    "priority": "",
                    "people": res.get("capacity"),
                    "medical": "",
                    "status": res.get("status"),
                    "color": _resource_color(res),
                    "radius": 80,
                }
            )
        except (TypeError, ValueError, KeyError):
            continue

    hospital_rows = []
    for h in center.hospitals:
        try:
            hospital_rows.append(
                {
                    "lat": float(h["lat"]),
                    "lon": float(h["lon"]),
                    "id": h.get("id"),
                    "kind": "Hospital",
                    "type": h.get("name"),
                    "severity": "",
                    "priority": "",
                    "people": h.get("available_beds"),
                    "medical": "ER" if as_bool(h.get("emergency_capability")) else "",
                    "status": f"{h.get('available_beds')}/{h.get('total_beds')} beds",
                    "color": [180, 230, 255],
                    "radius": 70,
                }
            )
        except (TypeError, ValueError, KeyError):
            continue

    shelter_rows = []
    for s in center.shelters:
        try:
            avail = as_int(s.get("capacity")) - as_int(s.get("occupied"))
            shelter_rows.append(
                {
                    "lat": float(s["lat"]),
                    "lon": float(s["lon"]),
                    "id": s.get("id"),
                    "kind": "Shelter",
                    "type": s.get("name"),
                    "severity": "",
                    "priority": "",
                    "people": avail,
                    "medical": "",
                    "status": f"{avail} spaces",
                    "color": [160, 255, 190],
                    "radius": 70,
                }
            )
        except (TypeError, ValueError, KeyError):
            continue

    road_rows = []
    for road in center.roads:
        try:
            blocked = str(road.get("status")).lower() in {"blocked", "closed"}
            road_rows.append(
                {
                    "from_lat": float(road["from_lat"]),
                    "from_lon": float(road["from_lon"]),
                    "to_lat": float(road["to_lat"]),
                    "to_lon": float(road["to_lon"]),
                    "name": f"{road.get('id')} {road.get('name')} ({road.get('status')})",
                    "color": [231, 76, 60] if blocked else [70, 90, 120],
                    "width": 6 if blocked else 2,
                    "id": road.get("id"),
                    "kind": "Road",
                    "type": road.get("name"),
                    "severity": "",
                    "priority": "",
                    "people": "",
                    "medical": "",
                    "status": road.get("status"),
                }
            )
        except (TypeError, ValueError, KeyError):
            continue

    is_dark = st.session_state.get("resq_theme", "Light") == "Dark"
    if is_dark:
        for road in road_rows:
            road["color"] = [255, 111, 128] if any(word in str(road.get("name", "")).lower() for word in ("blocked", "closed")) else [165, 194, 232]
        for row in resource_rows:
            row["color"] = _resource_color(row)
        for row in hospital_rows:
            row["color"] = [88, 216, 255]
        for row in shelter_rows:
            row["color"] = [89, 235, 175]
    layers = []
    if road_rows:
        layers.append(
            pdk.Layer(
                "LineLayer",
                data=pd.DataFrame(road_rows),
                get_source_position=["from_lon", "from_lat"],
                get_target_position=["to_lon", "to_lat"],
                get_color="color",
                get_width="width",
                width_min_pixels=3,
                pickable=True,
            )
        )
    for data in (incident_rows, resource_rows, hospital_rows, shelter_rows):
        if not data:
            continue
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=pd.DataFrame(data),
                get_position=["lon", "lat"],
                get_fill_color="color",
                get_radius="radius",
                radius_min_pixels=6,
                radius_max_pixels=24,
                pickable=True,
                opacity=0.96,
            )
        )

    tooltip = {
        "html": "<b>{kind} {id}</b><br/>{type}<br/>Severity: {severity}<br/>Priority: {priority}"
        "<br/>People / capacity: {people}<br/>Medical: {medical}<br/>Status: {status}",
        "style": {"backgroundColor": "#101a2b" if is_dark else "#ffffff", "color": "#f3f7ff" if is_dark else "#152238", "border": "1px solid #6b8bb8", "borderRadius": "8px", "padding": "10px", "fontSize": "12px"},
    }
    view = pdk.ViewState(latitude=CITY_LAT, longitude=CITY_LON, zoom=MAP_ZOOM, pitch=35)
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view,
        tooltip=tooltip,
        map_provider="carto",
        map_style="dark" if is_dark else "light",
    )
    st.pydeck_chart(deck, use_container_width=True, height=560)
    st.caption(
        "🔴 Critical  🟠 High  🟡 Medium  🟢 Resolved  ·  blue teams  ·  pink medical  ·  cyan hospitals  ·  green shelters. "
        + DISTANCE_LABEL
        + ". Map uses simulated coordinates."
    )
