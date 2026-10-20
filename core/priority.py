"""Transparent deterministic emergency priority scoring (0–100)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "medical"}


def _parse_ts(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _urgency_band(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def calculate_priority(
    incident: dict[str, Any],
    *,
    now: datetime | None = None,
    nearest_resource_km: float | None = None,
) -> dict[str, Any]:
    """Return score, band, and an explainable component breakdown."""
    status = str(incident.get("status") or "Active").strip().lower()
    if status == "resolved":
        return {
            "score": 0,
            "urgency": "Resolved",
            "components": [
                {"label": "Resolved status", "points": 0, "detail": "Closed incidents are not queued"},
            ],
            "formula_note": "Resolved incidents receive a priority of 0.",
        }

    severity = max(1, min(5, _as_int(incident.get("severity"), 3)))
    people = max(0, _as_int(incident.get("people_affected"), 0))
    medical = _as_bool(incident.get("medical_emergency"))
    vulnerable = max(0, _as_int(incident.get("vulnerable_population"), 0))
    access = str(incident.get("accessibility") or "Open").strip().title()

    severity_pts = severity * 6  # 6–30
    # Scale impact beyond small incidents: the old 25-point cap made 120,000
    # affected people contribute no more than a report involving ~88 people.
    # Keep the existing small-incident scale, then increase points by impact tier.
    if people <= 70:
        people_pts = int(round(people * (20 / 70)))
    elif people < 100:
        people_pts = round(20 + (people - 70) * (5 / 30))
    elif people < 500:
        people_pts = round(25 + (people - 100) * (5 / 400))
    elif people < 1_000:
        # A report affecting nearly 1,000 people should have a substantial impact weight.
        people_pts = round(30 + (people - 500) * (16 / 500))
    elif people < 5_000:
        people_pts = round(46 + (people - 1_000) * (10 / 4_000))
    elif people < 10_000:
        people_pts = round(56 + (people - 5_000) * (8 / 5_000))
    elif people < 50_000:
        people_pts = round(64 + (people - 10_000) * (6 / 40_000))
    elif people < 100_000:
        people_pts = round(70 + (people - 50_000) * (5 / 50_000))
    else:
        people_pts = 75
    medical_pts = 20 if medical else 0
    vuln_pts = min(10, 4 + min(6, vulnerable // 10)) if vulnerable > 0 else 0
    if access == "Blocked":
        access_pts = 10
    elif access == "Restricted":
        access_pts = 6
    else:
        access_pts = 0

    now = now or datetime.now(timezone.utc)
    reported = _parse_ts(incident.get("reported_at"))
    hours = 0.0
    if reported:
        hours = max(0.0, (now - reported).total_seconds() / 3600.0)
    time_pts = min(8, int(hours * 1.5) + (2 if hours >= 1 else 0))

    proximity_pts = 0
    proximity_detail = "Not applied"
    if nearest_resource_km is not None and nearest_resource_km != float("inf"):
        if nearest_resource_km > 8:
            proximity_pts = 7
            proximity_detail = f"{nearest_resource_km:.1f} km from nearest resource"
        elif nearest_resource_km > 4:
            proximity_pts = 4
            proximity_detail = f"{nearest_resource_km:.1f} km from nearest resource"
        else:
            proximity_detail = f"{nearest_resource_km:.1f} km from nearest resource"

    components = [
        {"label": "Severity", "points": severity_pts, "detail": f"Severity {severity}/5 × 6"},
        {"label": "People affected", "points": people_pts, "detail": f"{people:,} people affected; impact contribution {people_pts}/75"},
        {"label": "Medical emergency", "points": medical_pts, "detail": "Yes" if medical else "No"},
        {"label": "Vulnerability", "points": vuln_pts, "detail": f"{vulnerable} vulnerable / children / elderly"},
        {"label": "Accessibility risk", "points": access_pts, "detail": access},
        {"label": "Time factor", "points": time_pts, "detail": f"{hours:.1f} hours since report"},
        {"label": "Resource proximity", "points": proximity_pts, "detail": proximity_detail},
    ]
    score = int(min(100, sum(c["points"] for c in components)))
    return {
        "score": score,
        "urgency": _urgency_band(score),
        "components": components,
        "formula_note": (
            "Priority Score = severity + people + medical + vulnerability "
            "+ accessibility + time + proximity (capped at 100). "
            "People-impact points scale with reported impact: 70 people = 20 points; "
            "1,000 people = 46 points; 100,000 or more = 75 points."
        ),
    }


def recommended_action(incident: dict[str, Any], urgency: str) -> str:
    disaster = str(incident.get("disaster_type") or "Incident")
    medical = _as_bool(incident.get("medical_emergency"))
    access = str(incident.get("accessibility") or "")
    if urgency == "Resolved":
        return "No further field assignment required. Keep on after-action review."
    parts = []
    if medical:
        parts.append("Immediate medical rescue")
    if "flood" in disaster.lower():
        parts.append("evacuation to higher ground / shelter")
    elif "fire" in disaster.lower():
        parts.append("fire suppression and perimeter control")
    elif "collapse" in disaster.lower() or "earthquake" in disaster.lower():
        parts.append("structural rescue / search")
    else:
        parts.append("field rescue dispatch")
    if access.lower() == "blocked":
        parts.append("alternate access route required")
    text = " and ".join(parts) + "."
    if urgency == "Critical":
        return f"Recommended action: {text[0].upper() + text[1:]}"
    return f"Recommended action: {text[0].upper() + text[1:]}"
