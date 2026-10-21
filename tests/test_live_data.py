
import base64
import time

import core.live_data as live_data
from core.live_data import (
    _active_cap_alerts,
    _as_rows,
    _parse_cap_xml,
    _parse_wis2_cap_items,
    get_ndma_cap_alerts,
)


def test_as_rows_handles_common_api_response_shapes():
    assert _as_rows({"data": [{"district": "Pune"}]}) == [
        {"district": "Pune"}
    ]
    assert _as_rows([{"warning": "Heavy rain"}, "invalid"]) == [
        {"warning": "Heavy rain"}
    ]
    assert _as_rows(None) == []
    assert _as_rows({"data": {"items": [{"district": "Noida"}]}}) == [
        {"district": "Noida"}
    ]


def test_cap_parser_reads_rss_items():
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>Heavy rainfall warning</title>
      <description>District alert</description>
      <link>https://sachet.ndma.gov.in/alert/123</link>
      <pubDate>Mon, 19 Oct 2026 10:00:00 +0530</pubDate>
      <severity>Severe</severity>
      <areaDesc>Example district</areaDesc>
      <expires>2026-10-22T10:00:00Z</expires>
    </item></channel></rss>"""

    items = _parse_cap_xml(xml)

    assert len(items) == 1
    assert items[0]["title"] == "Heavy rainfall warning"
    assert items[0]["summary"] == "District alert"
    assert items[0]["link"] == "https://sachet.ndma.gov.in/alert/123"
    assert items[0]["severity"] == "Severe"
    assert items[0]["area"] == "Example district"
    assert items[0]["expires"] == "2026-10-22T10:00:00Z"


def test_cap_parser_reads_single_cap_alert():
    xml = b"""<?xml version="1.0"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <identifier>test-alert</identifier>
      <sender>official@example.gov</sender>
      <sent>2026-10-19T10:00:00+05:30</sent>
      <status>Actual</status>
      <msgType>Alert</msgType>
      <scope>Public</scope>
      <info>
        <event>Flood</event>
        <headline>Flash flood warning</headline>
        <description>Move away from riverbanks.</description>
        <severity>Severe</severity>
        <expires>2026-10-22T10:00:00+05:30</expires>
        <area>
          <areaDesc>Example district</areaDesc>
        </area>
        <web>https://sachet.ndma.gov.in/</web>
      </info>
    </alert>"""

    items = _parse_cap_xml(xml)

    assert len(items) == 1
    assert items[0]["title"] == "Flash flood warning"
    assert items[0]["summary"] == "Move away from riverbanks."
    assert items[0]["link"] == "https://sachet.ndma.gov.in/"
    assert items[0]["severity"] == "Severe"
    assert items[0]["area"] == "Example district"


def test_active_cap_alerts_excludes_expired_alerts():
    alerts = [
        {
            "title": "Expired warning",
            "expires": "2020-01-01T00:00:00Z",
        },
        {
            "title": "Future warning",
            "expires": "2099-01-01T00:00:00Z",
        },
        {
            "title": "No expiry supplied",
            "expires": "",
        },
    ]

    result = _active_cap_alerts(alerts)

    assert [alert["title"] for alert in result] == [
        "Future warning",
        "No expiry supplied",
    ]


def test_wis2_parser_extracts_active_imd_cap_record():
    cap_xml = b"""<?xml version="1.0"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <identifier>test-alert</identifier>
      <sender>imd@example.gov</sender>
      <sent>2026-10-21T10:00:00+05:30</sent>
      <status>Actual</status>
      <msgType>Alert</msgType>
      <scope>Public</scope>
      <info>
        <event>Heavy Rain</event>
        <headline>Heavy rain warning</headline>
        <description>Official warning</description>
        <severity>Severe</severity>
        <expires>2099-10-22T10:00:00+05:30</expires>
        <area>
          <areaDesc>Example district</areaDesc>
        </area>
      </info>
    </alert>"""

    encoded = base64.b64encode(cap_xml).decode("ascii")

    payload = {
        "features": [
            {
                "properties": {
                    "metadata_id": live_data.IMD_CAP_METADATA_ID,
                    "data_id": "in-imd:cap_alerts/test-alert",
                    "content": {
                        "encoding": "base64",
                        "value": encoded,
                    },
                }
            }
        ]
    }

    alerts, seen = _parse_wis2_cap_items(payload)

    assert seen == 1
    assert len(alerts) == 1
    assert alerts[0]["title"] == "Heavy rain warning"
    assert alerts[0]["severity"] == "Severe"
    assert alerts[0]["area"] == "Example district"
    assert alerts[0]["source"] == "IMD WIS2 CAP feed"


def test_wis2_parser_ignores_unrelated_metadata():
    payload = {
        "features": [
            {
                "properties": {
                    "metadata_id": "unrelated:metadata",
                    "data_id": "unrelated:dataset",
                    "content": {"value": "invalid"},
                }
            }
        ]
    }

    alerts, seen = _parse_wis2_cap_items(payload)

    assert alerts == []
    assert seen == 0


def test_ndma_requires_confirmed_feed_url_and_does_not_guess(monkeypatch):
    monkeypatch.delenv("NDMA_CAP_FEED_URL", raising=False)

    try:
        import streamlit as st

        # A configured Streamlit secret takes precedence over this test's
        # missing environment variable, so only assert missing-feed behavior
        # when the secret is also absent.
        try:
            secret_url = st.secrets.get("NDMA_CAP_FEED_URL", "")
        except Exception:
            secret_url = ""

        if secret_url:
            return
    except ImportError:
        pass

    result = get_ndma_cap_alerts()

    assert result["configured"] is False
    assert result["ok"] is False
    assert result["alerts"] == []
    assert result["fetched_at"] is None


def test_imd_public_cap_fallback_fetches_official_rss(monkeypatch):
    cache_key = "imd-public-cap:" + live_data.IMD_PUBLIC_CAP_URL
    live_data._cache.pop(cache_key, None)

    class FakeResponse:
        status_code = 200
        headers = {"ETag": '"test-etag"'}
        content = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><item>
          <title>IMD weather alert</title>
          <description>Official CAP alert</description>
          <link>https://mausam.imd.gov.in/</link>
          <pubDate>Wed, 21 Oct 2026 10:00:00 GMT</pubDate>
          <expires>2099-10-22T10:00:00Z</expires>
        </item></channel></rss>"""

        def raise_for_status(self):
            return None

    def fake_get(url, *args, **kwargs):
        if url == live_data.IMD_PUBLIC_CAP_URL:
            return FakeResponse()

        raise AssertionError(
            f"Unexpected network request in RSS success test: {url}"
        )

    monkeypatch.setattr(live_data.requests, "get", fake_get)

    try:
        result = live_data.get_imd_public_cap_alerts()

        assert result["ok"] is True
        assert result["rss_ok"] is True
        assert result["alerts"][0]["title"] == "IMD weather alert"
        assert result["alerts"][0]["source"] == "IMD public CAP feed"
        assert result["source_url"] == live_data.IMD_PUBLIC_CAP_URL
    finally:
        live_data._cache.pop(cache_key, None)


