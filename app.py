from components.theme import page_setup, render_header, render_sidebar
from components.session import get_center

page_setup("Live Disaster Intelligence")

from components.live_disaster_intelligence import render_live_disaster_intelligence

center = get_center()
render_sidebar(center)
render_header(
    center,
    "Monitor source-reported global hazards from GDACS and USGS, with interactive filters and official source records.",
)
render_live_disaster_intelligence()
