"""Deterministic, review-only duplicate incident hints (never auto-merges reports)."""
from __future__ import annotations
import re
from typing import Any
from core.geo import haversine_km

_STOP = {"the","a","an","and","or","of","to","in","at","is","are","was","were","with","for","on","near","about","people","person","reported","incident","help","urgent"}

def _tokens(row: dict[str, Any]) -> set[str]:
    text = " ".join(str(row.get(key) or "") for key in ("disaster_type","summary","description","accessibility"))
    return {word for word in re.findall(r"[a-z0-9]+", text.casefold()) if len(word) > 2 and word not in _STOP}

def find_possible_duplicates(candidate: dict[str, Any], incidents: list[dict[str, Any]], max_distance_km: float = 5.0, limit: int = 5) -> list[dict[str, Any]]:
    """Rank similar open incidents for human review. Candidate may not be in incidents."""
    cand_tokens = _tokens(candidate)
    results = []
    for existing in incidents:
        if str(existing.get("id") or "") == str(candidate.get("id") or ""):
            continue
        if str(existing.get("status") or "").casefold() == "resolved":
            continue
        try:
            distance = haversine_km(candidate.get("lat"), candidate.get("lon"), existing.get("lat"), existing.get("lon"))
        except (TypeError, ValueError):
            distance = float("inf")
        other = _tokens(existing)
        union = cand_tokens | other
        similarity = len(cand_tokens & other) / len(union) if union else 0.0
        same_type = str(candidate.get("disaster_type") or "").casefold() == str(existing.get("disaster_type") or "").casefold()
        nearby = distance <= max_distance_km
        if similarity >= 0.25 or (same_type and nearby):
            score = max(similarity, 0.45 if same_type and nearby else 0.0)
            results.append({"incident_id": existing.get("id"), "disaster_type": existing.get("disaster_type"),
                            "status": existing.get("workflow_status") or existing.get("status"),
                            "priority_score": int(existing.get("priority_score") or 0),
                            "distance_km": round(distance, 2) if distance != float("inf") else None,
                            "text_similarity": round(similarity, 3), "review_score": round(score, 3),
                            "reason": "Same type and nearby" if same_type and nearby else "Description/type overlap"})
    results.sort(key=lambda row: (row["review_score"], row["priority_score"]), reverse=True)
    return results[:max(0, min(int(limit), 20))]
