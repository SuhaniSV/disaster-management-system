"""Operator incident workflow and audit timeline."""
from __future__ import annotations
import streamlit as st
from components.session import persist
from core.state import CommandCenter
from core.duplicate_detection import find_possible_duplicates

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
    # Make the existing allocation engine's recommendation visible at the point of triage.
    st.markdown("#### Resource allocation review")
    assignment = center.assignment_for(str(incident.get("id")))
    if assignment and assignment.get("resource_id"):
        x, y, z = st.columns(3)
        x.metric("Recommended resource", str(assignment.get("resource_name") or assignment.get("resource_id")))
        distance = assignment.get("distance_km")
        y.metric("Estimated distance", f"{distance} km" if distance is not None else "Unavailable")
        z.metric("Assignment state", "Recommendation only")
        st.write(assignment.get("reason") or "Selected by the current weighted allocation logic.")
    else:
        st.warning("No suitable available resource was found for this incident. Review resource availability and capability before deciding next steps.")
        if assignment and assignment.get("reason"):
            st.caption(str(assignment.get("reason")))

    support = []
    if assignment and assignment.get("hospital_name"):
        hospital_distance = assignment.get("hospital_km")
        hospital_text = f"Nearest hospital recommendation: **{assignment.get('hospital_name')}**"
        if hospital_distance is not None:
            hospital_text += f" ({hospital_distance} km estimate)"
        support.append(hospital_text)
    if assignment and assignment.get("shelter_name"):
        shelter_distance = assignment.get("shelter_km")
        shelter_text = f"Shelter recommendation: **{assignment.get('shelter_name')}**"
        if shelter_distance is not None:
            shelter_text += f" ({shelter_distance} km estimate)"
        support.append(shelter_text)
    for item in support:
        st.markdown(f"- {item}")
    st.caption("Recommendations use the prototype's current resource and facility records; they are not live dispatch confirmations. Distance estimates are not guaranteed travel times.")

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
    st.markdown("#### Possible duplicate reports (review only)")
    matches = find_possible_duplicates(incident, [row for row in center.incidents if row.get("id") != incident.get("id")])
    if matches:
        st.caption("Similarity hints are not proof of duplication. Confirm location and details before linking or resolving any report.")
        st.dataframe(matches, use_container_width=True, hide_index=True)
    else:
        st.caption("No strong duplicate hints found in the current incident snapshot.")
    st.markdown("#### Audit timeline")
    events = [e for e in center.events if incident.get("id") in str(e.get("message", ""))]
    if not events:
        st.info("No incident-specific events yet.")
    for event in events[:30]:
        with st.container(border=True):
            st.caption(f"{event.get('ts') or event.get('time') or ''} · {event.get('category') or 'event'}")
            st.write(event.get("message") or "")
