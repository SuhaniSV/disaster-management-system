from core.duplicate_detection import find_possible_duplicates

def test_detects_nearby_same_type_for_human_review():
    candidate = {"id":"NEW","disaster_type":"Flood","description":"water inside school","lat":18.5164,"lon":73.8567}
    existing = [{"id":"INC-1","disaster_type":"Flood","description":"street flooding","lat":18.517,"lon":73.857,"status":"Active","priority_score":80}]
    matches = find_possible_duplicates(candidate, existing)
    assert matches and matches[0]["incident_id"] == "INC-1"
    assert "nearby" in matches[0]["reason"].lower()

def test_does_not_suggest_resolved_incidents():
    candidate = {"id":"NEW","disaster_type":"Flood","description":"water inside school","lat":18.5164,"lon":73.8567}
    existing = [{"id":"INC-1","disaster_type":"Flood","description":"water inside school","lat":18.5164,"lon":73.8567,"status":"Resolved"}]
    assert find_possible_duplicates(candidate, existing) == []
