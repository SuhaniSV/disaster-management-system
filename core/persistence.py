"""Durable storage for operator-submitted incidents.

The Streamlit server connects to Supabase Postgres using DATABASE_URL stored in
Streamlit secrets. Never put that connection string in source control.
"""
from __future__ import annotations

import os
from contextlib import closing
from datetime import datetime
from typing import Any

import streamlit as st


def get_database_url() -> str | None:
    """Read the connection string from server-side Streamlit secrets or env."""
    try:
        value = st.secrets.get("DATABASE_URL")
    except Exception:
        value = None
    return str(value).strip() if value else os.getenv("DATABASE_URL")


def is_configured() -> bool:
    return bool(get_database_url())


def _connect():
    """Open a short-lived TLS-protected Postgres connection."""
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured in Streamlit secrets.")
    import psycopg2

    return psycopg2.connect(database_url, connect_timeout=10, sslmode="require")


def incident_record(
    incident: dict[str, Any],
    analysis: dict[str, Any] | None = None,
    assignment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the relational columns plus complete JSON snapshots for a report."""
    incident_id = str(incident.get("id") or "").strip()
    if not incident_id:
        raise ValueError("Incident is missing its ID.")

    lat = incident.get("lat")
    lon = incident.get("lon")
    location = (
        f"{float(lat):.6f}, {float(lon):.6f}"
        if lat is not None and lon is not None
        else "Coordinates not provided"
    )
    disaster_type = str(incident.get("disaster_type") or "Unclassified")
    description = str(incident.get("description") or "").strip()
    if not description:
        raise ValueError("Incident description is empty.")

    return {
        "incident_code": incident_id,
        "title": disaster_type,
        "hazard_type": disaster_type,
        "location": location,
        "description": description,
        "severity": str(incident.get("severity") or "Unknown"),
        "status": str(incident.get("status") or "Active"),
        "people_affected": max(0, int(incident.get("people_affected") or 0)),
        "source": str(incident.get("source") or "operator-report"),
        "incident_data": dict(incident),
        "analysis_data": dict(analysis or {}),
        "assignment_data": dict(assignment or {}),
    }


def save_incident(
    incident: dict[str, Any],
    analysis: dict[str, Any] | None = None,
    assignment: dict[str, Any] | None = None,
) -> bool:
    """Persist an incident; return False only when persistence isn't configured.

    Connection/schema errors are raised to the caller so the UI can clearly
    report that the incident was not saved permanently.
    """
    if not is_configured():
        return False

    from psycopg2.extras import Json

    record = incident_record(incident, analysis, assignment)
    columns = (
        "incident_code, title, hazard_type, location, description, severity, "
        "status, people_affected, source, incident_data, analysis_data, assignment_data"
    )
    values = (
        record["incident_code"],
        record["title"],
        record["hazard_type"],
        record["location"],
        record["description"],
        record["severity"],
        record["status"],
        record["people_affected"],
        record["source"],
        Json(record["incident_data"]),
        Json(record["analysis_data"]),
        Json(record["assignment_data"]),
    )
    placeholders = ", ".join(["%s"] * len(values))
    with closing(_connect()) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO public.incidents ({columns}) VALUES ({placeholders})",
                    values,
                )
    return True


def load_incidents() -> list[dict[str, Any]]:
    """Load saved incident snapshots oldest-first for stable command-queue order."""
    if not is_configured():
        return []

    import json
    from psycopg2.extras import RealDictCursor

    with closing(_connect()) as connection:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT incident_data, created_at FROM public.incidents "
                    "ORDER BY created_at ASC, id ASC"
                )
                rows = cursor.fetchall()

    incidents: list[dict[str, Any]] = []
    for row in rows:
        payload = row.get("incident_data")
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict) or not payload:
            continue
        incident = dict(payload)
        if not incident.get("reported_at"):
            created_at = row.get("created_at")
            incident["reported_at"] = (
                created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or "")
            )
        incidents.append(incident)
    return incidents