def test_imd_public_cap_uses_wis2_when_rss_has_no_active_alerts(
    monkeypatch,
):
    cache_key = "imd-public-cap:" + live_data.IMD_PUBLIC_CAP_URL
    live_data._cache.pop(cache_key, None)

    class FakeResponse:
        def __init__(self, content=b"", payload=None):
            self.status_code = 200
            self.headers = {}
            self.content = content
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    rss_response = FakeResponse(
        content=b"""<rss version="2.0"><channel></channel></rss>"""
    )

    wis2_payload = {"features": []}
    wis2_response = FakeResponse(payload=wis2_payload)

    def fake_get(url, *args, **kwargs):
        if url == live_data.IMD_PUBLIC_CAP_URL:
            return rss_response
        if url == live_data.IMD_WIS2_CAP_URL:
            return wis2_response

        raise AssertionError(f"Unexpected network request: {url}")

    monkeypatch.setattr(live_data.requests, "get", fake_get)

    try:
        result = live_data.get_imd_public_cap_alerts()

        assert result["rss_ok"] is True
        assert result["wis2_ok"] is True
        assert result["ok"] is True
        assert result["alerts"] == []
        assert result["source_url"] == live_data.IMD_WIS2_CAP_URL
    finally:
        live_data._cache.pop(cache_key, None)


