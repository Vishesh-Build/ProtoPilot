"""
All password/token cryptography lives here — nowhere else should hash a
password, mint a JWT, or generate a reset token directly.
"""

import datetime
import hashlib
import secrets

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------

def create_access_token(user_id: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Returns the user_id (sub) if valid. Raises jwt.PyJWTError if not."""
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload["sub"]


# ---------------------------------------------------------------------------
# Opaque tokens (refresh tokens, password-reset tokens)
#
# These are NOT JWTs — they're random opaque strings. Only their SHA-256
# hash is ever stored in the DB, same principle as passwords: a leaked DB
# row shouldn't hand out a usable token.
# ---------------------------------------------------------------------------

def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# OAuth CSRF state tokens
#
# Short-lived signed JWTs used only as the OAuth `state` parameter — proves
# the callback belongs to a login we actually started, without needing a
# server-side session store (stateless, works fine across multiple workers).
# ---------------------------------------------------------------------------

def create_oauth_state_token(provider: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "type": "oauth_state",
        "provider": provider,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_oauth_state_token(token: str, expected_provider: str) -> None:
    """Raises jwt.PyJWTError (incl. a plain ValueError wrapped as such) if invalid."""
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "oauth_state" or payload.get("provider") != expected_provider:
        raise jwt.InvalidTokenError("state token doesn't match this provider/flow")
