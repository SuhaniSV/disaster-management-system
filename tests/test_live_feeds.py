from datetime import datetime, timezone

import pytest
import requests

from core import live_feeds


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_fetch_usgs_earthquakes_normalizes_live_geojson(monkeypatch):
    payload = {
        "metadata": {"generated": 1_800_000_000_000},
        "features": [
            {
                "id": "us7000test",
                "properties": {
                    "mag": 4.2,
                    "place": "10 km east of Example",
                    "time": 1_800_000_000_000,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000test",
                    "type": "earthquake",
                    "tsunami": 0,
                },
                "geometry": {"coordinates": [72.5, 19.1, 12.3]},
            }
        ],
    }
    calls = {}

    def fake_get(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return FakeResponse(payload)

    monkeypatch.setattr(live_feeds.requests, "get", fake_get)
    result = live_feeds.fetch_usgs_earthquakes(limit=10)

    assert result["data_mode"] == "live"
    assert result["source_url"] == live_feeds.USGS_ALL_DAY_URL
    assert result["event_count"] == 1
    assert result["events"][0]["id"] == "us7000test"
    assert result["events"][0]["magnitude"] == 4.2
    assert result["events"][0]["latitude"] == 19.1
    assert result["events"][0]["longitude"] == 72.5
    assert result["events"][0]["depth_km"] == 12.3
    assert result["fetched_at_utc"]
    assert result["feed_generated_at_utc"]
    assert calls["kwargs"]["timeout"] == live_feeds.REQUEST_TIMEOUT_SECONDS


def test_fetch_usgs_earthquakes_rejects_malformed_payload(monkeypatch):
    monkeypatch.setattr(
        live_feeds.requests,
        "get",
        lambda *args, **kwargs: FakeResponse({"metadata": {}}),
    )
    with pytest.raises(ValueError, match="unexpected GeoJSON"):
        live_feeds.fetch_usgs_earthquakes()


def test_fetch_usgs_earthquakes_skips_invalid_coordinates(monkeypatch):
    monkeypatch.setattr(
        live_feeds.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            {
                "features": [
                    {"properties": {"mag": 2}, "geometry": {"coordinates": ["bad", 2]}},
                    {"properties": {"mag": 3}, "geometry": {"coordinates": [70, 20, 5]}},
                ]
            }
        ),
    )
    result = live_feeds.fetch_usgs_earthquakes()
    assert result["event_count"] == 1
    assert result["events"][0]["latitude"] == 20.0


def test_fetch_usgs_earthquakes_surfaces_http_errors(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(live_feeds.requests, "get", fail)
    with pytest.raises(requests.Timeout):
        live_feeds.fetch_usgs_earthquakes()