def test_imd_public_cap_cache_returns_cached_result(monkeypatch):
    cache_key = "imd-public-cap:" + live_data.IMD_PUBLIC_CAP_URL
    live_data._cache.pop(cache_key, None)

    class FakeResponse:
        status_code = 200
        headers = {}
        content = b"""<rss version="2.0"><channel><item>
        <title>Cached test alert</title>
        <description>Test</description>
        <expires>2099-10-22T10:00:00Z</expires>
        </item></channel></rss>"""

        def raise_for_status(self):
            return None

    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse()

    monkeypatch.setattr(live_data.requests, "get", fake_get)

    try:
        first = live_data.get_imd_public_cap_alerts()
        second = live_data.get_imd_public_cap_alerts()

        assert first["cached"] is False
        assert second["cached"] is True
        assert second["alerts"][0]["title"] == "Cached test alert"
        assert calls["count"] == 1
    finally:
        live_data._cache.pop(cache_key, None)


def test_usgs_india_earthquake_feed_filters_by_coordinates(monkeypatch):
    cache_key = "usgs-india-earthquakes:" + live_data.USGS_EARTHQUAKE_FEED_URL
    live_data._cache.pop(cache_key, None)

    class FakeResponse:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "features": [
                    {
                        "properties": {
                            "title": "M 4.2 - 20 km north of Delhi, India",
                            "place": "20 km north of Delhi, India",
                            "mag": 4.2,
                            "time": 1792576800000,
                            "url": "https://earthquake.usgs.gov/example",
                        },
                        "geometry": {"coordinates": [77.2, 28.6, 10.0]},
                    },
                    {
                        "properties": {"title": "Outside India-region bounds", "mag": 5.0},
                        "geometry": {"coordinates": [-118.2, 34.0, 8.0]},
                    },
                ]
            }

    def fake_get(url, *args, **kwargs):
        assert url == live_data.USGS_EARTHQUAKE_FEED_URL
        return FakeResponse()

    monkeypatch.setattr(live_data.requests, "get", fake_get)

    try:
        result = live_data.get_usgs_india_earthquakes()
        assert result["ok"] is True
        assert result["records_seen"] == 2
        assert len(result["events"]) == 1
        assert result["events"][0]["magnitude"] == 4.2
        assert result["events"][0]["latitude"] == 28.6
    finally:
        live_data._cache.pop(cache_key, None)

def test_wis2_parser_accepts_root_level_metadata_and_nested_items():
    cap_xml = b"""<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <info><event>Heavy Rain</event><headline>Test CAP alert</headline>
      <expires>2099-01-01T00:00:00Z</expires></info>
    </alert>"""
    encoded = base64.b64encode(cap_xml).decode("ascii")
    payload = {
        "items": {
            "features": [
                {
                    "metadataId": live_data.IMD_CAP_METADATA_ID,
                    "dataId": "in-imd:cap_alerts/test-root-level",
                    "content": {"encoding": "base64", "value": encoded},
                }
            ]
        }
    }

    alerts, seen = _parse_wis2_cap_items(payload)

    assert seen == 1
    assert len(alerts) == 1
    assert alerts[0]["title"] == "Test CAP alert"




def test_wis2_parser_accepts_literal_xml_when_encoding_is_missing():
    cap_xml = """<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <info><event>Heavy Rain</event><headline>Literal XML warning</headline>
      <expires>2099-01-01T00:00:00Z</expires></info>
    </alert>"""
    payload = {
        "features": [
            {
                "properties": {
                    "metadata_id": live_data.IMD_CAP_METADATA_ID,
                    "data_id": "in-imd:cap_alerts/literal-xml",
                    "content": {"value": cap_xml},
                }
            }
        ]
    }

    alerts, seen = _parse_wis2_cap_items(payload)

    assert seen == 1
    assert len(alerts) == 1
    assert alerts[0]["title"] == "Literal XML warning"


def test_wis2_parser_accepts_base64_when_encoding_is_missing():
    cap_xml = b"""<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <info><event>Flood</event><headline>Encoded warning</headline>
      <expires>2099-01-01T00:00:00Z</expires></info>
    </alert>"""
    payload = {
        "features": [
            {
                "properties": {
                    "metadata_id": live_data.IMD_CAP_METADATA_ID,
                    "data_id": "in-imd:cap_alerts/base64-no-encoding",
                    "content": {"value": base64.b64encode(cap_xml).decode("ascii")},
                }
            }
        ]
    }

    alerts, seen = _parse_wis2_cap_items(payload)

    assert seen == 1
    assert len(alerts) == 1
    assert alerts[0]["title"] == "Encoded warning"
