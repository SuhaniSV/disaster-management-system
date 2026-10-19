"""Grounded Streamlit response copilot with a deterministic offline fallback."""
from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st

from core.llm_client import LLMClient, llm_configured
from core.state import CommandCenter

SYSTEM_PROMPT = """You are ResQ Assistant, a disaster-response decision-support assistant.
Use only the supplied snapshot, which contains simulated Pune-area demo data, not live feeds.
Do not invent incidents, resource availability, routes, or capacities. Explain but never change priority scores.
Never authorize dispatch or claim to contact responders. A human coordinator must verify facts and decide.
Be concise and calm. Return JSON with one string field named answer."""


def _snapshot(center: CommandCenter) -> dict[str, Any]:
    incidents = sorted(center.incidents, key=lambda row: int(row.get("priority_score") or 0), reverse=True)
    return {
        "data_mode": "SIMULATED DEMO DATA",
        "metrics": center.metrics(),
        "incidents": [{
            key: row.get(key) for key in (
                "id", "disaster_type", "priority_score", "urgency", "status", "people_affected",
                "medical_emergency", "accessibility", "summary", "description", "recommended_action",
                "priority_breakdown",
            )
        } for row in incidents[:30]],
        "assignments": center.assignments[:30],
        "resources": [{key: row.get(key) for key in ("id", "name", "type", "status", "medical_capable")} for row in center.resources],
        "hospitals": [{key: row.get(key) for key in ("id", "name", "available_beds", "total_beds")} for row in center.hospitals],
        "shelters": [{key: row.get(key) for key in ("id", "name", "capacity", "occupied")} for row in center.shelters],
    }


def _fallback(question: str, center: CommandCenter) -> str:
    q = question.lower()
    metrics = center.metrics()
    active = [row for row in center.incidents if str(row.get("status", "")).lower() != "resolved"]
    active.sort(key=lambda row: int(row.get("priority_score") or 0), reverse=True)
    if any(word in q for word in ("shelter", "evacuation centre", "evacuation center")):
        shelters = sorted(center.shelters, key=lambda row: max(0, int(row.get("capacity") or 0) - int(row.get("occupied") or 0)), reverse=True)
        lines = ["Shelter capacity in the simulated dataset:"]
        lines += [f"- **{r.get('name', r.get('id'))}**: {max(0, int(r.get('capacity') or 0)-int(r.get('occupied') or 0))} spaces reported free." for r in shelters[:5]]
        return "\n".join(lines) + "\n\nVerify capacity with local authorities before directing anyone to a shelter."
    if any(word in q for word in ("hospital", "bed", "medical capacity")):
        lines = [f"Reported available hospital beds: **{metrics.get('hospital_beds_available', 0)}**."]
        lines += [f"- **{r.get('name', r.get('id'))}**: {r.get('available_beds', 0)} of {r.get('total_beds', 0)} beds reported available." for r in center.hospitals]
        return "\n".join(lines) + "\n\nThese are simulated figures and must be confirmed directly."
    if any(word in q for word in ("resource", "team", "ambulance", "available unit")):
        rows = [r for r in center.resources if str(r.get("status", "")).lower() == "available"]
        return f"**{len(rows)} resources** are marked available in the demo state.\n" + "\n".join(f"- {r.get('id')}: {r.get('name', r.get('type', 'Resource'))}" for r in rows[:10]) + "\n\nConfirm availability before deployment."
    match = re.search(r"\bINC[- ]?\d+\b", question, re.I)
    if match:
        incident_id = match.group(0).upper().replace(" ", "-")
        row = next((r for r in center.incidents if str(r.get("id", "")).upper() == incident_id), None)
        if row:
            return (f"**{row.get('id')} — {row.get('disaster_type')}**\n\n"
                    f"- Priority: **{row.get('priority_score', 0)}/100 ({row.get('urgency', 'Unknown')})**\n"
                    f"- Status: {row.get('status')}\n- People affected: {row.get('people_affected', 0)}\n"
                    f"- Medical emergency: {row.get('medical_emergency', False)}\n"
                    f"- Access: {row.get('accessibility', 'Unknown')}\n"
                    f"- Recommendation: {row.get('recommended_action', 'Review with coordinator')}\n\n"
                    "The priority is calculated by the deterministic engine; this assistant cannot authorize dispatch.")
        return f"I couldn't find **{incident_id}** in the current demo snapshot."
    if any(word in q for word in ("urgent", "critical", "highest priority", "most important", "top incident", "priorit")) and active:
        row = active[0]
        return (f"**Highest-priority active incident: {row.get('id')} — {row.get('disaster_type')}**\n\n"
                f"- Score: **{row.get('priority_score', 0)}/100 ({row.get('urgency', 'Unknown')})**\n"
                f"- People affected: {row.get('people_affected', 0)}; medical emergency: {row.get('medical_emergency', False)}\n"
                f"- Access: {row.get('accessibility', 'Unknown')}\n"
                f"- Recommendation: {row.get('recommended_action', 'Review with coordinator')}\n\n"
                "This is a deterministic ranking of simulated data, not dispatch authorization.")
    return (f"ResQ-AI reports **{metrics.get('active_incidents', 0)} active incidents**, "
            f"**{metrics.get('critical_incidents', 0)} critical incidents**, "
            f"**{metrics.get('people_affected', 0)} people affected**, and "
            f"**{metrics.get('available_resources', 0)} resources marked available** in simulated data.\n\n"
            "Try: *Which incident is most urgent?*, *Explain INC-001*, *Which shelters have space?*, or *What hospital beds are available?*")


