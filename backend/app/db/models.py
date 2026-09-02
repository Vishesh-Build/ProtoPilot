import datetime
import uuid

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Nullable now — OAuth-only accounts (Google/GitHub) never set a password.
    # `verify_password` correctly rejects login attempts against a None hash.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # One row per user, but a user can link both providers to the same
    # account (matched by email on first OAuth login) — both columns can
    # be set on the same row.
    google_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    github_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # --- Password reset ---
    # Only the HASH of the reset token is stored (same principle as passwords —
    # if the DB leaks, raw tokens shouldn't be usable). Single-use: cleared
    # the moment it's consumed or a new one is requested.
    reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Refresh token rotation ---
    # Stores only the hash of the *current* valid refresh token per user.
    # Logging in issues a new one and invalidates any previous refresh token.
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refresh_token_expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
