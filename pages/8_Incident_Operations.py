from components.theme import page_setup, render_header, render_sidebar
from components.session import get_center
from components.operations import render_operations

page_setup("Incident Operations")
center = get_center()
render_sidebar(center)
render_header(center, "Incident lifecycle, operator notes and audit timeline")
render_operations(center)
