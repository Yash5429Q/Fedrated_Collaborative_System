"""GET /api/training  and  GET /api/training/rounds"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.training import TrainingResponse, TrainingRoundsResponse
from app.services import db_data

router = APIRouter(prefix="/api/training", tags=["training"])


@router.get("", response_model=TrainingResponse, summary="Current training state")
async def get_training(db: AsyncSession = Depends(get_db)) -> TrainingResponse:
    """
    Returns the current federated training state derived from the latest
    CICIDS2017 experiment: global model summary, per-client statuses,
    and participation time-series.

    All values are sourced from the ``experiment_summary``,
    ``experiment_round``, and ``experiment_org`` metric categories.
    """
    return await db_data.get_training(db)


@router.get("/rounds", response_model=TrainingRoundsResponse, summary="Round history")
async def get_training_rounds(db: AsyncSession = Depends(get_db)) -> TrainingRoundsResponse:
    """
    Returns the complete history of federated training rounds from the
    latest CICIDS2017 experiment (newest first), with per-round accuracy,
    F1, and client participation.
    """
    return await db_data.get_training_rounds(db)
