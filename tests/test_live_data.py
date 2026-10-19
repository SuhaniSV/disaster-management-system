from core.live_data import _as_rows, _parse_cap_xml, get_ndma_cap_alerts


def test_as_rows_handles_common_api_response_shapes():
    assert _as_rows({"data": [{"district": "Pune"}]}) == [{"district": "Pune"}]
    assert _as_rows([{"warning": "Heavy rain"}, "invalid"]) == [{"warning": "Heavy rain"}]
    assert _as_rows(None) == []


def test_cap_parser_reads_rss_items():
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>Heavy rainfall warning</title>
      <description>District alert</description>
      <link>https://sachet.ndma.gov.in/alert/123</link>
      <pubDate>Mon, 19 Oct 2026 10:00:00 +0530</pubDate>
    </item></channel></rss>"""
    items = _parse_cap_xml(xml)
    assert len(items) == 1
    assert items[0]["title"] == "Heavy rainfall warning"
    assert items[0]["summary"] == "District alert"
    assert items[0]["link"] == "https://sachet.ndma.gov.in/alert/123"


def test_cap_parser_reads_single_cap_alert():
    xml = b"""<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
    <info><event>Flood</event><headline>Flash flood warning</headline>
    <description>Move away from riverbanks.</description><web>https://sachet.ndma.gov.in/</web></info>
    <sent>2026-10-19T10:00:00+05:30</sent></alert>"""
    items = _parse_cap_xml(xml)
    assert len(items) == 1
    assert items[0]["title"] == "Flash flood warning"
    assert items[0]["summary"] == "Move away from riverbanks."


def test_ndma_requires_confirmed_feed_url_and_does_not_guess():
    result = get_ndma_cap_alerts()
    assert result["configured"] is False
    assert result["ok"] is False
    assert result["alerts"] == []
