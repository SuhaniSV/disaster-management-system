from pathlib import Path


def test_dark_theme_has_high_contrast_heading_hierarchy():
    source = Path("components/theme.py").read_text(encoding="utf-8")
    assert "[data-testid=\"stMarkdownContainer\"] h2" in source
    assert "color: #f3f7ff !important" in source
    assert "border-left: 4px solid #79aaff" in source
    assert "resq-map-frame" in source


def test_map_uses_selected_theme_and_visible_markers():
    source = Path("components/map.py").read_text(encoding="utf-8")
    assert 'st.session_state.get("resq_theme", "Light") == "Dark"' in source
    assert 'map_style="dark" if is_dark else "light"' in source
    assert "radius_min_pixels=5" in source
    assert "width_min_pixels=3" in source
    assert "height=560" in source
