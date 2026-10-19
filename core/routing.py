"""Optional route estimates via OSRM public demo service.

This is a convenience integration, not an emergency-grade routing guarantee.
Use an approved provider for production and verify road closures with authorities.
"""
from __future__ import annotations
import os, requests
from typing import Any
from urllib.parse import urlparse

DEFAULT_BASE = "https://router.project-osrm.org"

def route_estimate(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float) -> dict[str, Any]:
    try:
        coords = [float(origin_lon), float(origin_lat), float(destination_lon), float(destination_lat)]
    except (TypeError, ValueError):
        return {"ok": False, "error": "Coordinates must be numeric."}
    if not (-90 <= coords[1] <= 90 and -90 <= coords[3] <= 90 and -180 <= coords[0] <= 180 and -180 <= coords[2] <= 180):
        return {"ok": False, "error": "Coordinates are outside valid latitude/longitude ranges."}
    base = os.getenv("RESQ_ROUTING_BASE_URL", DEFAULT_BASE).strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname:
        return {"ok": False, "error": "Routing endpoint must be a trusted HTTPS URL."}
    url = f"{base}/route/v1/driving/{coords[0]},{coords[1]};{coords[2]},{coords[3]}"
    try:
        response = requests.get(url, params={"overview": "false", "steps": "false"}, timeout=(3, 8), headers={"User-Agent":"ResQ-AI/1.0"})
        response.raise_for_status()
        payload = response.json()
        routes = payload.get("routes", []) if isinstance(payload, dict) else []
        if not routes:
            return {"ok": False, "error": "No route returned by routing service."}
        route = routes[0]
        return {"ok": True, "distance_km": round(float(route["distance"]) / 1000, 2),
                "duration_minutes": round(float(route["duration"]) / 60, 1),
                "provider": parsed.hostname, "source_url": url,
                "notice": "Estimate only. Public demo routing may be rate-limited, stale, or unaware of disaster road closures."}
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        return {"ok": False, "error": f"Routing service unavailable ({type(exc).__name__})."}
