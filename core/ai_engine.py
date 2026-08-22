"""Incident NLP: LLM extraction with deterministic keyword fallback."""

from __future__ import annotations

import json
import re
from typing import Any

from core.llm_client import LLMClient, llm_configured
from utils.validation import as_bool, as_int


DISASTER_KEYWORDS = {
    "Flood": ["flood", "inundat", "water has entered", "submerged", "overflow", "waterlogging"],
    "Fire": ["fire", "blaze", "burn", "smoke", "flames"],
    "Earthquake": ["earthquake", "tremor", "seismic", "aftershock"],
    "Building Collapse": ["collapse", "collapsed", "rubble", "debris of building", "building fell"],
    "Landslide": ["landslide", "mudslide", "slope failure"],
    "Cyclone": ["cyclone", "hurricane", "storm surge", "typhoon"],
    "Medical Emergency": ["cardiac", "outbreak", "epidemic", "mass casualty", "multiple injured"],
    "Road Accident": ["accident", "collision", "pile-up", "bus crash", "vehicle"],
    "Gas Leak": ["gas leak", "chemical leak", "chlorine", "toxic gas"],
}

MEDICAL_TERMS = [
    "medical",
    "injured",
    "injury",
    "ambulance",
    "bleeding",
    "unconscious",
    "fracture",
    "require medical",
    "requires medical",
    "casualt",
    "burn",
    "trauma",
    "pregnant",
    "critical condition",
]

BLOCKED_TERMS = ["blocked", "inaccessible", "cut off", "road is closed", "main road is blocked", "no access"]
RESTRICTED_TERMS = ["debris", "partially blocked", "slow access", "congested", "one-way only"]
VULN_TERMS = ["student", "child", "children", "school", "elderly", "old age", "pregnant", "disabled", "orphan"]

REQUIRED_FIELDS = {
    "disaster_type",
    "severity",
    "people_affected",
    "medical_emergency",
    "accessibility",
    "urgency",
}


SYSTEM_PROMPT = """You extract structured facts from an emergency report for a decision-support prototype.
You do NOT assign specific rescue units and you do NOT make a final operational decision.
Return JSON only with keys:
disaster_type, severity (1-5 integer), people_affected (integer), medical_emergency (boolean),
accessibility (Open, Restricted, or Blocked), urgency (Low, Medium, High, Critical),
summary (one short sentence), vulnerable_population (integer),
recommended_resource_type (one of: rescue_team, medical_rescue, ambulance, fire_response).
Use only evidence in the report. If unknown, make a conservative estimate and keep severity honest.
"""


