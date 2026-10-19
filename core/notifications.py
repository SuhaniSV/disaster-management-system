"""Optional operator notifications. Disabled unless explicitly configured."""
from __future__ import annotations
import os, smtplib
from email.message import EmailMessage
from typing import Any

def send_email(subject: str, body: str, recipient: str | None = None) -> dict[str, Any]:
    host = os.getenv("RESQ_SMTP_HOST", "").strip()
    sender = os.getenv("RESQ_SMTP_FROM", "").strip()
    target = (recipient or os.getenv("RESQ_ALERT_EMAIL_TO", "")).strip()
    if not host or not sender or not target:
        return {"ok": False, "status": "not_configured", "message": "Configure RESQ_SMTP_HOST, RESQ_SMTP_FROM and RESQ_ALERT_EMAIL_TO to enable email notifications."}
    message = EmailMessage()
    message["Subject"] = subject[:180]
    message["From"] = sender
    message["To"] = target
    message.set_content(body[:12000])
    try:
        port = int(os.getenv("RESQ_SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            username = os.getenv("RESQ_SMTP_USERNAME", "")
            password = os.getenv("RESQ_SMTP_PASSWORD", "")
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        return {"ok": True, "status": "sent", "message": "Notification accepted by configured SMTP server."}
    except Exception as exc:
        return {"ok": False, "status": "error", "message": f"Email delivery failed ({type(exc).__name__})."}
