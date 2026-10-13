"""Threat repository — detections with filtering, summary, distribution, timeline."""
from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.threat_detection import ThreatDetection


class ThreatRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_threats(
        self,
        organization: str | None = None,
        threat_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ThreatDetection], int]:
        """Returns (detections, total_filtered_count)."""
        stmt = select(ThreatDetection).order_by(ThreatDetection.timestamp.desc())
        if organization:
            stmt = stmt.where(ThreatDetection.organization_name == organization)
        if threat_type:
            stmt = stmt.where(ThreatDetection.threat_type == threat_type)
        if severity:
            stmt = stmt.where(ThreatDetection.severity == severity)
        if status:
            stmt = stmt.where(ThreatDetection.status == status)
        if search:
            s = f"%{search.lower()}%"
            from sqlalchemy import or_
            stmt = stmt.where(
                or_(
                    func.lower(ThreatDetection.threat_type).like(s),
                    func.lower(ThreatDetection.organization_name).like(s),
                    ThreatDetection.source_ip.like(s),
                    ThreatDetection.id.like(s),
                )
            )
        # Total count of filtered results
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_counts_by_severity(self) -> dict[str, int]:
        """Real DB COUNT grouped by severity — replaces hardcoded magic numbers."""
        result = await self.db.execute(
            select(ThreatDetection.severity, func.count())
            .group_by(ThreatDetection.severity)
        )
        return dict(result.all())

    async def get_counts_by_status(self) -> dict[str, int]:
        """Real DB COUNT grouped by status — replaces hardcoded magic numbers."""
        result = await self.db.execute(
            select(ThreatDetection.status, func.count())
            .group_by(ThreatDetection.status)
        )
        return dict(result.all())

    async def get_counts_by_type(self) -> list[dict]:
        result = await self.db.execute(
            select(ThreatDetection.threat_type, func.count().label("cnt"))
            .group_by(ThreatDetection.threat_type)
            .order_by(func.count().desc())
        )
        return [{"type": row[0], "count": row[1]} for row in result.all()]

    async def get_total_count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(ThreatDetection))
        return result.scalar_one()

    async def count_by_status(self, status: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ThreatDetection)
            .where(ThreatDetection.status == status)
        )
        return result.scalar_one()

    async def get_hourly_timeline(self) -> list[dict]:
        """Return real hourly aggregation of threats by severity.

        Uses SQLite's strftime to group by hour-of-day.
        Returns a list of dicts with keys: hour, critical, high, medium, low.
        Only hours that have at least one detection are returned.
        """
        result = await self.db.execute(
            text(
                """
                SELECT
                    strftime('%H:00', timestamp) AS hour,
                    SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical,
                    SUM(CASE WHEN severity = 'high'     THEN 1 ELSE 0 END) AS high,
                    SUM(CASE WHEN severity = 'medium'   THEN 1 ELSE 0 END) AS medium,
                    SUM(CASE WHEN severity = 'low'      THEN 1 ELSE 0 END) AS low
                FROM threat_detections
                GROUP BY hour
                ORDER BY hour
                """
            )
        )
        rows = result.all()
        return [
            {
                "hour":     row[0],
                "critical": row[1] or 0,
                "high":     row[2] or 0,
                "medium":   row[3] or 0,
                "low":      row[4] or 0,
            }
            for row in rows
        ]

    async def avg_confidence(self) -> float:
        result = await self.db.execute(
            select(func.avg(ThreatDetection.confidence)).select_from(ThreatDetection)
        )
        val = result.scalar_one()
        return round(float(val), 1) if val is not None else 0.0

    async def add(self, td: ThreatDetection) -> None:
        self.db.add(td)
        await self.db.flush()

    async def count(self) -> int:
        return await self.get_total_count()
