"""Metric repository — performance metrics queries."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.metric import Metric


class MetricRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_category(self, category: str) -> list[Metric]:
        result = await self.db.execute(
            select(Metric)
            .where(Metric.category == category)
            .options(selectinload(Metric.organization))
            .order_by(Metric.round_number, Metric.metric_name)
        )
        return list(result.scalars().all())

    async def get_by_name_and_type(self, name: str, model_type: str) -> list[Metric]:
        result = await self.db.execute(
            select(Metric)
            .where(Metric.metric_name == name, Metric.model_type == model_type)
            .order_by(Metric.round_number)
        )
        return list(result.scalars().all())

    async def get_for_round(self, round_number: int) -> list[Metric]:
        result = await self.db.execute(
            select(Metric)
            .where(Metric.round_number == round_number)
        )
        return list(result.scalars().all())

    async def get_for_org(self, org_id: str) -> list[Metric]:
        result = await self.db.execute(
            select(Metric).where(Metric.org_id == org_id)
        )
        return list(result.scalars().all())

    async def get_summary_metrics(self) -> dict[str, float]:
        """Returns {metric_name: value} for category='summary' (legacy seeded — not used for KPIs)."""
        rows = await self.get_by_category("summary")
        return {m.metric_name: m.metric_value for m in rows}

    async def get_comparison_metrics(self) -> list[Metric]:
        return await self.get_by_category("comparison")

    async def get_org_performance(self) -> list[Metric]:
        return await self.get_by_category("org_performance")

    async def get_noniid_metrics(self) -> list[Metric]:
        return await self.get_by_category("noniid")

    async def get_round_metrics(self) -> list[Metric]:
        return await self.get_by_category("round_perf")

    async def get_collab_benefit(self) -> list[Metric]:
        return await self.get_by_category("collab_benefit")

    async def get_confusion_matrix(self, model_type: str) -> list[Metric]:
        result = await self.db.execute(
            select(Metric)
            .where(Metric.category == "confusion_matrix", Metric.model_type == model_type)
        )
        return list(result.scalars().all())

    async def get_confusion_matrix_like(self, model_type_suffix: str) -> list[Metric]:
        """Get confusion matrix rows where model_type ends with the given suffix."""
        result = await self.db.execute(
            select(Metric)
            .where(Metric.category == "confusion_matrix", Metric.model_type.endswith(model_type_suffix))
        )
        return list(result.scalars().all())

    # ── FIXED: was reading metric_value (float 0.0) instead of model_type ──

    async def get_latest_experiment_id(self) -> str | None:
        """Return the experiment_id from the most recent experiment_metadata row.

        The experiment ID is stored in ``model_type``
        (e.g. ``exp_20261005_071403_79eccaf1``), NOT in ``metric_value``
        (which is a placeholder 0.0 float).
        Any dataset suffix such as ``__cicids2017`` is stripped.
        """
        result = await self.db.execute(
            select(Metric.model_type)
            .where(
                Metric.category == "experiment_metadata",
                Metric.metric_name == "experiment_id",
            )
            .order_by(Metric.timestamp.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        # Strip dataset suffix: "exp_20261005_071403_79eccaf1__cicids2017" -> "exp_20261005_071403_79eccaf1"
        return row.split("__")[0]

    async def get_experiment_ids_list(self) -> list[str]:
        """Return all distinct experiment IDs ordered newest-first."""
        result = await self.db.execute(
            select(Metric.model_type)
            .where(
                Metric.category == "experiment_metadata",
                Metric.metric_name == "experiment_id",
            )
            .order_by(Metric.timestamp.desc())
        )
        rows = result.scalars().all()
        seen: set[str] = set()
        ids: list[str] = []
        for row in rows:
            exp_id = row.split("__")[0]
            if exp_id not in seen:
                seen.add(exp_id)
                ids.append(exp_id)
        return ids

    async def get_experiment_metadata(self, experiment_id: str) -> dict:
        """Return {metric_name: value} dict for a given experiment's metadata rows."""
        result = await self.db.execute(
            select(Metric)
            .where(
                Metric.category == "experiment_metadata",
                Metric.model_type.startswith(experiment_id),
            )
            .order_by(Metric.timestamp.desc())
        )
        rows = result.scalars().all()
        meta: dict = {}
        for m in rows:
            if m.metric_name == "dataset":
                # Dataset name is encoded in model_type suffix, e.g. exp_xxx__cicids2017
                suffix = m.model_type.replace(experiment_id, "").lstrip("_")
                meta["dataset"] = suffix if suffix else "unknown"
            else:
                meta[m.metric_name] = m.metric_value
        return meta

    async def get_by_category_for_experiment(self, category: str, experiment_id: str) -> list[Metric]:
        """Get metrics for a specific experiment: model_type starts with experiment_id."""
        result = await self.db.execute(
            select(Metric)
            .where(Metric.category == category, Metric.model_type.startswith(f"{experiment_id}__"))
            .options(selectinload(Metric.organization))
            .order_by(Metric.round_number, Metric.metric_name)
        )
        return list(result.scalars().all())

    async def add(self, m: Metric) -> None:
        self.db.add(m)
        await self.db.flush()

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(Metric)
        )
        return result.scalar_one()
