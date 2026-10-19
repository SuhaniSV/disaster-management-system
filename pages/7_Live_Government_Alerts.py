from components.theme import page_setup, render_sidebar
from components.session import get_center

page_setup("Live Government Alerts")

from components.live_alerts import render_live_alerts

center = get_center()
render_sidebar(center)
render_live_alerts()
