"""
Database initialisation — creates all tables on startup.
"""
from __future__ import annotations

import logging

from app.database.session import Base, engine, AsyncSessionLocal
import app.models  # noqa: F401 - Ensure tables are registered
from app.database.seed import seed_experiments_if_empty, seed_if_empty

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create database tables if they do not already exist, and seed data."""
    logger.info("Initialising database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        await seed_if_empty(session)
        await seed_experiments_if_empty(session)
        
    logger.info("Database ready.")

