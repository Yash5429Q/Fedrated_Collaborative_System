"""Testing repository — validation test cases."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.validation_test import ValidationTest


class TestingRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all(self) -> list[ValidationTest]:
        result = await self.db.execute(
            select(ValidationTest).order_by(ValidationTest.id)
        )
        return list(result.scalars().all())

    async def get_by_category(self, category: str) -> list[ValidationTest]:
        result = await self.db.execute(
            select(ValidationTest)
            .where(ValidationTest.category == category)
            .order_by(ValidationTest.id)
        )
        return list(result.scalars().all())

    async def get_summary(self) -> dict:
        all_tests = await self.get_all()
        mock_run  = sum(1 for t in all_tests if t.execution_state == "mock_run")
        not_run   = sum(1 for t in all_tests if t.execution_state == "not_run")
        executed  = sum(1 for t in all_tests if t.execution_state == "executed")
        passed    = sum(1 for t in all_tests if t.status == "pass")
        failed    = sum(1 for t in all_tests if t.status == "fail")
        warnings  = sum(1 for t in all_tests if t.status == "warning")
        pending   = sum(1 for t in all_tests if t.status == "pending")
        ran       = mock_run + executed
        return {
            "total":    len(all_tests),
            "executed": executed,
            "mock_run": mock_run,
            "not_run":  not_run,
            "passed":   passed,
            "failed":   failed,
            "warnings": warnings,
            "pending":  pending,
            "pass_rate": round(passed / ran * 100, 1) if ran > 0 else 0.0,
        }

    async def add(self, t: ValidationTest) -> None:
        self.db.add(t)
        await self.db.flush()

    async def count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ValidationTest)
        )
        return result.scalar_one()