def answer_question(question: str, center: CommandCenter, history: list[dict[str, str]] | None = None) -> str:
    if not llm_configured():
        return _fallback(question, center)
    prompt = json.dumps({
        "snapshot": _snapshot(center),
        "recent_conversation": (history or [])[-8:],
        "latest_question": question,
    }, ensure_ascii=False, default=str)
    try:
        parsed = json.loads(LLMClient().complete_json(SYSTEM_PROMPT, prompt, timeout=20))
        answer = parsed.get("answer") if isinstance(parsed, dict) else None
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
    except Exception:
        pass
    return _fallback(question, center)


def render_chatbot(center: CommandCenter) -> None:
    st.markdown('<div class="resq-kicker">RESQ-AI / RESPONSE COPILOT</div>', unsafe_allow_html=True)
    st.title("ResQ Assistant")
    st.caption("Ask about incidents, deterministic priorities, team availability, hospital beds, and shelter capacity.")
    st.info("Demo mode: answers use simulated Pune-area data. This assistant provides decision support only; it does not authorize dispatch.", icon="ℹ️")
    st.caption("AI provider configured · grounded in the current snapshot" if llm_configured() else "Offline fallback active · no API key required for built-in question patterns")

    history: list[dict[str, str]] = st.session_state.setdefault("resq_chat_messages", [])
    for item in history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    prompt = None
    if not history:
        st.markdown("**Try asking**")
        columns = st.columns(3)
        for column, label, question in zip(columns, ("Highest priority?", "Shelter capacity", "Resource status"),
                                          ("Which incident is most urgent?", "Which shelters have space?", "Which rescue resources are available?")):
            if column.button(label, use_container_width=True):
                prompt = question
    typed = st.chat_input("Ask ResQ about the current response plan…")
    if typed:
        prompt = typed
    if prompt:
        prior = history.copy()
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Checking the current response snapshot…"):
                response = answer_question(prompt, center, prior)
            st.markdown(response)
        history.append({"role": "assistant", "content": response})
        st.session_state.resq_chat_messages = history[-24:]
        st.rerun()
    with st.sidebar:
        st.markdown("### ResQ Assistant")
        st.caption("Read-only incident intelligence")
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.resq_chat_messages = []
            st.rerun()
        st.caption("No dispatch actions are exposed through this chat.")
