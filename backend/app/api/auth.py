import datetime
import logging

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.email import EmailNotConfigured, EmailSendError, send_password_reset_email
from app.core.rate_limit import forgot_password_limiter, login_limiter, rate_limit_key
from app.core.security import (
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.core.session_cookies import clear_auth_cookies, issue_session
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)

logger = logging.getLogger("protopilot.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(email=body.email.lower(), name=body.name.strip(), hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await issue_session(user, db, response)
    return user


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    login_limiter.check(rate_limit_key(request, body.email))

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    # Same error for "no such user" and "wrong password" — don't leak which one it was.
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if user is None or user.hashed_password is None or not verify_password(body.password, user.hashed_password):
        # user.hashed_password is None for accounts created via Google/GitHub
        # only — same generic error, so this doesn't leak how the account
        # was created either.
        raise invalid
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been disabled.")

    await issue_session(user, db, response)
    return user


@router.post("/refresh", response_model=UserResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired — please log in again.")
    if refresh_token is None:
        raise unauthorized

    token_hash = hash_opaque_token(refresh_token)
    result = await db.execute(select(User).where(User.refresh_token_hash == token_hash))
    user = result.scalar_one_or_none()

    now = datetime.datetime.now(datetime.timezone.utc)
    # SQLite (unlike Postgres/asyncpg) returns naive datetimes even from a
    # timezone-aware column, and comparing naive vs aware raises. Normalise
    # before comparing so the backend works on both databases.
    expires_at = user.refresh_token_expires_at if user is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
    if user is None or expires_at is None or expires_at < now:
        raise unauthorized

    await issue_session(user, db, response)  # rotates the refresh token too
    return user


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.refresh_token_hash = None
    current_user.refresh_token_expires_at = None
    await db.commit()
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    forgot_password_limiter.check(rate_limit_key(request, body.email))

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    # Always return the same message whether or not the account exists —
    # otherwise this endpoint becomes a way to check who has an account.
    generic_response = MessageResponse(
        message="If an account with that email exists, a reset link has been sent."
    )

    if user is None:
        return generic_response

    raw_token = generate_opaque_token()
    user.reset_token_hash = hash_opaque_token(raw_token)
    user.reset_token_expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )
    await db.commit()

    reset_link = f"{settings.password_reset_url_base}?token={raw_token}"

    try:
        await send_password_reset_email(user.email, reset_link)
    except EmailNotConfigured as e:
        logger.error("password reset requested but email isn't configured: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset email could not be sent — SMTP is not configured on the server.",
        ) from e
    except EmailSendError as e:
        # Deliberately caught separately from EmailNotConfigured (and from any
        # other, truly unexpected exception) so this always resolves to a
        # clean HTTPException — an unhandled exception here would bypass
        # CORSMiddleware and show up in the browser as a misleading "CORS
        # blocked" error instead of the real cause.
        logger.error("password reset email failed to send: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_opaque_token(body.token)
    result = await db.execute(select(User).where(User.reset_token_hash == token_hash))
    user = result.scalar_one_or_none()

    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired.")

    now = datetime.datetime.now(datetime.timezone.utc)
    # Same SQLite/Postgres naive-vs-aware difference as /auth/refresh.
    reset_expires = user.reset_token_expires_at if user is not None else None
    if reset_expires is not None and reset_expires.tzinfo is None:
        reset_expires = reset_expires.replace(tzinfo=datetime.timezone.utc)
    if user is None or reset_expires is None or reset_expires < now:
        raise invalid

    user.hashed_password = hash_password(body.new_password)
    # Single-use: clear it immediately so the same link can't be replayed.
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    # Also kill any existing session — a password reset should log out
    # every device that was using the old password.
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None
    await db.commit()

    return MessageResponse(message="Password updated — please log in with your new password.")
