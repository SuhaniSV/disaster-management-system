from core.reporting import incidents_csv, json_report, situation_report_markdown
from core.routing import route_estimate
from core.state import load_demo_disaster

def test_exports_are_labelled_and_parseable():
    center = load_demo_disaster()
    payload = json_report(center)
    assert '"data_mode": "simulated_demo_data"' in payload
    assert "not a dispatch order" in payload.lower()
    assert "id,disaster_type" in incidents_csv(center)
    assert "Situation Report" in situation_report_markdown(center)

def test_route_rejects_invalid_coordinates():
    result = route_estimate(999, 0, 0, 0)
    assert result["ok"] is False
    assert "valid latitude" in result["error"]

def test_route_endpoint_must_use_https(monkeypatch):
    monkeypatch.setenv("RESQ_ROUTING_BASE_URL", "http://127.0.0.1:1234")
    result = route_estimate(18.5, 73.8, 18.6, 73.9)
    assert result["ok"] is False
    assert "HTTPS" in result["error"]
