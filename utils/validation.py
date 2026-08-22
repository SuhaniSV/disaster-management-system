from __future__ import annotations

from typing import Any


def as_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def valid_lat(value: Any) -> bool:
    v = as_float(value)
    return v is not None and -90 <= v <= 90


def valid_lon(value: Any) -> bool:
    v = as_float(value)
    return v is not None and -180 <= v <= 180


def validate_report(
    description: str,
    people_affected: Any,
    lat: Any,
    lon: Any,
) -> list[str]:
    errors: list[str] = []
    if not str(description or "").strip():
        errors.append("Incident description is required.")
    if not valid_lat(lat):
        errors.append("Latitude must be a number between -90 and 90.")
    if not valid_lon(lon):
        errors.append("Longitude must be a number between -180 and 180.")
    people = as_int(people_affected, -1)
    if people < 0:
        errors.append("Estimated people affected must be zero or a positive number.")
    return errors
