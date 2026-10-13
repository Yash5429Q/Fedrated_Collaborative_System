"""Training repository — rounds, client participations, participation chart."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client_participation import ClientParticipation
from app.models.organization import Organization
from app.models.training_round import TrainingRound


class TrainingRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Rounds ──────────────────────────────────────────────────

    async def get_all_rounds(self) -> list[TrainingRound]:
        result = await self.db.execute(
            select(TrainingRound).order_by(TrainingRound.round_number)
        )
        return list(result.scalars().all())

    async def get_latest_round(self) -> TrainingRound | None:
        result = await self.db.execute(
            select(TrainingRound).order_by(TrainingRound.round_number.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def count_rounds(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(TrainingRound)
        )
        return result.scalar_one()

    # ── Client participations (for current / latest round) ──────

    async def get_participations_for_round(self, round_id: int) -> list[ClientParticipation]:
        result = await self.db.execute(
            select(ClientParticipation)
            .where(ClientParticipation.round_id == round_id)
            .options(selectinload(ClientParticipation.organization))
        )
        return list(result.scalars().all())

    async def get_all_participations(self) -> list[ClientParticipation]:
        result = await self.db.execute(
            select(ClientParticipation)
            .options(selectinload(ClientParticipation.organization))
            .options(selectinload(ClientParticipation.training_round))
            .order_by(ClientParticipation.round_id, ClientParticipation.org_id)
        )
        return list(result.scalars().all())

    # ── Organisations (for client status list) ───────────────────

    async def get_all_orgs(self) -> list[Organization]:
        result = await self.db.execute(select(Organization).order_by(Organization.name))
        return list(result.scalars().all())

    # ── Participation chart (round → count) ──────────────────────

    async def get_participation_by_round(self) -> list[dict]:
        """Returns [{round, participating, total}, ...] ordered by round."""
        rounds = await self.get_all_rounds()
        rows: list[dict] = []
        for r in rounds:
            parts = await self.get_participations_for_round(r.id)
            active = sum(1 for p in parts if p.status != "skipped")
            rows.append({
                "round":         r.round_number,
                "participating": active,
                "total":         r.total_clients,
            })
        return rows

    # ── Upsert helpers ───────────────────────────────────────────

    async def upsert_round(self, tr: TrainingRound) -> TrainingRound:
        result = await self.db.execute(
            select(TrainingRound).where(TrainingRound.round_number == tr.round_number)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            self.db.add(tr)
            await self.db.flush()
            return tr
        existing.status = tr.status
        existing.started_at = tr.started_at
        existing.completed_at = tr.completed_at
        existing.duration_s = tr.duration_s
        existing.participating_clients = tr.participating_clients
        existing.total_clients = tr.total_clients
        existing.accuracy = tr.accuracy
        existing.loss = tr.loss
        existing.f1 = tr.f1
        existing.model_version = tr.model_version
        existing.aggregation_method = tr.aggregation_method
        await self.db.flush()
        return existing

    async def add_participation(self, cp: ClientParticipation) -> None:
        self.db.add(cp)
        await self.db.flush()
