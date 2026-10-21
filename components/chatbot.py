"""Grounded Streamlit response copilot with a deterministic offline fallback."""
from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st

from core.llm_client import LLMClient, llm_configured
from core.state import CommandCenter
from components.voice_assistant import voice_assistant

SYSTEM_PROMPT = """You are ResQ Assistant, a disaster-response decision-support assistant.
Use the supplied snapshot only for operational incident/resource facts; it is not a live government alert feed.
For general safety questions, provide concise, conservative preparedness guidance and link official sources included in the answer.
Never invent incidents, resource availability, routes, capacities, or current warnings. Explain but never change deterministic priority scores.
Never authorize dispatch or claim to contact responders. Direct people to local emergency services and official local instructions for immediate danger.
Be concise and calm. Return JSON with one string field named answer."""


def _snapshot(center: CommandCenter) -> dict[str, Any]:
    incidents = sorted(center.incidents, key=lambda row: int(row.get("priority_score") or 0), reverse=True)
    return {
        "data_mode": "Current command-center records; not a live government-alert feed",
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


def _safety_guidance(question: str) -> str | None:
    """Conservative general safety guidance with links to official public sources."""
    q = question.casefold()
    if any(word in q for word in ("earthquake", "earth quake", "tremor", "aftershock")):
        return (
            "**Earthquake safety**\n\n"
            "- If shaking starts indoors: **Drop, Cover, and Hold On**; protect your head and neck and stay away from windows. "
            "Do not use elevators.\n"
            "- If outdoors: move away from buildings, walls, trees, and power lines; protect yourself from falling debris.\n"
            "- After shaking: expect aftershocks, check for injuries only when safe, leave visibly damaged buildings, and avoid downed wires. "
            "Do not re-enter a damaged structure until authorities say it is safe.\n\n"
            "Official guidance: [USGS earthquake safety](https://www.usgs.gov/programs/earthquake-hazards) · "
            "[India NDMA](https://ndma.gov.in/)\n\n"
            "This is general guidance, not a location-specific warning. Follow local emergency instructions."
        )
    if any(word in q for word in ("flood", "flash flood", "floodwater", "waterlogging")):
        return (
            "**Flood safety**\n\n"
            "- Move to higher ground early if flooding threatens; follow official evacuation instructions.\n"
            "- Never walk, swim, or drive through floodwater. Water depth and road damage can be deceptive.\n"
            "- Keep away from drains, riverbanks, and fallen power lines. If safe, switch off electricity before water reaches equipment.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[Ready.gov flood safety](https://www.ready.gov/floods)\n\n"
            "Check local authority alerts for current routes and evacuation orders; this assistant cannot verify road conditions."
        )
    if any(word in q for word in ("cyclone", "hurricane", "typhoon", "severe storm", "strong wind")):
        return (
            "**Cyclone and severe-storm safety**\n\n"
            "- Follow official warnings and evacuate when instructed; do not wait for visible conditions to worsen.\n"
            "- Shelter in a sturdy building, away from windows; secure loose outdoor items only if it is safe to do so.\n"
            "- Avoid beaches, flood-prone areas, and downed wires. Do not go outside during a lull unless officials confirm the danger has passed.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[India Meteorological Department](https://mausam.imd.gov.in/)\n\n"
            "Use IMD and local-authority updates for current warnings; this answer is not a live forecast."
        )
    if any(word in q for word in ("fire", "wildfire", "smoke", "building burning")):
        return (
            "**Fire and smoke safety**\n\n"
            "- Leave immediately using the safest available exit; stay low under smoke and do not use elevators.\n"
            "- Once outside, stay outside and call local emergency services. Do not re-enter to retrieve belongings.\n"
            "- If trapped, close doors between you and smoke, signal from a window if safe, and follow dispatcher instructions.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[Ready.gov](https://www.ready.gov/)\n\n"
            "If there is an active fire or immediate danger, contact emergency services now."
        )
    if any(word in q for word in ("heatwave", "heat wave", "extreme heat", "heat stroke", "hot weather")):
        return (
            "**Extreme-heat safety**\n\n"
            "- Move to a cool or shaded place, reduce exertion, and drink water regularly if the person is conscious and able to swallow.\n"
            "- Check on older adults, young children, and people working outdoors. Never leave a person or child in a parked vehicle.\n"
            "- Confusion, fainting, seizures, or very hot skin can indicate a life-threatening emergency: seek urgent medical help and follow dispatcher guidance.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[India Meteorological Department](https://mausam.imd.gov.in/)\n\n"
            "This is general preparedness guidance, not a diagnosis or a current local heat alert."
        )
    if any(phrase in q for phrase in (
        "emergency number", "call emergency", "immediate danger", "urgent help",
        "call an ambulance", "need an ambulance", "send an ambulance",
        "someone is injured", "person is injured", "medical emergency",
        "call the police", "call police", "call fire brigade", "need emergency help",
    )):
        return (
            "**If someone is in immediate danger**\n\n"
            "- Contact local emergency services and give the exact location, hazard, injuries, and any immediate access risks.\n"
            "- In India, **112** is the pan-India emergency response number: [official 112 portal](https://112.gov.in/). "
            "If you are elsewhere, use your local emergency number.\n"
            "- Do not enter an unsafe area or delay calling for help to use this chatbot. ResQ Assistant cannot call responders or dispatch resources."
        )
    if any(word in q for word in ("safety advice", "prepare for disaster", "emergency kit", "preparedness", "go bag")):
        return (
            "**Basic disaster preparedness**\n\n"
            "- Keep drinking water, essential medicines, a first-aid kit, a torch, batteries/power bank, important documents, and emergency contacts ready.\n"
            "- Agree on a family meeting point and out-of-area contact; plan for children, older adults, disabilities, and pets.\n"
            "- Monitor official local alerts and know your evacuation route and nearest designated shelter before an emergency.\n\n"
            "Official guidance: [India NDMA](https://ndma.gov.in/) · "
            "[National Institute of Disaster Management](https://nidm.gov.in/)\n\n"
            "Shelter availability, routes, and warnings must be confirmed with local authorities; ResQ does not currently verify them in this chat."
        )
    return None


def _fallback(question: str, center: CommandCenter) -> str:
    q = question.lower()
    guidance = _safety_guidance(question)
    if guidance:
        return guidance
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
    # Safety-critical, well-defined guidance must not depend on LLM availability or output.
    # Keep these known hazard answers deterministic even when an AI provider is configured.
    guidance = _safety_guidance(question)
    if guidance:
        return guidance

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
    st.caption("Ask about incident priorities, operational records, or general disaster-safety guidance with official source links.")
    st.info("Operational records may be incomplete and are not a live government-alert feed. General safety answers link to official guidance; this assistant cannot verify local warnings, call responders, or authorize dispatch.", icon="ℹ️")
    st.caption("AI provider configured · grounded in the current snapshot" if llm_configured() else "Offline fallback active · no API key required for built-in question patterns")

    history: list[dict[str, str]] = st.session_state.setdefault("resq_chat_messages", [])
    prompt = None

    voice_result = voice_assistant(
        response_text=st.session_state.get("resq_voice_response", ""),
        response_id=st.session_state.get("resq_voice_response_id", 0),
    )
    if isinstance(voice_result, dict) and voice_result.get("text"):
        voice_id = str(voice_result.get("id", ""))
        if voice_id and voice_id != st.session_state.get("resq_last_voice_id"):
            st.session_state["resq_last_voice_id"] = voice_id
            prompt = str(voice_result["text"]).strip()

    for item in history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    if not history:
        st.markdown("**Try asking**")
        columns = st.columns(4)
        for column, label, question in zip(columns, ("Highest priority?", "Shelter capacity", "Resource status", "Earthquake safety"),
                                          ("Which incident is most urgent?", "Which shelters have space?", "Which rescue resources are available?", "What should I do during an earthquake?")):
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
        st.session_state["resq_voice_response"] = response
        st.session_state["resq_voice_response_id"] = int(
            st.session_state.get("resq_voice_response_id", 0)
        ) + 1
        st.rerun()
    with st.sidebar:
        st.markdown("### ResQ Assistant")
        st.caption("Read-only incident intelligence")
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.resq_chat_messages = []
            st.rerun()
        st.caption("No dispatch actions are exposed through this chat.")
