from pathlib import Path


def test_dark_mode_overrides_late_light_form_and_widget_rules():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    dark = source[source.index('DARK_CSS = """'):]
    assert '[data-testid="stForm"] input' in dark
    assert "stDownloadButton" in dark
    assert "stFileUploaderDropzone" in dark
    assert "stPlotlyChart" in dark
    assert "color-scheme: dark" in dark


def test_plotly_charts_follow_selected_theme():
    source = Path("components/charts.py").read_text(encoding="utf-8")
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in source
    assert "def _plotly_layout()" in source
    assert 'fig.update_layout(**_plotly_layout())' in source


def test_pydeck_map_uses_selected_theme_and_visible_markers():
    source = Path("components/map.py").read_text(encoding="utf-8")
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in source
    assert 'map_style="dark" if is_dark else "light"' in source
    assert "radius_min_pixels=6" in source
    assert "width_min_pixels=3" in source
    assert "height=560" in source
