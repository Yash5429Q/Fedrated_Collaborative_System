"""GET /api/organizations"""
from fastapi import APIRouter
from app.schemas.organizations import OrganizationsResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services import db_data

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=OrganizationsResponse, summary="Organization list")
async def get_organizations(db: AsyncSession = Depends(get_db)) -> OrganizationsResponse:
    """
    Returns all simulated organizations with status, data distribution,
    local model info, and training participation history.

    **Data source:** demo until real Flower clients are connected.
    """
    return await db_data.get_organizations(db)
