"""Prototype geospatial helpers. Distances are straight-line (Haversine), not routed."""

from __future__ import annotations

import math
from typing import Any, Iterable, Optional


EARTH_RADIUS_KM = 6371.0
DISTANCE_LABEL = "Prototype distance estimation (straight-line / Haversine)"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    try:
        lat1_f, lon1_f, lat2_f, lon2_f = float(lat1), float(lon1), float(lat2), float(lon2)
    except (TypeError, ValueError):
        return float("inf")
    if any(math.isnan(v) for v in (lat1_f, lon1_f, lat2_f, lon2_f)):
        return float("inf")
    p1, p2 = math.radians(lat1_f), math.radians(lat2_f)
    dphi = math.radians(lat2_f - lat1_f)
    dlmb = math.radians(lon2_f - lon1_f)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def _ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)


def segments_intersect(
    a_lat: float,
    a_lon: float,
    b_lat: float,
    b_lon: float,
    c_lat: float,
    c_lon: float,
    d_lat: float,
    d_lon: float,
) -> bool:
    """Treat lat/lon as a planar sketch for prototype intersection checks."""
    a = _ccw(a_lon, a_lat, c_lon, c_lat, d_lon, d_lat)
    b = _ccw(b_lon, b_lat, c_lon, c_lat, d_lon, d_lat)
    c = _ccw(a_lon, a_lat, b_lon, b_lat, c_lon, c_lat)
    d = _ccw(a_lon, a_lat, b_lon, b_lat, d_lon, d_lat)
    return a != b and c != d


def path_crosses_blocked_road(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    roads: Iterable[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    for road in roads:
        status = str(road.get("status", "")).strip().lower()
        if status not in {"blocked", "closed", "inaccessible"}:
            continue
        try:
            if segments_intersect(
                from_lat,
                from_lon,
                to_lat,
                to_lon,
                float(road["from_lat"]),
                float(road["from_lon"]),
                float(road["to_lat"]),
                float(road["to_lon"]),
            ):
                return road
        except (TypeError, ValueError, KeyError):
            continue
    return None


def effective_distance_km(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    roads: Iterable[dict[str, Any]] | None = None,
) -> tuple[float, Optional[str]]:
    base = haversine_km(from_lat, from_lon, to_lat, to_lon)
    if not roads or math.isinf(base):
        return base, None
    blocked = path_crosses_blocked_road(from_lat, from_lon, to_lat, to_lon, roads)
    if blocked:
        # Straight-line path crosses a blocked segment — apply a detour penalty.
        return base * 3.6 + 6.0, str(blocked.get("id") or blocked.get("name") or "blocked-road")
    return base, None


def nearest(
    origin_lat: float,
    origin_lon: float,
    candidates: Iterable[dict[str, Any]],
    *,
    lat_key: str = "lat",
    lon_key: str = "lon",
    predicate=None,
    roads: Iterable[dict[str, Any]] | None = None,
) -> tuple[Optional[dict[str, Any]], float, Optional[str]]:
    best = None
    best_d = float("inf")
    best_blocked = None
    for item in candidates:
        if predicate and not predicate(item):
            continue
        try:
            d, blocked = effective_distance_km(
                origin_lat,
                origin_lon,
                float(item[lat_key]),
                float(item[lon_key]),
                roads,
            )
        except (TypeError, ValueError, KeyError):
            continue
        if d < best_d:
            best, best_d, best_blocked = item, d, blocked
    return best, best_d, best_blocked
