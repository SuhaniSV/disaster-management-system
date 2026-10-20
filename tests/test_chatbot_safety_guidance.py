from core.state import CommandCenter
from components.chatbot import _fallback, _safety_guidance


def _empty_center():
    return CommandCenter(bundle={
        "incidents": [], "resources": [], "hospitals": [],
        "shelters": [], "roads": [], "events": [],
    })


def test_earthquake_guidance_includes_drop_cover_hold_and_official_sources():
    answer = _safety_guidance("What should I do during an earthquake?")
    assert answer is not None
    assert "Drop, Cover, and Hold On" in answer
    assert "usgs.gov" in answer
    assert "ndma.gov.in" in answer


def test_flood_guidance_warns_against_entering_floodwater():
    answer = _safety_guidance("How do I stay safe in a flood?")
    assert answer is not None
    assert "Never walk, swim, or drive through floodwater" in answer
    assert "ready.gov/floods" in answer


def test_emergency_guidance_has_india_112_and_no_dispatch_claim():
    answer = _safety_guidance("What emergency number should I call?")
    assert answer is not None
    assert "112" in answer
    assert "112.gov.in" in answer
    assert "cannot call responders" in answer


def test_general_preparedness_links_official_sources():
    answer = _safety_guidance("What should go in an emergency kit?")
    assert answer is not None
    assert "drinking water" in answer
    assert "ndma.gov.in" in answer


def test_unmatched_question_falls_back_to_operational_snapshot_summary():
    answer = _fallback("Give me a dashboard summary", _empty_center())
    assert "active incidents" in answer
    assert "simulated data" in answer


def test_answer_question_uses_deterministic_safety_guidance_when_llm_is_configured(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    def unexpected_llm_call(*args, **kwargs):
        raise AssertionError("LLM should not be called for built-in safety guidance")

    monkeypatch.setattr(chatbot.LLMClient, "complete_json", unexpected_llm_call)
    answer = chatbot.answer_question("What should I do during an earthquake?", _empty_center())
    assert "Drop, Cover, and Hold On" in answer
    assert "usgs.gov" in answer


def test_answer_question_uses_llm_for_non_guidance_when_configured(monkeypatch):
    import components.chatbot as chatbot

    monkeypatch.setattr(chatbot, "llm_configured", lambda: True)

    class FakeLLMClient:
        def complete_json(self, system, prompt, timeout):
            return '{"answer": "Snapshot-based response"}'

    monkeypatch.setattr(chatbot, "LLMClient", FakeLLMClient)
    answer = chatbot.answer_question("Summarize the response snapshot", _empty_center())
    assert answer == "Snapshot-based response"
