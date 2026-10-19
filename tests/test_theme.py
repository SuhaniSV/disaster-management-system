from pathlib import Path

def test_theme_has_light_dark_toggle_and_dark_palette():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in source
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in source
    assert "DARK_CSS" in source
