import requests

from core import gdacs_feed


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_fetch_gdacs_normalizes_multi_hazard_events(monkeypatch):
    payload = {
        "features": [
            {
                "id": "FL-123",
                "properties": {
                    "eventtype": "FL",
                    "eventid": "123",
                    "eventname": "Flood event",
                    "country": "India",
                    "alertlevel": "Orange",
                    "fromdate": "2026-10-18T10:00:00Z",
                    "todate": "2026-10-19T10:00:00Z",
                    "url": "https://www.gdacs.org/report.aspx?eventid=123",
                },
                "geometry": {"type": "Point", "coordinates": [77.2, 28.6]},
            },
            {
                "id": "EQ-456",
                "properties": {
                    "eventtype": "EQ",
                    "eventid": "456",
                    "eventname": "Earthquake event",
                    "country": "Nepal",
                    "alertlevel": "Green",
                },
                "geometry": {"type": "Point", "coordinates": [85.3, 27.7]},
            },
        ]
    }
    calls = {}

    def fake_get(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return FakeResponse(payload)

    monkeypatch.setattr(gdacs_feed.requests, "get", fake_get)
    result = gdacs_feed.fetch_gdacs_events(lookback_days=30, limit=10)

    assert result["data_mode"] == "live"
    assert result["source"] == gdacs_feed.GDACS_SOURCE_NAME
    assert result["event_count"] == 2
    assert result["events"][0]["event_type"] == "Flood"
    assert result["events"][0]["country"] == "India"
    assert result["events"][0]["latitude"] == 28.6
    assert result["events"][0]["longitude"] == 77.2
    assert result["events"][0]["source_url"].startswith("https://")
    assert calls["url"] == gdacs_feed.GDACS_API_URL
    assert calls["kwargs"]["params"]["eventlist"] == "EQ;TC;FL;VO;FF;DR"
    assert calls["kwargs"]["timeout"] == gdacs_feed.REQUEST_TIMEOUT_SECONDS


def test_fetch_gdacs_rejects_malformed_payload(monkeypatch):
    monkeypatch.setattr(gdacs_feed.requests, "get", lambda *args, **kwargs: FakeResponse({"items": []}))
    try:
        gdacs_feed.fetch_gdacs_events()
    except ValueError as exc:
        assert "unexpected GeoJSON" in str(exc)
    else:
        raise AssertionError("Malformed feed should not be treated as live data")


def test_fetch_gdacs_surfaces_network_errors(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(gdacs_feed.requests, "get", fail)
    try:
        gdacs_feed.fetch_gdacs_events()
    except requests.Timeout:
        pass
    else:
        raise AssertionError("Network errors must be surfaced, not replaced with demo records")
