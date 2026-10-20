from core.priority import calculate_priority


def test_high_priority_school_flood():
    incident = {
        "severity": 5,
        "people_affected": 70,
        "medical_emergency": True,
        "vulnerable_population": 70,
        "accessibility": "Blocked",
        "status": "Active",
        "reported_at": "2026-08-21T10:00:00+00:00",
    }
    result = calculate_priority(incident)
    assert result["score"] >= 85
    assert result["urgency"] == "Critical"
    labels = {c["label"]: c["points"] for c in result["components"]}
    assert labels["Severity"] == 30
    assert labels["People affected"] == 20
    assert labels["Medical emergency"] == 20
    assert labels["Accessibility risk"] == 10
    assert sum(c["points"] for c in result["components"]) == result["score"] or result["score"] == 100


def test_resolved_is_zero():
    result = calculate_priority({"status": "Resolved", "severity": 5, "people_affected": 90})
    assert result["score"] == 0
    assert result["urgency"] == "Resolved"


def test_not_random_and_monotonic_people():
    low = calculate_priority({"severity": 2, "people_affected": 5, "medical_emergency": False, "status": "Active"})
    high = calculate_priority({"severity": 2, "people_affected": 80, "medical_emergency": False, "status": "Active"})
    assert high["score"] > low["score"]


def test_mass_casualty_scale_for_large_reported_impact():
    result = calculate_priority({
        "severity": 3,
        "people_affected": 120_000,
        "medical_emergency": False,
        "status": "Active",
    })
    labels = {c["label"]: c["points"] for c in result["components"]}
    assert labels["People affected"] == 75
    assert result["urgency"] == "Critical"
    assert result["score"] >= 85



def test_nearly_one_thousand_affected_gets_high_impact_weight():
    result = calculate_priority({
        "severity": 4,
        "people_affected": 987,
        "medical_emergency": False,
        "status": "Active",
    })
    labels = {c["label"]: c["points"] for c in result["components"]}
    assert labels["People affected"] == 46
    assert result["score"] >= 70
    assert result["urgency"] == "High"


def test_people_impact_points_do_not_drop_at_tier_boundaries():
    populations = [70, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000]
    points = []
    for people in populations:
        result = calculate_priority({
            "severity": 1,
            "people_affected": people,
            "medical_emergency": False,
            "status": "Active",
        })
        points.append(next(c["points"] for c in result["components"] if c["label"] == "People affected"))
    assert points == sorted(points)
