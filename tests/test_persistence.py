from core.persistence import incident_record


def test_incident_record_keeps_fields_needed_for_database_and_restore():
    incident = {
        "id": "INC-001",
        "disaster_type": "Flood",
        "description": "Flooding near a school",
        "severity": 4,
        "status": "Active",
        "people_affected": 27,
        "lat": 28.61,
        "lon": 77.21,
        "source": "operator-report",
        "priority_score": 86,
    }
    analysis = {"disaster_type": "Flood", "severity": 4}
    assignment = {"incident_id": "INC-001", "resource_id": None}

    record = incident_record(incident, analysis, assignment)

    assert record["incident_code"] == "INC-001"
    assert record["hazard_type"] == "Flood"
    assert record["location"] == "28.610000, 77.210000"
    assert record["people_affected"] == 27
    assert record["incident_data"] == incident
    assert record["analysis_data"] == analysis
    assert record["assignment_data"] == assignment


def test_incident_record_rejects_missing_id_or_description():
    try:
        incident_record({"description": "A report without an ID"})
    except ValueError as exc:
        assert "ID" in str(exc)
    else:
        raise AssertionError("Expected missing incident ID to be rejected")

    try:
        incident_record({"id": "INC-002", "description": " "})
    except ValueError as exc:
        assert "description" in str(exc)
    else:
        raise AssertionError("Expected empty incident description to be rejected")
