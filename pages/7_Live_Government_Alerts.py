from components.theme import page_setup, render_header, render_sidebar
from components.session import get_center

page_setup("Live Government Alerts")

from components.live_alerts import render_live_alerts

center = get_center()
render_sidebar(center)
render_header(
    center,
    "Official government weather and disaster alerts, with source availability clearly identified.",
)
render_live_alerts()
