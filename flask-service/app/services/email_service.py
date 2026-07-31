"""
Email delivery, two genuinely working modes (same honest-fallback pattern
as fastapi-service's AI assistant):

1. "smtp"    - if SMTP_HOST is configured, sends a real email via smtplib.
2. "console" - if not, appends the message to EMAIL_OUTBOX_PATH instead of
               failing. This keeps the milestone fully testable without
               real mail credentials, and every response says which mode
               handled it so nothing is mistaken for a real delivery.
"""

import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from ..config import Settings


def send_email(settings: Settings, to_address: str, subject: str, body: str) -> str:
    """Returns the mode used: 'smtp' or 'console'."""
    if settings.SMTP_HOST:
        _send_via_smtp(settings, to_address, subject, body)
        return "smtp"

    _write_to_console_outbox(settings, to_address, subject, body)
    return "console"


def _send_via_smtp(settings: Settings, to_address: str, subject: str, body: str) -> None:
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM
    message["To"] = to_address

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, [to_address], message.as_string())


def _write_to_console_outbox(settings: Settings, to_address: str, subject: str, body: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = (
        f"\n--- EMAIL (console fallback, no SMTP_HOST configured) ---\n"
        f"Time: {timestamp}\nTo: {to_address}\nFrom: {settings.EMAIL_FROM}\n"
        f"Subject: {subject}\n\n{body}\n"
        f"-----------------------------------------------------------\n"
    )
    print(entry)
    with open(settings.EMAIL_OUTBOX_PATH, "a", encoding="utf-8") as f:
        f.write(entry)
