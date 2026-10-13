"""Organization repository — async SQL queries."""
from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


class OrganizationRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Organization))
        return result.scalar_one()

    async def get_all(self) -> list[Organization]:
        result = await self.db.execute(select(Organization).order_by(Organization.name))
        return list(result.scalars().all())

    async def get_by_id(self, org_id: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_summary(self) -> dict:
        orgs = await self.get_all()
        return {
            "total":    len(orgs),
            "active":   sum(1 for o in orgs if o.status == "active"),
            "training": sum(1 for o in orgs if o.status == "training"),
            "idle":     sum(1 for o in orgs if o.status == "idle"),
            "offline":  sum(1 for o in orgs if o.status == "offline"),
        }

    async def get_data_distribution(self, org_id: str) -> list[dict]:
        org = await self.get_by_id(org_id)
        if org is None:
            return []
        try:
            return json.loads(org.data_distribution_json)
        except Exception:
            return []

    async def upsert(self, org: Organization) -> None:
        existing = await self.get_by_id(org.id)
        if existing is None:
            self.db.add(org)
        else:
            existing.name = org.name
            existing.description = org.description
            existing.status = org.status
            existing.dataset_size = org.dataset_size
            existing.participation_rate = org.participation_rate
            existing.local_model_status = org.local_model_status
            existing.local_model_accuracy = org.local_model_accuracy
            existing.current_round = org.current_round
            existing.last_update = org.last_update
            existing.joined_at = org.joined_at
            existing.privacy_mode = org.privacy_mode
            existing.data_distribution_json = org.data_distribution_json
        await self.db.flush()
