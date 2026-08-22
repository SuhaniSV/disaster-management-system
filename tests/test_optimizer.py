from core.optimizer import assign_resources


def test_assigns_medical_resource_to_medical_incident():
    incidents = [
        {
            "id": "INC-004",
            "disaster_type": "Flood",
            "priority_score": 96,
            "people_affected": 70,
            "medical_emergency": True,
            "status": "Active",
            "lat": 18.5164,
            "lon": 73.8567,
        }
    ]
    resources = [
        {
            "id": "R01",
            "name": "Rescue Team",
            "type": "rescue_team",
            "lat": 18.53,
            "lon": 73.86,
            "capacity": 10,
            "status": "Available",
            "capabilities": "flood",
        },
        {
            "id": "R04",
            "name": "Medical Rescue Team R04",
            "type": "medical_rescue",
            "lat": 18.52,
            "lon": 73.86,
            "capacity": 8,
            "status": "Available",
            "capabilities": "medical,flood",
        },
    ]
    result = assign_resources(incidents, resources, roads=[], hospitals=[], shelters=[])
    assert result[0]["resource_id"] == "R04"


def test_reassign_when_resource_unavailable():
    incident = {
        "id": "INC-007",
        "disaster_type": "Flood",
        "priority_score": 90,
        "people_affected": 40,
        "medical_emergency": True,
        "status": "Active",
        "lat": 18.5074,
        "lon": 73.8077,
    }
    r03 = {
        "id": "R03",
        "name": "Team Charlie",
        "type": "medical_rescue",
        "lat": 18.508,
        "lon": 73.81,
        "capacity": 8,
        "status": "Available",
        "capabilities": "medical,flood",
    }
    r01 = {
        "id": "R01",
        "name": "Team Alpha",
        "type": "medical_rescue",
        "lat": 18.54,
        "lon": 73.84,
        "capacity": 8,
        "status": "Available",
        "capabilities": "medical,flood",
    }
    first = assign_resources([incident], [r03, r01])
    assert first[0]["resource_id"] == "R03"
    r03 = {**r03, "status": "Unavailable"}
    second = assign_resources([incident], [r03, r01])
    assert second[0]["resource_id"] == "R01"


def test_empty_resources_does_not_crash():
    incidents = [
        {
            "id": "INC-001",
            "disaster_type": "Fire",
            "priority_score": 80,
            "people_affected": 10,
            "medical_emergency": False,
            "status": "Active",
            "lat": 18.5,
            "lon": 73.8,
        }
    ]
    result = assign_resources(incidents, [])
    assert result[0]["resource_id"] is None
