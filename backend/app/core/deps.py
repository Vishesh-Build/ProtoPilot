import jwt
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.database import get_db
from app.db.models import User

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    # 1. Collect candidate tokens (prefer Authorization header if present, fallback to cookie)
    candidates = []
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            candidates.append(parts[1])
        elif len(parts) == 1:
            candidates.append(parts[0])
    if access_token:
        candidates.append(access_token)

    if not candidates:
        raise _CREDENTIALS_ERROR

    user_id = None
    for cand in candidates:
        try:
            user_id = decode_access_token(cand)
            if user_id:
                break
        except jwt.PyJWTError:
            continue

    if not user_id:
        raise _CREDENTIALS_ERROR

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR

    if not user.email_verified:
        # OAuth users are pre-verified by their identity provider (Google / GitHub)
        if user.google_id or user.github_id:
            user.email_verified = True
            await db.commit()
            await db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before logging in.",
            )

    return user
