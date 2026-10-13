"""GET /api/privacy"""
from fastapi import APIRouter
from app.schemas.privacy import PrivacyResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services import db_data

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.get("", response_model=PrivacyResponse, summary="Privacy & security status")
async def get_privacy(db: AsyncSession = Depends(get_db)) -> PrivacyResponse:
    """
    Returns privacy architecture status, per-org model update statuses,
    and security event log.

    **Important:** DP, SecAgg, and mTLS are PLANNED — not yet implemented.
    This endpoint reflects design intent, not a deployed privacy system.
    """
    return await db_data.get_privacy(db)
