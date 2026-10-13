from fastapi import APIRouter
from app.schemas.system import SystemResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database.session import get_db
from app.services import db_data

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("", response_model=SystemResponse, summary="System health")
async def get_system(db: AsyncSession = Depends(get_db)) -> SystemResponse:
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return await db_data.get_system(db, db_ok=db_ok)
