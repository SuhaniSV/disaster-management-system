from core.ai_engine import fallback_analyze, analyze_incident
from utils.validation import validate_report


def test_school_flood_fallback():
    text = (
        "Flood water has entered a school. Around 70 students are trapped and two people "
        "require medical assistance. The main road is blocked."
    )
    result = fallback_analyze(text)
    assert result["disaster_type"] == "Flood"
    assert result["people_affected"] == 70
    assert result["medical_emergency"] is True
    assert result["accessibility"] == "Blocked"
    assert result["severity"] >= 4
    assert result["urgency"] in {"High", "Critical"}


def test_analyze_without_api_uses_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = analyze_incident("Fire in a warehouse with 12 workers trapped.", people_hint=12)
    assert result["engine"] == "fallback"
    assert result["disaster_type"] == "Fire"
    assert result["people_affected"] == 12


def test_invalid_report_inputs():
    errors = validate_report("", "nope", 200, 400)
    assert any("description" in e.lower() for e in errors)
    assert any("Latitude" in e for e in errors)
    assert any("Longitude" in e for e in errors)


def test_valid_report_inputs():
    assert validate_report("Flood at school", 70, 18.5, 73.8) == []
