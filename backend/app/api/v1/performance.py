"""GET /api/performance"""
from fastapi import APIRouter
from app.schemas.performance import PerformanceResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services import db_data

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("", response_model=PerformanceResponse, summary="Performance analytics")
async def get_performance(db: AsyncSession = Depends(get_db)) -> PerformanceResponse:
    """
    Returns full performance analytics: local vs federated comparison,
    per-org results, Non-IID experiment data, confusion matrices,
    round metrics, and collaboration benefit summary.

    **Data source:** demo — all values are illustrative until real
    ML experiments are run.
    """
    return await db_data.get_performance(db)
