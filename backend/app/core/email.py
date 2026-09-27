"""
Sends real password reset emails via HTTP APIs (Resend, Brevo) or standard SMTP.
On hosting platforms like Render free tier where SMTP ports (25, 465, 587) are
blocked, setting RESEND_API_KEY sends reliably over HTTPS Port 443.
"""

import asyncio
import logging
from email.message import EmailMessage

import aiosmtplib
import httpx

from app.config import settings

logger = logging.getLogger("protopilot.email")

_SEND_TIMEOUT_SECONDS = 5.0


class EmailNotConfigured(RuntimeError):
    pass


class EmailSendError(RuntimeError):
    pass


async def _send_via_resend(to_email: str, subject: str, html_content: str, text_content: str) -> None:
    sender = (
        settings.smtp_from_address
        if settings.smtp_from_address and not settings.smtp_from_address.endswith("@protopilot.app")
        else "ProtoPilot <onboarding@resend.dev>"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": sender,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": text_content,
            },
        )
        if resp.status_code >= 400:
            logger.error("Resend API error: %s", resp.text)
            try:
                err_data = resp.json()
                msg = err_data.get("message", "")
                if "only send testing emails to your own email address" in msg:
                    raise EmailSendError(
                        f"Resend Sandbox Mode: Free Resend only allows sending to the account owner's email ({to_email} is not the owner). "
                        "To send to any recipient, verify your domain at resend.com/domains or use Brevo."
                    )
            except (ValueError, KeyError):
                pass
            raise EmailSendError(f"Email service rejected request: {resp.text[:200]}")


async def _send_via_brevo(to_email: str, subject: str, html_content: str, text_content: str) -> None:
    sender_email = (
        settings.brevo_sender_email
        or settings.smtp_username
        or (settings.smtp_from_address if "@" in settings.smtp_from_address and not settings.smtp_from_address.endswith("@protopilot.app") else None)
        or "visheshbarot7@gmail.com"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": settings.brevo_api_key,
                "Content-Type": "application/json",
            },
            json={
                "sender": {"email": sender_email, "name": "ProtoPilot"},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
                "textContent": text_content,
            },
        )
        if resp.status_code >= 400:
            logger.error("Brevo API error (%d): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                msg = err_data.get("message", "")
                if msg:
                    raise EmailSendError(f"Brevo error: {msg}")
            except (ValueError, KeyError):
                pass
            raise EmailSendError(f"Email service rejected request: {resp.text[:200]}")


async def _send_via_smtp(to_email: str, subject: str, text_content: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from_address
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text_content)

    is_ssl_port = settings.smtp_port == 465
    try:
        await asyncio.wait_for(
            aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password.replace(" ", ""),
                use_tls=is_ssl_port,
                start_tls=not is_ssl_port,
            ),
            timeout=_SEND_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as e:
        logger.error("SMTP delivery to %s timed out after %.0fs", to_email, _SEND_TIMEOUT_SECONDS)
        raise EmailSendError(
            "Email server timed out. Note: Render free tier blocks outbound SMTP ports 25, 465, and 587. "
            "Set BREVO_API_KEY or RESEND_API_KEY in Render to send emails over HTTPS Port 443."
        ) from e
    except aiosmtplib.SMTPAuthenticationError as e:
        logger.error("SMTP auth rejected for %s: %s", to_email, e)
        raise EmailSendError(
            "SMTP login was rejected. If using Gmail, SMTP_PASSWORD must be a 16-character App Password."
        ) from e
    except aiosmtplib.SMTPException as e:
        logger.error("SMTP error for %s: %s", to_email, e)
        raise EmailSendError(f"SMTP server rejected message: {e}") from e


async def _dispatch_email(to_email: str, subject: str, html_content: str, text_content: str) -> None:
    if settings.brevo_api_key:
        await _send_via_brevo(to_email, subject, html_content, text_content)
        logger.info("Email '%s' sent to %s via Brevo API", subject, to_email)
        return

    if settings.resend_api_key:
        await _send_via_resend(to_email, subject, html_content, text_content)
        logger.info("Email '%s' sent to %s via Resend API", subject, to_email)
        return

    if settings.smtp_host and settings.smtp_username and settings.smtp_password:
        await _send_via_smtp(to_email, subject, text_content)
        logger.info("Email '%s' sent to %s via SMTP", subject, to_email)
        return

    raise EmailNotConfigured(
        "No email service configured. Set BREVO_API_KEY or RESEND_API_KEY (recommended on Render) or SMTP settings."
    )


async def send_password_reset_email(to_email: str, reset_link: str) -> None:
    subject = "Reset your ProtoPilot password"
    text_content = (
        "We received a request to reset your ProtoPilot password.\n\n"
        f"Reset it here (expires in {settings.password_reset_token_expire_minutes} minutes):\n"
        f"{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )
    html_content = (
        f"<div style='font-family: sans-serif; max-width: 500px; margin: 0 auto; padding: 24px; color: #1e293b;'>"
        f"<h2>Reset your ProtoPilot password</h2>"
        f"<p>We received a request to reset your password. Click the button below to set a new password:</p>"
        f"<p style='margin: 24px 0;'><a href='{reset_link}' style='background: #4A63E8; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;'>Reset Password</a></p>"
        f"<p style='color: #64748b; font-size: 13px;'>Or copy and paste this link in your browser:<br/><a href='{reset_link}' style='color: #4A63E8;'>{reset_link}</a></p>"
        f"<p style='color: #94a3b8; font-size: 12px; margin-top: 32px;'>This link expires in {settings.password_reset_token_expire_minutes} minutes. If you did not make this request, you can ignore this email.</p>"
        f"</div>"
    )
    await _dispatch_email(to_email, subject, html_content, text_content)


async def send_verification_email(to_email: str, verify_link: str) -> None:
    subject = "Verify your ProtoPilot account"
    text_content = (
        "Welcome to ProtoPilot!\n\n"
        f"Please verify your email address to activate your account:\n"
        f"{verify_link}\n\n"
        "This link expires in 24 hours. If you did not sign up for ProtoPilot, you can safely ignore this email."
    )
    html_content = (
        f"<div style='font-family: sans-serif; max-width: 500px; margin: 0 auto; padding: 24px; color: #1e293b;'>"
        f"<h2>Welcome to ProtoPilot!</h2>"
        f"<p>Thank you for creating an account. Please click the button below to verify your email address and activate your account:</p>"
        f"<p style='margin: 24px 0;'><a href='{verify_link}' style='background: #4A63E8; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;'>Verify Email Address</a></p>"
        f"<p style='color: #64748b; font-size: 13px;'>Or copy and paste this link in your browser:<br/><a href='{verify_link}' style='color: #4A63E8;'>{verify_link}</a></p>"
        f"<p style='color: #94a3b8; font-size: 12px; margin-top: 32px;'>This verification link expires in 24 hours. If you did not create a ProtoPilot account, you can safely ignore this email.</p>"
        f"</div>"
    )
    await _dispatch_email(to_email, subject, html_content, text_content)
