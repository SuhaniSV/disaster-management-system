from __future__ import annotations

import pandas as pd
import plotly.express as px
from core.state import CommandCenter
from utils.validation import as_bool, as_int


PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(18,26,43,0.9)",
    font=dict(color="#e8eef7"),
    margin=dict(l=10, r=10, t=40, b=10),
)


def _incidents_df(center: CommandCenter) -> pd.DataFrame:
    return pd.DataFrame(center.incidents or [])


def incidents_by_type(center: CommandCenter):
    df = _incidents_df(center)
    if df.empty:
        return None
    counts = df.groupby("disaster_type").size().reset_index(name="count")
    fig = px.bar(counts, x="disaster_type", y="count", title="Incidents by type")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def incidents_by_severity(center: CommandCenter):
    df = _incidents_df(center)
    if df.empty:
        return None
    fig = px.histogram(df, x="severity", nbins=5, title="Incidents by severity")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def people_over_time(center: CommandCenter):
    df = _incidents_df(center)
    if df.empty or "reported_at" not in df.columns:
        return None
    work = df.copy()
    work["reported_at"] = pd.to_datetime(work["reported_at"], errors="coerce")
    work = work.dropna(subset=["reported_at"]).sort_values("reported_at")
    work["people_affected"] = work["people_affected"].apply(as_int)
    work["cumulative_people"] = work["people_affected"].cumsum()
    fig = px.line(work, x="reported_at", y="cumulative_people", title="People affected over time (cumulative)")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def priority_distribution(center: CommandCenter):
    df = _incidents_df(center)
    if df.empty:
        return None
    fig = px.histogram(df, x="priority_score", nbins=10, title="Priority distribution")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def resource_utilization(center: CommandCenter):
    rows = []
    assigned_ids = {a.get("resource_id") for a in center.assignments if a.get("resource_id")}
    for r in center.resources:
        status = str(r.get("status") or "")
        if r.get("id") in assigned_ids:
            bucket = "Recommended / assigned"
        elif status.lower() == "available":
            bucket = "Available"
        else:
            bucket = "Unavailable"
        rows.append({"status": bucket})
    if not rows:
        return None
    fig = px.pie(pd.DataFrame(rows), names="status", title="Resource utilization (recommended plan)")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def hospital_chart(center: CommandCenter):
    df = pd.DataFrame(center.hospitals or [])
    if df.empty:
        return None
    fig = px.bar(df, x="id", y=["available_beds", "total_beds"], barmode="group", title="Hospital capacity")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def shelter_chart(center: CommandCenter):
    df = pd.DataFrame(center.shelters or [])
    if df.empty:
        return None
    df["available"] = df.apply(lambda r: as_int(r.get("capacity")) - as_int(r.get("occupied")), axis=1)
    fig = px.bar(df, x="id", y=["occupied", "available"], barmode="stack", title="Shelter occupancy")
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


def assignment_table(center: CommandCenter) -> pd.DataFrame:
    rows = []
    for a in center.assignments:
        rows.append(
            {
                "Incident": a.get("incident_id"),
                "Resource": a.get("resource_id") or "Unassigned",
                "Distance km": a.get("distance_km"),
                "Hospital": a.get("hospital_id") or "—",
                "Shelter": a.get("shelter_id") or "—",
                "Reason": a.get("reason"),
            }
        )
    return pd.DataFrame(rows)


def medical_share(center: CommandCenter) -> int:
    active = [i for i in center.incidents if str(i.get("status")).lower() != "resolved"]
    return sum(1 for i in active if as_bool(i.get("medical_emergency")))
