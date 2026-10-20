from core.ai_engine import fallback_analyze


def test_common_earthquake_misspelling_is_classified():
    result = fallback_analyze("earthqauke damaged several buildings")
    assert result["disaster_type"] == "Earthquake"
