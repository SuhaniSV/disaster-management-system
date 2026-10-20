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


def test_empty_resource_inventory_explains_unassigned_reason():
    incident = {
        "id": "INC-EMPTY",
        "disaster_type": "Earthquake",
        "priority_score": 99,
        "people_affected": 120_000,
        "medical_emergency": False,
        "status": "Active",
        "lat": 18.5,
        "lon": 73.8,
    }
    result = assign_resources([incident], [])
    assert result[0]["resource_id"] is None
    assert "No resource inventory is loaded" in result[0]["reason"]


def test_all_resources_unavailable_explains_unassigned_reason():
    incident = {
        "id": "INC-UNAVAILABLE",
        "disaster_type": "Flood",
        "priority_score": 90,
        "people_affected": 20,
        "medical_emergency": False,
        "status": "Active",
        "lat": 18.5,
        "lon": 73.8,
    }
    resource = {
        "id": "R01",
        "name": "Team Alpha",
        "type": "rescue_team",
        "lat": 18.51,
        "lon": 73.81,
        "capacity": 8,
        "status": "Unavailable",
        "capabilities": "flood",
    }
    result = assign_resources([incident], [resource])
    assert result[0]["resource_id"] is None
    assert "No resource is currently marked Available" in result[0]["reason"]


def test_never_assigns_a_suitable_team_thousands_of_kilometres_away():
    incident = {
        "id": "INC-FAR",
        "disaster_type": "Flood",
        "priority_score": 99,
        "people_affected": 20,
        "medical_emergency": False,
        "status": "Active",
        "lat": 18.5204,
        "lon": 73.8567,
    }
    far_team = {
        "id": "R-FAR",
        "name": "Far-away rescue team",
        "type": "rescue_team",
        "lat": 0.0,
        "lon": 0.0,
        "capacity": 8,
        "status": "Available",
        "capabilities": "flood",
    }
    result = assign_resources([incident], [far_team])
    assert result[0]["resource_id"] is None
    assert result[0]["distance_km"] is None
    assert "No suitable available resource is within 100 km" in result[0]["reason"]
    assert "No distant team was assigned" in result[0]["reason"]


def test_nearest_eligible_team_is_preferred_over_farther_team():
    incident = {
        "id": "INC-NEAR",
        "disaster_type": "Flood",
        "priority_score": 90,
        "people_affected": 20,
        "medical_emergency": False,
        "status": "Active",
        "lat": 18.5204,
        "lon": 73.8567,
    }
    near = {
        "id": "R-NEAR",
        "name": "Nearby rescue team",
        "type": "rescue_team",
        "lat": 18.5210,
        "lon": 73.8570,
        "capacity": 8,
        "status": "Available",
        "capabilities": "flood",
    }
    far = {
        "id": "R-FAR",
        "name": "Farther rescue team",
        "type": "rescue_team",
        "lat": 18.60,
        "lon": 73.90,
        "capacity": 8,
        "status": "Available",
        "capabilities": "flood",
    }
    result = assign_resources([incident], [far, near])
    assert result[0]["resource_id"] == "R-NEAR"
    assert result[0]["distance_km"] < 1
