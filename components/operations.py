"""Operator incident workflow and audit timeline."""
from __future__ import annotations
import streamlit as st
from components.session import persist
from core.state import CommandCenter

STATUSES = ["Reported", "Verified", "Assigned", "Responding", "Resolved"]

def render_operations(center: CommandCenter) -> None:
    st.markdown('<div class="resq-kicker">RESQ-AI / OPERATIONS</div>', unsafe_allow_html=True)
    st.title("Incident Operations")
    st.caption("Track verification and response progress. Status changes are operator-entered and are not dispatch commands.")
    rows = sorted(center.incidents, key=lambda r: int(r.get("priority_score") or 0), reverse=True)
    if not rows:
        st.info("No incidents are currently recorded.")
        return
    labels = [f"{r.get('id')} · {r.get('disaster_type')} · score {r.get('priority_score', 0)} · {r.get('workflow_status') or r.get('status')}" for r in rows]
    selected_label = st.selectbox("Select incident", labels)
    incident = rows[labels.index(selected_label)]
    st.markdown(f"### {incident.get('id')} — {incident.get('disaster_type')}")
    a,b,c,d = st.columns(4)
    a.metric("Deterministic priority", f"{incident.get('priority_score',0)}/100")
    b.metric("People reported", int(incident.get("people_affected") or 0))
    c.metric("Status", str(incident.get("workflow_status") or incident.get("status") or "Reported"))
    d.metric("Medical emergency", "Yes" if str(incident.get("medical_emergency")).lower() in {"true","1","yes"} else "No")
    st.write(incident.get("summary") or incident.get("description") or "No description.")
    st.caption(f"Reported: {incident.get('reported_at') or 'unknown'} · Source: {incident.get('source') or 'unspecified'}")
    st.markdown("#### Update workflow")
    current = str(incident.get("workflow_status") or incident.get("status") or "Reported")
    default = current if current in STATUSES else ("Assigned" if current.lower()=="assigned" else "Reported")
    with st.form("incident_workflow"):
        status = st.selectbox("Status", STATUSES, index=STATUSES.index(default))
        note = st.text_area("Operator note (optional)", placeholder="Verification result, handover note, or field update…")
        submit = st.form_submit_button("Save update", type="primary")
    if submit:
        old = incident.get("workflow_status") or incident.get("status")
        incident["workflow_status"] = status
        incident["status"] = "Resolved" if status == "Resolved" else ("Active" if old == "Resolved" else incident.get("status", "Active"))
        if note.strip():
            incident.setdefault("operator_notes", []).append({"at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"), "note": note.strip()[:2000]})
        center.log(f"{incident.get('id')} workflow status changed from {old} to {status}", "audit")
        if note.strip():
            center.log(f"Operator note added to {incident.get('id')}", "note")
        center.recalculate(reason=f"Response plan reviewed after {incident.get('id')} workflow update")
        persist(center)
        st.success("Workflow update saved in the current session.")
        st.rerun()
    notes = incident.get("operator_notes", [])
    if notes:
        st.markdown("#### Operator notes")
        for item in reversed(notes[-20:]):
            with st.container(border=True):
                st.caption(item.get("at", ""))
                st.write(item.get("note", ""))
    st.markdown("#### Audit timeline")
    events = [e for e in center.events if incident.get("id") in str(e.get("message", ""))]
    if not events:
        st.info("No incident-specific events yet.")
    for event in events[:30]:
        with st.container(border=True):
            st.caption(f"{event.get('ts') or event.get('time') or ''} · {event.get('category') or 'event'}")
            st.write(event.get("message") or "")
