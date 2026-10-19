"""Fetch and normalize public live disaster data feeds.

The first integration is the USGS public GeoJSON earthquake feed. It is
read-only and does not change the simulated command-center incidents or
dispatch recommendations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

USGS_ALL_DAY_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
)
USGS_SOURCE_NAME = "USGS Earthquake Hazards Program — Past Day"
REQUEST_TIMEOUT_SECONDS = 8


def _utc_iso_from_ms(value: Any) -> str | None:
    try:
        timestamp = float(value) / 1000.0
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(
            timespec="seconds"
        )
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def fetch_usgs_earthquakes(limit: int | None = None) -> dict[str, Any]:
    """Fetch the USGS past-day GeoJSON feed and return a normalized snapshot.

    Raises requests.RequestException for network/HTTP failures and ValueError
    for malformed feed payloads, allowing the UI to show a clear unavailable
    state instead of silently presenting stale or fabricated live data.
    """
    response = requests.get(
        USGS_ALL_DAY_URL,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"Accept": "application/geo+json, application/json"},
    )
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise ValueError("USGS returned an unexpected GeoJSON payload.")

    metadata = payload.get("metadata") or {}
    generated_at = _utc_iso_from_ms(metadata.get("generated"))
    events: list[dict[str, Any]] = []

    for feature in payload["features"]:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            continue

        try:
            longitude = float(coordinates[0])
            latitude = float(coordinates[1])
        except (TypeError, ValueError):
            continue

        magnitude = _optional_float(properties.get("mag"))
        depth_km = _optional_float(coordinates[2]) if len(coordinates) > 2 else None

        events.append(
            {
                "id": str(feature.get("id") or ""),
                "magnitude": magnitude,
                "location": str(properties.get("place") or "Location not reported"),
                "time_utc": _utc_iso_from_ms(properties.get("time")),
                "latitude": latitude,
                "longitude": longitude,
                "depth_km": depth_km,
                "detail_url": str(properties.get("url") or ""),
                "event_type": str(properties.get("type") or "earthquake"),
                "tsunami_warning": bool(properties.get("tsunami", 0)),
            }
        )

    events.sort(key=lambda event: event["time_utc"] or "", reverse=True)
    if limit is not None:
        events = events[:max(1, int(limit))]
    return {
        "source_name": USGS_SOURCE_NAME,
        "source_url": USGS_ALL_DAY_URL,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "feed_generated_at_utc": generated_at,
        "event_count": len(events),
        "events": events,
        "data_mode": "live",
    }
