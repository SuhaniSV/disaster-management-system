from core import alert_translation


def test_english_text_keeps_english_unchanged():
    assert alert_translation.english_text("Flash Flood risk is likely") == "Flash Flood risk is likely"


def test_regional_text_uses_english_translation(monkeypatch):
    monkeypatch.setattr(alert_translation, "_translate_cached", lambda text: "Heavy rain is likely")
    assert alert_translation.english_text("മഴ") == "Heavy rain is likely"


def test_english_record_translates_text_and_preserves_source_metadata(monkeypatch):
    monkeypatch.setattr(alert_translation, "_translate_cached", lambda text: "Thunderstorm warning")
    row = {
        "title": "వర్ష హెచ్చరిక",
        "summary": "వర్షం పడే అవకాశం",
        "link": "https://example.gov/alert/1",
        "published": "Wed, 21 Oct 2026 08:53:43 GMT",
        "source": "NDMA SACHET CAP feed",
    }
    translated = alert_translation.english_record(row)
    assert translated["title"] == "Thunderstorm warning"
    assert translated["summary"] == "Thunderstorm warning"
    assert translated["link"] == row["link"]
    assert translated["published"] == row["published"]
    assert translated["source"] == row["source"]


def test_translation_failure_returns_empty_text_for_ui_to_omit(monkeypatch):
    monkeypatch.setattr(alert_translation, "_translate_cached", lambda text: "")
    assert alert_translation.english_text("മഴ") == ""
