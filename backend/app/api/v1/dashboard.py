"""GET /api/dashboard"""
from fastapi import APIRouter
from app.schemas.dashboard import DashboardResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services import db_data

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse, summary="Dashboard summary")
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> DashboardResponse:
    """
    Returns all data needed to render the main dashboard:
    stat cards, chart data, org activity, recent threats, system health.

    **Data source:** demo until Flower + PyTorch pipeline is connected.
    """
    return await db_data.get_dashboard(db)