def _clean_json_text(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
        text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _normalize(result: dict[str, Any], fallback_people: int | None = None) -> dict[str, Any]:
    disaster = str(result.get("disaster_type") or "Unknown").strip().title()
    if disaster.lower() == "unknown":
        disaster = "Unknown"
    severity = max(1, min(5, as_int(result.get("severity"), 3)))
    people = as_int(result.get("people_affected"), fallback_people if fallback_people is not None else 0)
    people = max(0, people)
    medical = as_bool(result.get("medical_emergency"))
    access = str(result.get("accessibility") or "Open").strip().title()
    if access not in {"Open", "Restricted", "Blocked"}:
        access = "Open"
    urgency = str(result.get("urgency") or "").strip().title()
    if urgency not in {"Low", "Medium", "High", "Critical"}:
        if severity >= 5 or (medical and people >= 20):
            urgency = "Critical"
        elif severity >= 4:
            urgency = "High"
        elif severity >= 3:
            urgency = "Medium"
        else:
            urgency = "Low"
    rtype = str(result.get("recommended_resource_type") or "").strip().lower()
    if rtype not in {"rescue_team", "medical_rescue", "ambulance", "fire_response"}:
        if "fire" in disaster.lower():
            rtype = "fire_response"
        elif medical:
            rtype = "medical_rescue"
        else:
            rtype = "rescue_team"
    summary = str(result.get("summary") or "").strip()
    if not summary:
        summary = f"{disaster} incident affecting {people} people."
    vuln = as_int(result.get("vulnerable_population"), 0)
    return {
        "disaster_type": disaster,
        "severity": severity,
        "people_affected": people,
        "medical_emergency": medical,
        "accessibility": access,
        "urgency": urgency,
        "summary": summary,
        "vulnerable_population": max(0, vuln),
        "recommended_resource_type": rtype,
    }


def fallback_analyze(
    description: str,
    people_hint: int | None = None,
    accessibility_hint: str | None = None,
) -> dict[str, Any]:
    text = (description or "").lower()
    disaster = "Unknown"
    hits = 0
    for label, words in DISASTER_KEYWORDS.items():
        count = sum(1 for w in words if w in text)
        if count > hits:
            hits = count
            disaster = label

    people = people_hint if people_hint is not None else 0
    if not people:
        match = re.search(
            r"(\d+)\s+(?:students|people|persons|residents|families|villagers|workers|children|injured)",
            text,
        )
        if match:
            people = int(match.group(1))
        else:
            match = re.search(r"around\s+(\d+)|approximately\s+(\d+)|about\s+(\d+)", text)
            if match:
                people = int(next(g for g in match.groups() if g))

    medical = any(term in text for term in MEDICAL_TERMS)
    if accessibility_hint:
        access = accessibility_hint.title()
        if access not in {"Open", "Restricted", "Blocked"}:
            access = "Open"
    elif any(term in text for term in BLOCKED_TERMS):
        access = "Blocked"
    elif any(term in text for term in RESTRICTED_TERMS):
        access = "Restricted"
    else:
        access = "Open"

    vuln = 0
    if any(term in text for term in VULN_TERMS):
        vuln = people if people else 10
        if "student" in text or "school" in text:
            vuln = max(vuln, people)

    severity = 3
    if any(w in text for w in ("trapped", "collapse", "critical", "urgent", "life-threatening")):
        severity = 5
    elif medical or people >= 50:
        severity = 4
    elif people >= 20:
        severity = 4 if access == "Blocked" else 3
    if disaster == "Fire" and "school" in text:
        severity = max(severity, 5)
    if access == "Blocked":
        severity = max(severity, 4)
    if disaster == "Unknown":
        severity = max(2, severity - 1)

    result = {
        "disaster_type": disaster,
        "severity": severity,
        "people_affected": people,
        "medical_emergency": medical,
        "accessibility": access,
        "vulnerable_population": vuln,
        "summary": (description or "").strip()[:220] or f"{disaster} report",
        "recommended_resource_type": None,
        "urgency": None,
    }
    return _normalize(result, fallback_people=people)


def analyze_incident(
    description: str,
    people_hint: int | None = None,
    accessibility_hint: str | None = None,
) -> dict[str, Any]:
    """Return structured analysis plus metadata about which engine was used."""
    fallback = fallback_analyze(description, people_hint, accessibility_hint)
    if people_hint is not None and fallback["people_affected"] == 0:
        fallback["people_affected"] = max(0, people_hint)

    if not llm_configured():
        fallback["engine"] = "fallback"
        fallback["ai_mode"] = "Fallback Analysis Mode"
        return fallback

    try:
        client = LLMClient()
        user = (
            f"Report:\n{description}\n\n"
            f"Operator people estimate: {people_hint}\n"
            f"Operator accessibility hint: {accessibility_hint}\n"
        )
        raw = client.complete_json(SYSTEM_PROMPT, user)
        parsed = json.loads(_clean_json_text(raw))
        if not isinstance(parsed, dict) or not REQUIRED_FIELDS.issubset(set(parsed)):
            # Safe merge of whatever arrived.
            if not isinstance(parsed, dict):
                raise ValueError("not an object")
            merged = {**fallback, **parsed}
            parsed = merged
        normalized = _normalize(parsed, fallback_people=people_hint)
        if people_hint and normalized["people_affected"] == 0:
            normalized["people_affected"] = people_hint
        if accessibility_hint and normalized["accessibility"] == "Open" and accessibility_hint.title() != "Open":
            # Keep operator-observed access if model omitted it.
            hint = accessibility_hint.title()
            if hint in {"Restricted", "Blocked"}:
                normalized["accessibility"] = hint
        normalized["engine"] = "llm"
        normalized["ai_mode"] = "AI Mode: Active"
        return normalized
    except Exception:
        fallback["engine"] = "fallback"
        fallback["ai_mode"] = "Fallback Analysis Mode"
        return fallback
