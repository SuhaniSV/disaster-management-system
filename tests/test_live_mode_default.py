from components.session import load_live_center


def test_live_center_starts_without_simulated_operational_records():
    center = load_live_center()

    assert center.data_mode == "Live Data"
    assert center.demo_mode is False
    assert center.incidents == []
    assert center.resources == []
    assert center.hospitals == []
    assert center.shelters == []
    assert center.roads == []
    assert center.events == []


def test_live_center_does_not_load_demo_counts():
    center = load_live_center()
    metrics = center.metrics()

    assert metrics["active_incidents"] == 0
    assert metrics["available_resources"] == 0
    assert metrics["hospital_beds_available"] == 0
    assert metrics["shelter_spaces_available"] == 0


def test_sidebar_and_settings_offer_explicit_live_and_demo_modes():
    from pathlib import Path

    theme = Path("components/theme.py").read_text(encoding="utf-8")
    settings = Path("pages/12_Settings.py").read_text(encoding="utf-8")
    assert 'st.session_state.get("resq_data_mode", "Live Data")' in theme
    assert '["Live Data", "Demo Mode"]' in theme
    assert '["Live Data", "Demo Mode"]' in settings
    assert "No simulated records" in Path("components/session.py").read_text(encoding="utf-8") or "without sample records" in Path("components/session.py").read_text(encoding="utf-8")
