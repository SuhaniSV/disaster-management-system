"""Exportable, source-labelled situation reports for ResQ-AI."""
from __future__ import annotations
import csv, io, json
from datetime import datetime, timezone
from typing import Any

def _stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def situation_report(center: Any, live_alerts: dict[str, Any] | None = None) -> dict[str, Any]:
    metrics = center.metrics()
    incidents = sorted(center.incidents, key=lambda r: int(r.get("priority_score") or 0), reverse=True)
    return {
        "report_title": "ResQ-AI Situation Report",
        "generated_at": _stamp(),
        "data_mode": "simulated_demo_data" if getattr(center, "demo_mode", True) else "live_data_mode_session_records_only",
        "data_scope": "simulated sample records" if getattr(center, "demo_mode", True) else "current session records only; no complete live incident or operational-inventory feed is connected by default",
        "disclaimer": "Decision support only. Verify all facts and capacity with responsible authorities. Not a dispatch order.",
        "metrics": metrics,
        "incidents": incidents,
        "assignments": center.assignments,
        "resources": center.resources,
        "hospitals": center.hospitals,
        "shelters": center.shelters,
        "roads": center.roads,
        "recent_events": center.events[:50],
        "live_alerts": live_alerts or {"status": "not_attached", "note": "Live alerts were not fetched for this report."},
    }

def json_report(center: Any, live_alerts: dict[str, Any] | None = None) -> str:
    return json.dumps(situation_report(center, live_alerts), indent=2, ensure_ascii=False, default=str)

def incidents_csv(center: Any) -> str:
    fields = ["id","disaster_type","priority_score","urgency","status","people_affected","medical_emergency","vulnerable_population","accessibility","lat","lon","reported_at","reporter","summary","recommended_action","source"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(center.incidents)
    return stream.getvalue()

def event_log_csv(center: Any) -> str:
    stream = io.StringIO(newline="")
    rows = center.events[:]
    fields = sorted({key for row in rows for key in row}) or ["ts","category","message"]
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()

def situation_report_markdown(center: Any) -> str:
    report = situation_report(center)
    m = report["metrics"]
    lines = ["# ResQ-AI Situation Report", "", f"Generated: {report['generated_at']}", f"Data mode: {report['data_mode']}", f"Data scope: {report['data_scope']}", "",
    "> Decision support only. Verify reports and capacities with authorities. Not a dispatch order.", "",
    "## Situation summary", "", f"- Active incidents: {m.get('active_incidents', 0)}", f"- Critical incidents: {m.get('critical_incidents', 0)}",
    f"- People affected (reported): {m.get('people_affected', 0)}", f"- Available resources (reported): {m.get('available_resources', 0)}",
    f"- Hospital beds available (reported): {m.get('hospital_beds_available', 0)}", f"- Shelter spaces available (reported): {m.get('shelter_spaces_available', 0)}", "",
    "## Priority incidents", ""]
    for item in report["incidents"][:20]:
        lines.append(f"- **{item.get('id')}** — {item.get('disaster_type')}; score {item.get('priority_score', 0)}/100; status {item.get('status')}; people affected {item.get('people_affected', 0)}. {item.get('summary') or item.get('description') or ''}")
    lines += ["", "## Recommended assignments", ""]
    for item in report["assignments"][:30]:
        lines.append(f"- {item.get('incident_id')}: {item.get('resource_name') or item.get('resource_id') or 'Unassigned'}; {item.get('reason') or 'No recommendation reason supplied'}")
    return "\n".join(lines) + "\n"
