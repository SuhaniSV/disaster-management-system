from resq_mcp.logic import explain_priority, find_shelters, get_incident_details, get_resource_status, list_incidents


class FakeCenter:
    demo_mode = True

    def __init__(self):
        self.incidents = [
            {"id": "INC-001", "disaster_type": "Flood", "priority_score": 91, "urgency": "Critical", "status": "Active", "people_affected": 70, "medical_emergency": True, "vulnerable_population": 10, "accessibility": "Blocked", "summary": "School flood", "recommended_action": "Prioritize medical-capable response", "priority_breakdown": [{"label": "Severity", "points": 30}], "formula_note": "Deterministic score"},
            {"id": "INC-002", "disaster_type": "Fire", "priority_score": 42, "urgency": "Medium", "status": "Resolved", "people_affected": 3, "medical_emergency": False, "priority_breakdown": [], "formula_note": "Deterministic score"},
        ]
        self.resources = [{"id": "R01", "name": "Team One", "type": "rescue_team", "status": "Available", "medical_capable": True}]
        self.hospitals = [{"id": "H01", "name": "Demo Hospital", "available_beds": 4, "total_beds": 20}]
        self.shelters = [{"id": "S01", "name": "Demo Shelter", "capacity": 100, "occupied": 75}]
        self.assignments = [{"incident_id": "INC-001", "resource_id": "R01", "resource_name": "Team One", "hospital_name": "Demo Hospital", "shelter_name": "Demo Shelter", "reason": "Closest eligible team"}]

    def assignment_for(self, incident_id):
        return next((row for row in self.assignments if row["incident_id"] == incident_id), None)

    def metrics(self):
        return {"active_incidents": 1, "critical_incidents": 1, "people_affected": 70, "available_resources": 1, "hospital_beds_available": 4, "shelter_spaces_available": 25}


def test_incident_list_is_priority_sorted_and_active_by_default():
    result = list_incidents(FakeCenter())
    assert result["count"] == 1
    assert result["incidents"][0]["id"] == "INC-001"
    assert result["incidents"][0]["priority_score"] == 91


def test_incident_details_and_explanation_are_grounded_in_deterministic_fields():
    center = FakeCenter()
    details = get_incident_details(center, "inc-001")
    explanation = explain_priority(center, "INC-001")
    assert details["found"] is True
    assert details["incident"]["assignment_recommendation"]["resource_id"] == "R01"
    assert explanation["priority_score"] == 91
    assert explanation["breakdown"] == [{"label": "Severity", "points": 30}]
    assert get_incident_details(center, "INC-999")["found"] is False


def test_shelter_and_resource_capacity_are_reported_without_mutation():
    center = FakeCenter()
    assert find_shelters(center, minimum_spaces=20)["shelters"][0]["spaces_available"] == 25
    status = get_resource_status(center)
    assert status["available_resource_count"] == 1
    assert status["hospital_beds_available"] == 4
    assert status["shelter_spaces_available"] == 25


def test_briefing_falls_back_without_aws_model(monkeypatch):
    from resq_mcp.logic import generate_incident_brief

    monkeypatch.delenv("AWS_BEDROCK_MODEL_ID", raising=False)
    result = generate_incident_brief(FakeCenter())
    assert result["mode"] == "deterministic_fallback"
    assert "Active incidents: 1" in result["brief"]
    assert "does not authorize dispatch" in result["brief"]
