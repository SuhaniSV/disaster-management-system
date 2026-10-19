"""Live global multi-hazard events from the official GDACS API.

GDACS covers earthquake/tsunami-related alerts, tropical cyclones, floods,
volcanoes, forest fires, and droughts. These are source-reported hazard events,
not verified local rescue incidents or resource-dispatch instructions.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

GDACS_API_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
GDACS_SOURCE_NAME = "Global Disaster Alert and Coordination System (GDACS)"
GDACS_SOURCE_URL = "https://www.gdacs.org/Alerts/"
REQUEST_TIMEOUT_SECONDS = 15
EVENT_TYPES = {
    "EQ": "Earthquake",
    "TC": "Tropical cyclone",
    "FL": "Flood",
    "VO": "Volcano",
    "FF": "Forest fire",
    "DR": "Drought",
}


def _value(row: dict[str, Any], *names: str) -> Any:
    """Read a property using case-insensitive candidate names."""
    lowered = {str(key).casefold(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.casefold())
        if value not in (None, ""):
            return value
    return None


def _as_text(value: Any, fallback: str = "") -> str:
    return fallback if value is None else str(value).strip()


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _event_time(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        return text


def _coordinates(feature: dict[str, Any], properties: dict[str, Any]) -> tuple[float | None, float | None]:
    latitude = _as_float(_value(properties, "latitude", "lat"))
    longitude = _as_float(_value(properties, "longitude", "lon", "lng"))
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if isinstance(coords, list) and len(coords) >= 2 and all(
        isinstance(item, (int, float)) for item in coords[:2]
    ):
        # GeoJSON Point coordinates are [longitude, latitude].
        longitude = longitude if longitude is not None else _as_float(coords[0])
        latitude = latitude if latitude is not None else _as_float(coords[1])
    return latitude, longitude


def fetch_gdacs_events(lookback_days: int = 30, limit: int | None = None) -> dict[str, Any]:
    """Fetch and normalize recent GDACS GeoJSON events.

    Network and HTTP errors are raised so the UI can show an honest unavailable
    state instead of substituting fabricated or stale events.
    """
    days = max(1, min(int(lookback_days), 365))
    today = date.today()
    params = {
        "eventlist": ";".join(EVENT_TYPES),
        "fromdate": (today - timedelta(days=days)).isoformat(),
        "todate": today.isoformat(),
    }
    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    page_number = 1
    page_size = 100
    while True:
        response = requests.get(
            GDACS_API_URL,
            params={**params, "pageSize": page_size, "pageNumber": page_number},
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "Accept": "application/geo+json, application/json",
                "User-Agent": "ResQ-AI/1.0 (disaster-intelligence dashboard)",
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
            raise ValueError("GDACS returned an unexpected GeoJSON payload.")
        features = payload["features"]
        if not features:
            break
        for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties") or {}
        if not isinstance(properties, dict):
            continue

        raw_type = _as_text(_value(properties, "eventtype", "event_type", "type")).upper()
        event_type = EVENT_TYPES.get(raw_type, raw_type.title() or "Hazard")
        event_id = _as_text(_value(properties, "eventid", "event_id", "id") or feature.get("id"))
        if event_id and event_id in seen_ids:
            continue
        if event_id:
            seen_ids.add(event_id)
        name = _as_text(_value(properties, "eventname", "name", "title", "description"), event_type)
        country = _as_text(_value(properties, "country", "countryname", "country_name"), "Not reported")
        alert = _as_text(_value(properties, "alertlevel", "alert_level", "alert"), "Not reported")
        severity = _as_text(_value(properties, "severity", "severitytext", "severity_text"), "")
        started = _event_time(_value(properties, "fromdate", "from_date", "date", "eventdate"))
        updated = _event_time(_value(properties, "todate", "to_date", "updated", "pubdate"))
        latitude, longitude = _coordinates(feature, properties)
        link = _as_text(_value(properties, "url", "link", "htmlurl", "event_url"))
        if link and not link.startswith("https://"):
            link = ""

        events.append({
            "id": event_id or f"{raw_type or 'EVENT'}-{len(events) + 1}",
            "event_type": event_type,
            "name": name,
            "country": country,
            "alert_level": alert,
            "severity": severity,
            "started_at_utc": started,
            "updated_at_utc": updated,
            "latitude": latitude,
            "longitude": longitude,
            "source_url": link or GDACS_SOURCE_URL,
            "source": GDACS_SOURCE_NAME,
        })

        if len(features) < page_size:
            break
        page_number += 1

    events.sort(key=lambda item: item.get("updated_at_utc") or item.get("started_at_utc") or "", reverse=True)
    if limit is not None:
        events = events[:max(1, int(limit))]
    return {
        "source": GDACS_SOURCE_NAME,
        "source_url": GDACS_SOURCE_URL,
        "api_url": GDACS_API_URL,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lookback_days": days,
        "event_count": len(events),
        "events": events,
        "data_mode": "live",
    }
