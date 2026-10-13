"""GET /api/threats"""
from typing import Optional

from fastapi import APIRouter, Query
from app.schemas.threats import ThreatsResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services import db_data

router = APIRouter(prefix="/api/threats", tags=["threats"])


@router.get("", response_model=ThreatsResponse, summary="Threat detections")
async def get_threats(
    db: AsyncSession = Depends(get_db),
    organization: Optional[str] = Query(default=None, description="Filter by organization name"),
    threat_type:  Optional[str] = Query(default=None, alias="threatType", description="Filter by threat category"),
    severity:     Optional[str] = Query(default=None, description="critical | high | medium | low"),
    status:       Optional[str] = Query(default=None, description="detected | blocked | investigating | resolved"),
    search:       Optional[str] = Query(default=None, description="Free-text search across org, type, source IP"),
    page:         int           = Query(default=1, ge=1),
    page_size:    int           = Query(default=50, ge=1, le=200, alias="pageSize"),
) -> ThreatsResponse:
    """
    Returns threat detections with optional filtering, plus summary,
    type distribution, and 24-hour timeline.

    **Data source:** demo until real ML inference pipeline is connected.
    """
    return await db_data.get_threats(db=db, 
        organization=organization,
        threat_type=threat_type,
        severity=severity,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
