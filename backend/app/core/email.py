"""
Sends real email via SMTP. There is no mock/fake mode here on purpose —
if SMTP isn't configured, callers get a clear error instead of a
"pretend it sent" success response.
"""

import asyncio
import logging

import aiosmtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("protopilot.email")

_SEND_TIMEOUT_SECONDS = 15.0


class EmailNotConfigured(RuntimeError):
    pass


class EmailSendError(RuntimeError):
    """Raised when SMTP is configured but the actual send failed (bad
    credentials, unverified From address, network/timeout, etc.) — kept
    distinct from EmailNotConfigured so callers can show a different,
    accurate message for each case."""
    pass


async def send_password_reset_email(to_email: str, reset_link: str) -> None:
    if not (settings.smtp_host and settings.smtp_username and settings.smtp_password):
        raise EmailNotConfigured(
            "SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD are not set in .env — "
            "can't send real password reset emails until they are."
        )

    message = EmailMessage()
    message["From"] = settings.smtp_from_address
    message["To"] = to_email
    message["Subject"] = "Reset your ProtoPilot password"
    message.set_content(
        "We received a request to reset your ProtoPilot password.\n\n"
        f"Reset it here (expires in {settings.password_reset_token_expire_minutes} minutes):\n"
        f"{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )

    try:
        await asyncio.wait_for(
            aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                # Gmail (and most providers) show App Passwords grouped with
                # spaces for readability ("xfnz iptn xldc dlfs") but reject
                # auth if you send them with the spaces still in — strip them.
                password=settings.smtp_password.replace(" ", ""),
                start_tls=True,
            ),
            timeout=_SEND_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as e:
        logger.error("password reset email to %s timed out after %.0fs", to_email, _SEND_TIMEOUT_SECONDS)
        raise EmailSendError("Email server took too long to respond — check SMTP_HOST/PORT and your network.") from e
    except aiosmtplib.SMTPAuthenticationError as e:
        logger.error("password reset email to %s failed — SMTP auth rejected: %s", to_email, e)
        raise EmailSendError(
            "SMTP login was rejected. If you're using Gmail, SMTP_PASSWORD must be a 16-character "
            "App Password (not your normal Gmail password), entered without spaces."
        ) from e
    except aiosmtplib.SMTPException as e:
        logger.error("password reset email to %s failed: %s", to_email, e)
        raise EmailSendError(
            "The email server rejected the message. If SMTP_FROM_ADDRESS is different from "
            "SMTP_USERNAME, most providers (incl. Gmail) will reject the send unless that "
            "address is a verified alias on the account — set SMTP_FROM_ADDRESS to the same "
            "address as SMTP_USERNAME to fix this."
        ) from e
    else:
        logger.info("password reset email sent to %s", to_email)
