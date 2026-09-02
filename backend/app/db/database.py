"""
Async SQLAlchemy engine + session for the cloud auth database.

This is deliberately separate from anything meeting-related — per-meeting
session state (transcript, requirements, agent outputs) stays where it is
(local/in-memory per session.py). Only user accounts + auth live here.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)

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
