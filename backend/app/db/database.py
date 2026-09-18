"""
Async SQLAlchemy engine + session for the cloud auth database.

This is deliberately separate from anything meeting-related — per-meeting
session state (transcript, requirements, agent outputs) stays where it is
(local/in-memory per session.py). Only user accounts + auth live here.
"""

from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _build_async_engine():
    db_url = str(settings.database_url)
    connect_args = {}

    # Handle Postgres / Neon SSL requirements for asyncpg
    if "postgres" in db_url:
        parts = urlsplit(db_url)
        scheme = parts.scheme
        if scheme in ("postgres", "postgresql") or scheme.startswith("postgresql+"):
            scheme = "postgresql+asyncpg"

        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        sslmode_val = query.pop("sslmode", None)
        ssl_val = query.get("ssl")

        # asyncpg requires ssl=require, not sslmode=require
        if "neon.tech" in parts.netloc or sslmode_val == "require" or ssl_val in ("require", "true", "1"):
            query["ssl"] = "require"
            connect_args["ssl"] = "require"

        new_query = urlencode(query)
        db_url = urlunsplit((scheme, parts.netloc, parts.path, new_query, parts.fragment))

    return create_async_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args,
    )


engine = _build_async_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields one DB session per request, always closed after."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_models():
    """
    Creates tables if they don't exist yet. Fine for getting started quickly;
    once the schema stabilizes, switch to Alembic migrations instead of
    calling this on every startup (create_all never alters existing tables).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
