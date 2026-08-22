"""Greedy weighted resource assignment. Designed so a solver can replace assign_resources later."""

from __future__ import annotations

from typing import Any, Callable

from core.geo import effective_distance_km, nearest
from core.priority import _as_bool, _as_int


AssignFn = Callable[..., list[dict[str, Any]]]


def _available(resource: dict[str, Any]) -> bool:
    return str(resource.get("status") or "").strip().lower() in {"available", "idle", "standby"}


def _capability_match(incident: dict[str, Any], resource: dict[str, Any]) -> int:
    """Higher is a better type match. 0 means not usable."""
    rtype = str(resource.get("type") or "").lower()
    caps = str(resource.get("capabilities") or "").lower()
    disaster = str(incident.get("disaster_type") or "").lower()
    medical = _as_bool(incident.get("medical_emergency"))

    score = 1
    if medical and rtype in {"medical_rescue", "ambulance"}:
        score += 8
    elif medical and "medical" in caps:
        score += 5
    elif medical and rtype == "rescue_team":
        score += 2

    if "fire" in disaster and rtype == "fire_response":
        score += 8
    if "flood" in disaster and rtype in {"rescue_team", "medical_rescue"}:
        score += 3
    if "collapse" in disaster or "earthquake" in disaster:
        if rtype == "rescue_team":
            score += 4
    if "accident" in disaster and rtype in {"ambulance", "medical_rescue"}:
        score += 3
    return score


def _capacity_ok(incident: dict[str, Any], resource: dict[str, Any]) -> bool:
    cap = _as_int(resource.get("capacity"), 1)
    people = _as_int(incident.get("people_affected"), 0)
    # Teams do not need 1:1 people capacity; they need enough to start a response.
    return cap >= min(8, max(1, people // 15 or 1)) or cap >= 4


def greedy_assign(
    incidents: list[dict[str, Any]],
    resources: list[dict[str, Any]],
    roads: list[dict[str, Any]] | None = None,
    hospitals: list[dict[str, Any]] | None = None,
    shelters: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Assign at most one available resource per active incident, highest priority first."""
    roads = roads or []
    hospitals = hospitals or []
    shelters = shelters or []

    remaining = [r for r in resources if _available(r)]
    used: set[str] = set()
    assignments: list[dict[str, Any]] = []

    active = [
        i
        for i in incidents
        if str(i.get("status") or "").lower() != "resolved"
    ]
    active.sort(key=lambda x: int(x.get("priority_score") or 0), reverse=True)

    for incident in active:
        lat, lon = incident.get("lat"), incident.get("lon")
        try:
            lat_f, lon_f = float(lat), float(lon)
        except (TypeError, ValueError):
            continue

        best = None
        best_metric = None
        for resource in remaining:
            rid = str(resource.get("id"))
            if rid in used:
                continue
            match = _capability_match(incident, resource)
            if match <= 0 or not _capacity_ok(incident, resource):
                continue
            try:
                dist, blocked_id = effective_distance_km(
                    lat_f,
                    lon_f,
                    float(resource["lat"]),
                    float(resource["lon"]),
                    roads,
                )
            except (TypeError, ValueError, KeyError):
                continue
            # Lower is better: distance penalized, match rewarded.
            metric = dist - (match * 0.35)
            if best_metric is None or metric < best_metric:
                best_metric = metric
                best = (resource, dist, blocked_id, match)

        hospital = _recommend_hospital(incident, lat_f, lon_f, hospitals, roads)
        shelter = _recommend_shelter(incident, lat_f, lon_f, shelters, roads)

        if not best:
            assignments.append(
                {
                    "incident_id": incident.get("id"),
                    "resource_id": None,
                    "resource_name": None,
                    "distance_km": None,
                    "reason": "No suitable available resource with matching capability/capacity.",
                    "blocked_road_id": None,
                    "hospital_id": hospital[0],
                    "hospital_name": hospital[1],
                    "hospital_km": hospital[2],
                    "shelter_id": shelter[0],
                    "shelter_name": shelter[1],
                    "shelter_km": shelter[2],
                    "method": "greedy-weighted",
                }
            )
            continue

        resource, dist, blocked_id, match = best
        used.add(str(resource.get("id")))
        rtype = str(resource.get("type") or "resource").replace("_", " ").title()
        reason_bits = [
            f"Closest available {rtype.lower()} with sufficient capacity",
            f"capability match {match}",
        ]
        if blocked_id:
            reason_bits.append(f"straight-line path crosses {blocked_id}; detour penalty applied")
        assignments.append(
            {
                "incident_id": incident.get("id"),
                "resource_id": resource.get("id"),
                "resource_name": resource.get("name"),
                "distance_km": round(float(dist), 2),
                "reason": ". ".join(reason_bits) + ".",
                "blocked_road_id": blocked_id,
                "hospital_id": hospital[0],
                "hospital_name": hospital[1],
                "hospital_km": hospital[2],
                "shelter_id": shelter[0],
                "shelter_name": shelter[1],
                "shelter_km": shelter[2],
                "method": "greedy-weighted",
            }
        )

    return assignments


def _recommend_hospital(incident, lat, lon, hospitals, roads) -> tuple:
    if not hospitals:
        return None, None, None
    medical = _as_bool(incident.get("medical_emergency"))

    def ok(h: dict[str, Any]) -> bool:
        beds = _as_int(h.get("available_beds"), 0)
        if beds <= 0:
            return False
        if medical and str(h.get("emergency_capability") or "").lower() in {"no", "false", "0"}:
            return False
        return True

    found, dist, _ = nearest(lat, lon, hospitals, predicate=ok, roads=roads)
    if not found:
        found, dist, _ = nearest(
            lat,
            lon,
            hospitals,
            predicate=lambda h: _as_int(h.get("available_beds"), 0) > 0,
            roads=roads,
        )
    if not found:
        return None, None, None
    return found.get("id"), found.get("name"), round(dist, 2)


def _recommend_shelter(incident, lat, lon, shelters, roads) -> tuple:
    if not shelters:
        return None, None, None
    disaster = str(incident.get("disaster_type") or "").lower()
    people = _as_int(incident.get("people_affected"), 0)
    needs_evac = people >= 15 or any(k in disaster for k in ("flood", "fire", "collapse", "cyclone", "landslide"))
    if not needs_evac:
        return None, None, None

    def ok(s: dict[str, Any]) -> bool:
        cap = _as_int(s.get("capacity"), 0) - _as_int(s.get("occupied"), 0)
        return cap >= min(people, 20) or cap > 0

    found, dist, _ = nearest(lat, lon, shelters, predicate=ok, roads=roads)
    if not found:
        return None, None, None
    return found.get("id"), found.get("name"), round(dist, 2)


def assign_resources(*args, **kwargs) -> list[dict[str, Any]]:
    """Public entry point. Swap implementation here for a future MIP/CP-SAT solver."""
    return greedy_assign(*args, **kwargs)
