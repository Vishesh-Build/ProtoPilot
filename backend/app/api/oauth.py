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


from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

def _build_redirect_url(base_url: str, params: dict[str, str]) -> str:
    parts = list(urlparse(base_url))
    query = dict(parse_qsl(parts[4]))
    query.update(params)
    parts[4] = urlencode(query)
    return urlunparse(parts)


@router.get("/google/callback")
async def google_callback(
    response: Response,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    if error or not code or not state:
        reason = error or "missing_parameters"
        return RedirectResponse(_build_redirect_url(settings.oauth_error_redirect_url, {"oauth": "error", "error": reason}))

    try:
        decode_oauth_state_token(state, expected_provider="google")
    except jwt.PyJWTError:
        logger.warning("google oauth callback: invalid/expired state token")
        return RedirectResponse(_build_redirect_url(settings.oauth_error_redirect_url, {"oauth": "error", "error": "invalid_state"}))

    try:
        profile = await fetch_google_profile(code)
    except OAuthError as e:
        logger.warning("google oauth failed: %s", e)
        return RedirectResponse(_build_redirect_url(settings.oauth_error_redirect_url, {"oauth": "error", "error": str(e)}))

    user = await get_or_create_oauth_user(db, "google", profile)

    temp_resp = Response()
    access_token = await issue_session(user, db, temp_resp)

    redirect_url = _build_redirect_url(
        settings.oauth_success_redirect_url,
        {"oauth": "success", "oauth_token": access_token}
    )
    redirect = RedirectResponse(redirect_url)
    for header, value in temp_resp.raw_headers:
        if header.lower() == b"set-cookie":
            redirect.raw_headers.append((header, value))
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
        reason = error or "missing_parameters"
        return RedirectResponse(_build_redirect_url(settings.oauth_error_redirect_url, {"oauth": "error", "error": reason}))

    try:
        decode_oauth_state_token(state, expected_provider="github")
    except jwt.PyJWTError:
        logger.warning("github oauth callback: invalid/expired state token")
        return RedirectResponse(_build_redirect_url(settings.oauth_error_redirect_url, {"oauth": "error", "error": "invalid_state"}))

    try:
        profile = await fetch_github_profile(code)
    except OAuthError as e:
        logger.warning("github oauth failed: %s", e)
        return RedirectResponse(_build_redirect_url(settings.oauth_error_redirect_url, {"oauth": "error", "error": str(e)}))

    user = await get_or_create_oauth_user(db, "github", profile)

    temp_resp = Response()
    access_token = await issue_session(user, db, temp_resp)

    redirect_url = _build_redirect_url(
        settings.oauth_success_redirect_url,
        {"oauth": "success", "oauth_token": access_token}
    )
    redirect = RedirectResponse(redirect_url)
    for header, value in temp_resp.raw_headers:
        if header.lower() == b"set-cookie":
            redirect.raw_headers.append((header, value))
    return redirect
