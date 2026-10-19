from pathlib import Path

def test_professional_typography_and_layout_styles_are_present():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert "DM Sans" in source
    assert "IBM Plex Mono" in source
    assert "stSidebarNav" in source
    assert "prefers-reduced-motion" in source

def test_light_dark_theme_support_remains_available_in_settings():
    theme = Path("components/theme.py").read_text(encoding="utf-8")
    settings = Path("pages/12_Settings.py").read_text(encoding="utf-8")
    assert "DARK_CSS" in theme
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in theme
    assert 'options=["Light", "Dark"]' in settings
    assert 'st.sidebar.selectbox("Appearance"' not in theme
