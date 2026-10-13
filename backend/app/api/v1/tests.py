"""GET /api/tests"""
from fastapi import APIRouter
from app.schemas.testing import TestingResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services import db_data

router = APIRouter(prefix="/api/tests", tags=["testing"])


@router.get("", response_model=TestingResponse, summary="Test suite results")
async def get_tests(db: AsyncSession = Depends(get_db)) -> TestingResponse:
    """
    Returns test cases and acceptance criteria status.

    Each test includes an `execution_state`:
    - `not_run`  — configured but never executed
    - `mock_run` — run with simulated data only
    - `executed` — run against the live integrated system (none yet)

    No tests have been executed against the live system.
    """
    return await db_data.get_testing(db)
