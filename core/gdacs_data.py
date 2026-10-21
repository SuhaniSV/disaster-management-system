"""Read-only adapter for the official GDACS global disaster-event API."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import certifi
import requests

GDACS_API_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
GDACS_PORTAL_URL = "https://www.gdacs.org/"
_TIMEOUT_SECONDS = 12
_CACHE_SECONDS = 300
_lock = threading.Lock()
_cache: dict[str, Any] = {}


def get_gdacs_events() -> dict[str, Any]:
    """Fetch recent global GDACS events without credentials; never fabricate rows."""
    now = time.monotonic()
    with _lock:
        cached = _cache.get("events")
        if cached and now - cached["_stored_at"] < _CACHE_SECONDS:
            return {**cached, "cached": True}

    today = datetime.now(timezone.utc).date()
    params = {
        "fromdate": (today - timedelta(days=7)).isoformat(),
        "todate": today.isoformat(),
        "eventlist": "DR,EQ,FL,TC,VO,WF",
        "alertlevel": "Green;Orange;Red",
        "pagesize": 100,
        "pagenumber": 1,
    }
    result: dict[str, Any] = {
        "source": "Global Disaster Alert and Coordination System (GDACS)",
        "source_url": GDACS_API_URL,
        "ok": False,
        "events": [],
        "records_seen": 0,
        "fetched_at": None,
        "cached": False,
        "error": None,
    }
    try:
        response = requests.get(
            GDACS_API_URL,
            params=params,
            headers={
                "Accept": "application/geo+json, application/json",
                "User-Agent": "ResQ-AI/1.0 (disaster-awareness dashboard)",
            },
            timeout=_TIMEOUT_SECONDS,
            verify=certifi.where(),
        )
        response.raise_for_status()
        payload = response.json()
        features = payload.get("features", []) if isinstance(payload, dict) else []
        if not isinstance(features, list):
            raise ValueError("GDACS response did not contain a feature list")

        events: list[dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties", {})
            if not isinstance(props, dict):
                continue
            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
            try:
                longitude = float(coords[0]) if len(coords) >= 2 else None
                latitude = float(coords[1]) if len(coords) >= 2 else None
            except (TypeError, ValueError):
                longitude = latitude = None
            name = str(props.get("name") or props.get("eventname") or props.get("eventtype") or "Disaster event")
            country = str(props.get("country") or "").strip()
            event_type = str(props.get("eventtype") or "").strip()
            level = str(props.get("alertlevel") or "").strip()
            start = str(props.get("fromdate") or props.get("fromDate") or "")
            end = str(props.get("todate") or props.get("toDate") or "")
            description_parts = [part for part in (event_type, country, f"Alert level: {level}" if level else "") if part]
            events.append({
                "title": name,
                "summary": " · ".join(description_parts) or "Official GDACS event record.",
                "area": country,
                "country": country,
                "event_type": event_type,
                "alertlevel": level,
                "published": start,
                "expires": end,
                "latitude": latitude,
                "longitude": longitude,
                "link": _source_link(props),
                "source": "GDACS",
            })
        result.update({
            "ok": True,
            "events": events,
            "records_seen": len(features),
            "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        })
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        result["error"] = f"GDACS feed unavailable: {type(exc).__name__}"

    with _lock:
        _cache["events"] = {**result, "_stored_at": now}
    return result


def _source_link(props: dict[str, Any]) -> str:
    """Prefer an official source URL; otherwise build a grounded event link."""
    url = props.get("url") or props.get("link")
    if isinstance(url, str) and url.startswith("https://www.gdacs.org/"):
        return url
    event_id = props.get("eventid")
    event_type = str(props.get("eventtype") or "").strip()
    if event_id is None or not str(event_id).isdigit() or not event_type:
        return GDACS_PORTAL_URL
    return f"https://www.gdacs.org/report.aspx?eventtype={event_type}&eventid={event_id}"
