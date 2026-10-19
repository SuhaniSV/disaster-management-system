from pathlib import Path

def test_professional_typography_and_layout_styles_are_present():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert "DM Sans" in source
    assert "IBM Plex Mono" in source
    assert "resq-header" in source
    assert "stSidebarNav" in source
    assert "prefers-reduced-motion" in source

def test_light_dark_theme_support_remains_available():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert 'st.sidebar.selectbox("Appearance", ["Light", "Dark"]' in source
    assert "DARK_CSS" in source
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in source
