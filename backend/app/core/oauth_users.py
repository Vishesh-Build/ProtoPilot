from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.oauth_providers import OAuthProfile
from app.db.models import User

_PROVIDER_ID_COLUMN = {"google": User.google_id, "github": User.github_id}


async def get_or_create_oauth_user(db: AsyncSession, provider: str, profile: OAuthProfile) -> User:
    provider_column = _PROVIDER_ID_COLUMN[provider]

    # 1. Already linked to this provider before — this is a returning login.
    result = await db.execute(select(User).where(provider_column == profile.provider_user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    # 2. No link yet, but an account with this email already exists (e.g.
    #    they registered with a password originally) — link this provider
    #    to that same account instead of creating a duplicate.
    result = await db.execute(select(User).where(User.email == profile.email.lower()))
    user = result.scalar_one_or_none()
    if user is not None:
        setattr(user, f"{provider}_id", profile.provider_user_id)
        await db.commit()
        await db.refresh(user)
        return user

    # 3. Brand new account — no password, since it's OAuth-only for now.
    user = User(
        email=profile.email.lower(),
        name=profile.name.strip() or profile.email.split("@")[0],
        hashed_password=None,
    )
    setattr(user, f"{provider}_id", profile.provider_user_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
