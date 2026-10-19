from components.theme import page_setup

page_setup("ResQ Assistant")

from components.chatbot import render_chatbot
from components.session import get_center

render_chatbot(get_center())
