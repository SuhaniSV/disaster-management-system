from __future__ import annotations
import os
import streamlit as st
from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar
from core.reporting import situation_report_markdown
from core.notifications import send_email

page_setup("Notifications")
center = get_center()
render_sidebar(center)
render_header(center, "Optional operator-triggered email notifications")
st.warning("Notifications are disabled until an SMTP provider and recipient are configured. This page never sends automatically and never contacts emergency services.")
st.markdown("### Configuration status")
for label, key in [("SMTP host","RESQ_SMTP_HOST"),("From address","RESQ_SMTP_FROM"),("Default recipient","RESQ_ALERT_EMAIL_TO"),("SMTP username","RESQ_SMTP_USERNAME")]:
    st.write(f"**{label}:** {'Configured' if os.getenv(key) else 'Not configured'}")
st.markdown("### Send a situation summary")
recipient = st.text_input("Recipient email (optional; uses configured default if blank)")
if st.button("Send test situation summary", type="primary"):
    result = send_email("ResQ-AI situation summary (operator-triggered)", situation_report_markdown(center), recipient or None)
    if result.get("ok"):
        st.success(result["message"])
    else:
        st.error(result["message"])
st.caption("Set credentials through your hosting platform's secret manager or environment variables. Never commit credentials.")
