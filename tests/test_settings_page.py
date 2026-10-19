from pathlib import Path


def test_settings_page_does_not_duplicate_theme_control():
    settings_page = Path("pages/12_Settings.py")
    assert not settings_page.exists()


def test_theme_selector_is_not_only_in_sidebar():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert 'st.sidebar.selectbox("Appearance"' not in source
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in source
    assert 'key=f"header_theme_toggle_{current_theme}"' in source
    assert 'st.session_state["resq_theme"] = "Light" if current_theme == "Dark" else "Dark"' in source
    assert 'st.rerun()' in source
