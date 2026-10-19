from pathlib import Path

def test_settings_page_exposes_light_and_dark_theme_control():
    source = Path("pages/12_Settings.py").read_text(encoding="utf-8")
    assert 'options=["Light", "Dark"]' in source
    assert 'st.session_state["resq_theme"] = selected_theme' in source
    assert 'st.rerun()' in source

def test_theme_selector_is_not_only_in_sidebar():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert 'st.sidebar.selectbox("Appearance"' not in source
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in source
