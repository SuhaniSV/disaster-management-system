from __future__ import annotations

import core.gdacs_data as gdacs_data


def test_gdacs_fetch_normalizes_official_event_records(monkeypatch):
    gdacs_data._cache.clear()

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "type": "FeatureCollection",
                "features": [
                    {
                        "properties": {
                            "eventid": 123,
                            "eventtype": "FL",
                            "name": "Flood event",
                            "alertlevel": "Orange",
                            "fromdate": "2026-10-20T00:00:00Z",
                            "todate": "2026-10-22T00:00:00Z",
                            "country": "India",
                        },
                        "geometry": {"type": "Point", "coordinates": [77.2, 28.6]},
                    }
                ],
            }

    calls = {}

    def fake_get(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(gdacs_data.requests, "get", fake_get)

    result = gdacs_data.get_gdacs_events()

    assert result["ok"] is True
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert event["title"] == "Flood event"
    assert event["country"] == "India"
    assert event["alertlevel"] == "Orange"
    assert event["latitude"] == 28.6
    assert event["longitude"] == 77.2
    assert event["link"].startswith("https://www.gdacs.org/")
    assert calls["url"] == gdacs_data.GDACS_API_URL
    assert "fromdate" in calls["kwargs"]["params"]
    assert "todate" in calls["kwargs"]["params"]
    assert "Authorization" not in calls["kwargs"]["headers"]

    gdacs_data._cache.clear()


def test_gdacs_failure_returns_empty_data_not_fake_events(monkeypatch):
    gdacs_data._cache.clear()

    def fake_get(*args, **kwargs):
        raise gdacs_data.requests.Timeout()

    monkeypatch.setattr(gdacs_data.requests, "get", fake_get)

    result = gdacs_data.get_gdacs_events()

    assert result["ok"] is False
    assert result["events"] == []
    assert result["error"] == "GDACS feed unavailable: Timeout"

    gdacs_data._cache.clear()
