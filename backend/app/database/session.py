"""
SQLAlchemy async session factory.
Supports SQLite (development) and PostgreSQL (production) via DATABASE_URL.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

def normalize_database_url(url: str) -> str:
    """Ensure PostgreSQL URLs use the asyncpg driver for async SQLAlchemy.

    Render and other cloud platforms provide database URLs with postgres:// or
    postgresql:// schemes. SQLAlchemy's async engine requires postgresql+asyncpg://.
    SQLite and other schemes are preserved without changes.
    """
    clean_url = url.strip()
    if clean_url.startswith("postgres://"):
        return clean_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if clean_url.startswith("postgresql://"):
        return clean_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return clean_url


settings = get_settings()
database_url = normalize_database_url(settings.database_url)

engine = create_async_engine(
    database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
