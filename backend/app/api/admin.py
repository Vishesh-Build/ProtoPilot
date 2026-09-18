"""
Admin API Router for ProtoPilot.

Provides protected endpoints for system health diagnostics, live external service probes,
incident tracking (rate limits, LiveKit disconnections, DB latency, token quotas),
and actionable resolution workflows.

Strict Access Control:
- Requires X-Admin-Secret header or admin_secret cookie matching settings.admin_secret_key
- OR a valid logged-in session belonging to an email listed in settings.admin_emails.
- All unauthorized requests fail immediately with 403 Forbidden.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_access_token
from app.db.database import get_db
from app.db.models import User
from app.services.diagnostics import diagnostics_service

logger = logging.getLogger("protopilot.admin")
router = APIRouter(prefix="/admin", tags=["admin"])


class VerifyAdminRequest(BaseModel):
    secret: str | None = None


async def require_admin(
    request: Request,
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
    admin_secret_cookie: str | None = Cookie(default=None, alias="admin_secret"),
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Enforces that only authorized administrators can access the admin API.
    Raises 403 Forbidden with zero data leakage on any authorization failure.
    """
    # 1. Check secret key from header, cookie, or query param
    secret_candidate = (
        x_admin_secret
        or admin_secret_cookie
        or request.query_params.get("admin_secret")
    )
    if secret_candidate and settings.admin_secret_key:
        if secret_candidate.strip() == settings.admin_secret_key.strip():
            return {"authorized": True, "auth_type": "secret_key"}

    # 2. Check if the current authenticated user's email is in admin_emails
    admin_emails = [e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()]
    if access_token and admin_emails:
        try:
            user_id = decode_access_token(access_token)
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and user.is_active and user.email.lower() in admin_emails:
                return {"authorized": True, "auth_type": "admin_user", "email": user.email}
        except Exception:
            pass

    # No authorization match
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access Denied: You are not authorized to view the system admin console.",
    )


@router.post("/verify-access")
async def verify_admin_access(
    request: Request,
    response: Response,
    body: VerifyAdminRequest | None = None,
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
    admin_secret_cookie: str | None = Cookie(default=None, alias="admin_secret"),
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates provided secret key or user session and returns authorization status.
    Sets the admin_secret cookie on success for convenience.
    """
    provided_secret = (
        (body.secret if body else None)
        or x_admin_secret
        or admin_secret_cookie
        or request.query_params.get("admin_secret")
    )

    if provided_secret and settings.admin_secret_key:
        if provided_secret.strip() == settings.admin_secret_key.strip():
            response.set_cookie(
                key="admin_secret",
                value=provided_secret.strip(),
                httponly=False,  # Allow frontend to inspect presence
                secure=settings.cookie_secure,
                samesite="lax",
                max_age=86400 * 7,  # 7 days
            )
            return {
                "authorized": True,
                "auth_type": "secret_key",
                "message": "Admin authorization granted.",
            }

    # Check user session
    admin_emails = [e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()]
    if access_token and admin_emails:
        try:
            user_id = decode_access_token(access_token)
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and user.is_active and user.email.lower() in admin_emails:
                return {
                    "authorized": True,
                    "auth_type": "admin_user",
                    "email": user.email,
                    "message": f"Admin authorization granted for {user.email}.",
                }
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid admin credentials or unauthorized account.",
    )


@router.get("/health")
async def get_system_health(admin_auth: dict[str, Any] = Depends(require_admin)):
    """
    Runs live health probes on external services (Database, Gemini, Groq, Sarvam, LiveKit)
    and returns comprehensive diagnostics, resource usage, and incident logs.
    """
    report = await diagnostics_service.check_all()
    return {
        "status": "ok",
        "auth": admin_auth,
        "diagnostics": report,
    }


@router.get("/incidents")
async def get_incidents(admin_auth: dict[str, Any] = Depends(require_admin)):
    """
    Returns active problems and historical incident logs.
    """
    incidents = diagnostics_service.get_incidents()
    return {
        "status": "ok",
        "incidents": incidents,
    }


@router.post("/test-all")
async def run_live_diagnostics(admin_auth: dict[str, Any] = Depends(require_admin)):
    """
    Forces immediate live probes on all external providers and updates incident registry.
    """
    report = await diagnostics_service.check_all()
    return {
        "status": "ok",
        "message": "Live diagnostics completed successfully.",
        "diagnostics": report,
    }


@router.post("/resolve-incident/{incident_id}")
async def resolve_incident(
    incident_id: str,
    admin_auth: dict[str, Any] = Depends(require_admin),
):
    """
    Marks an active incident as resolved.
    """
    found = diagnostics_service.resolve_incident(incident_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return {
        "status": "ok",
        "message": f"Incident '{incident_id}' marked as resolved.",
        "incidents": diagnostics_service.get_incidents(),
    }


@router.post("/clear-resolved")
async def clear_resolved_incidents(admin_auth: dict[str, Any] = Depends(require_admin)):
    """
    Removes resolved incidents from the in-memory history log.
    """
    diagnostics_service.clear_resolved_incidents()
    return {
        "status": "ok",
        "message": "Resolved incidents cleared.",
        "incidents": diagnostics_service.get_incidents(),
    }
