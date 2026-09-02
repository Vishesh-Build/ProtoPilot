"""
Shared "mint a session for this user" logic — used by password login,
register, refresh, AND OAuth callbacks, so there's exactly one place that
sets/clears the auth cookies.
"""

import datetime

from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, generate_opaque_token, hash_opaque_token
from app.db.models import User

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = dict(
        httponly=True,
        secure=settings.cookie_secure,
        samesite="none" if settings.cookie_secure else "lax",
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        ACCESS_COOKIE, access_token,
        max_age=settings.access_token_expire_minutes * 60, **common,
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60, **common,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/", domain=settings.cookie_domain)
    response.delete_cookie(REFRESH_COOKIE, path="/", domain=settings.cookie_domain)


async def issue_session(user: User, db: AsyncSession, response: Response) -> None:
    """Mints a fresh access + refresh token pair, rotates the stored refresh
    token hash (invalidating any previous one), and sets both as cookies."""
    access_token = create_access_token(user.id)

    refresh_token = generate_opaque_token()
    user.refresh_token_hash = hash_opaque_token(refresh_token)
    user.refresh_token_expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        days=settings.refresh_token_expire_days
    )
    await db.commit()

    set_auth_cookies(response, access_token, refresh_token)
