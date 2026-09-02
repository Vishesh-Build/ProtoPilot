import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.oauth_providers import (
    OAuthError,
    build_github_authorize_url,
    build_google_authorize_url,
    fetch_github_profile,
    fetch_google_profile,
)
from app.core.oauth_users import get_or_create_oauth_user
from app.core.security import create_oauth_state_token, decode_oauth_state_token
from app.core.session_cookies import issue_session
from app.db.database import get_db

logger = logging.getLogger("protopilot.oauth")
router = APIRouter(prefix="/auth", tags=["oauth"])


def _require_configured(provider: str, client_id: str | None, client_secret: str | None):
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{provider} OAuth isn't configured on the server yet "
                   f"(missing {provider.upper()}_CLIENT_ID / {provider.upper()}_CLIENT_SECRET).",
        )


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

@router.get("/google/login")
async def google_login():
    _require_configured("google", settings.google_client_id, settings.google_client_secret)
    state = create_oauth_state_token("google")
    return RedirectResponse(build_google_authorize_url(state))


@router.get("/google/callback")
async def google_callback(
    response: Response,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    if error or not code or not state:
        return RedirectResponse(settings.oauth_error_redirect_url)

    try:
        decode_oauth_state_token(state, expected_provider="google")
    except jwt.PyJWTError:
        logger.warning("google oauth callback: invalid/expired state token")
        return RedirectResponse(settings.oauth_error_redirect_url)

    try:
        profile = await fetch_google_profile(code)
    except OAuthError as e:
        logger.warning("google oauth failed: %s", e)
        return RedirectResponse(settings.oauth_error_redirect_url)

    user = await get_or_create_oauth_user(db, "google", profile)

    redirect = RedirectResponse(settings.oauth_success_redirect_url)
    await issue_session(user, db, redirect)
    return redirect


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

@router.get("/github/login")
async def github_login():
    _require_configured("github", settings.github_client_id, settings.github_client_secret)
    state = create_oauth_state_token("github")
    return RedirectResponse(build_github_authorize_url(state))


@router.get("/github/callback")
async def github_callback(
    response: Response,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    if error or not code or not state:
        return RedirectResponse(settings.oauth_error_redirect_url)

    try:
        decode_oauth_state_token(state, expected_provider="github")
    except jwt.PyJWTError:
        logger.warning("github oauth callback: invalid/expired state token")
        return RedirectResponse(settings.oauth_error_redirect_url)

    try:
        profile = await fetch_github_profile(code)
    except OAuthError as e:
        logger.warning("github oauth failed: %s", e)
        return RedirectResponse(settings.oauth_error_redirect_url)

    user = await get_or_create_oauth_user(db, "github", profile)

    redirect = RedirectResponse(settings.oauth_success_redirect_url)
    await issue_session(user, db, redirect)
    return redirect
