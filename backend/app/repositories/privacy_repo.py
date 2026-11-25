"""Privacy repository — org update statuses and security events."""
from __future__ import annotations

from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.privacy_event import PrivacyEvent


class PrivacyRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_security_events(self, *, include_demo: bool = True) -> list[PrivacyEvent]:
        stmt = select(PrivacyEvent).options(selectinload(PrivacyEvent.organization))
        if not include_demo:
            stmt = stmt.where(PrivacyEvent.id.not_in(["sec-001", "sec-002", "sec-003", "sec-004"]))
        result = await self.db.execute(stmt.order_by(PrivacyEvent.timestamp.desc()))
        return list(result.scalars().all())

    async def get_events_by_severity(self, severity: str) -> list[PrivacyEvent]:
        result = await self.db.execute(
            select(PrivacyEvent)
            .where(PrivacyEvent.severity == severity)
            .order_by(PrivacyEvent.timestamp.desc())
        )
        return list(result.scalars().all())

    async def count_recent(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(PrivacyEvent)
        )
        return result.scalar_one()

    @staticmethod
    def count_last_24h(events, now=None) -> int:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        count = 0
        for event in events:
            try:
                stamp = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                if stamp.tzinfo is not None and cutoff <= stamp <= now:
                    count += 1
            except (ValueError, TypeError, AttributeError):
                continue
        return count

    async def count_critical(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(PrivacyEvent)
            .where(PrivacyEvent.severity == "critical")
        )
        return result.scalar_one()

    async def add(self, ev: PrivacyEvent) -> None:
        self.db.add(ev)
        await self.db.flush()

    async def count(self) -> int:
        return await self.count_recent()
