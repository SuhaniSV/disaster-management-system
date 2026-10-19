from components.theme import page_setup, render_sidebar

page_setup("ResQ Assistant")

from components.chatbot import render_chatbot
from components.session import get_center

center = get_center()
render_sidebar(center)
render_chatbot(center)
