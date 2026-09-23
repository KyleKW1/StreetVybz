"""
email_service.py — Transactional email over SMTP, using EMAIL_CONFIG from config.py.
"""

import re
import smtplib
from email.message import EmailMessage

try:
    from config import EMAIL_CONFIG
except Exception:
    EMAIL_CONFIG = {}


def send_transactional_email(to: str, subject: str, html: str) -> bool:
    """Send an HTML email (with a plain-text fallback). Returns True on success."""
    sender   = EMAIL_CONFIG.get("sender_email", "")
    password = EMAIL_CONFIG.get("sender_password", "")
    if not sender or not password or not to:
        return False
    try:
        msg = EmailMessage()
        msg["From"]    = sender
        msg["To"]      = to
        msg["Subject"] = subject
        text = re.sub(r'<a\s+href="([^"]*)"[^>]*>(.*?)</a>', r"\2: \1", html)
        msg.set_content(re.sub(r"<[^>]+>", "", text))
        msg.add_alternative(html, subtype="html")
        with smtplib.SMTP(EMAIL_CONFIG.get("smtp_server", "smtp.gmail.com"),
                          EMAIL_CONFIG.get("smtp_port", 587), timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)
            server.send_message(msg)
        return True
    except Exception:
        return False
