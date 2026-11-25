"""
SQLAlchemy async session factory.
Supports SQLite (development) and PostgreSQL (production) via DATABASE_URL.
"""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

# Directory that contains the ``backend/`` package tree.
# Used to resolve relative SQLite paths so the database file is always
# created inside ``backend/`` regardless of the working directory.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def normalize_database_url(url: str) -> str:
    """Normalise a database URL for async SQLAlchemy.

    * PostgreSQL ``postgres://`` / ``postgresql://`` → ``postgresql+asyncpg://``
    * SQLite relative paths (``sqlite+aiosqlite:///./cyber20.db``) are resolved
      relative to the ``backend/`` directory so the same ``.db`` file is used
      regardless of the working directory the process was started from.
    * All other schemes are returned unchanged.
    """
    clean_url = url.strip()
    if clean_url.startswith("postgres://"):
        return clean_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if clean_url.startswith("postgresql://"):
        return clean_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Resolve relative SQLite paths to backend/ directory.
    # Matches  sqlite+aiosqlite:///./cyber20.db  or  sqlite:///./data.db  etc.
    m = re.match(r"^(sqlite(?:\+\w+)?:///)(\./.+)$", clean_url)
    if m:
        prefix, rel_path = m.group(1), m.group(2)
        abs_path = (_BACKEND_DIR / rel_path).resolve()
        return f"{prefix}{abs_path.as_posix()}"

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
