"""GET /api/experiments  and  GET /api/experiments/latest

Read-only endpoints that surface experiment metadata stored in the
``experiment_metadata`` metrics category.  No experiment records are
created or modified.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.repositories.metric_repo import MetricRepo

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


class ExperimentSummary(BaseModel):
    experiment_id: str
    dataset: Optional[str] = None
    total_samples: Optional[int] = None
    number_of_rounds: Optional[int] = None
    number_of_clients: Optional[int] = None
    local_epochs: Optional[int] = None
    dirichlet_alpha: Optional[float] = None
    random_seed: Optional[int] = None
    is_latest: bool = False


class ExperimentsResponse(BaseModel):
    experiments: List[ExperimentSummary]
    total: int
    latest_experiment_id: Optional[str] = None


def _build_summary(exp_id: str, meta: dict, is_latest: bool = False) -> ExperimentSummary:
    return ExperimentSummary(
        experiment_id=exp_id,
        dataset=str(meta.get("dataset", "CICIDS2017")).upper(),
        total_samples=int(meta["total_samples"]) if "total_samples" in meta else None,
        number_of_rounds=int(meta["number_of_rounds"]) if "number_of_rounds" in meta else None,
        number_of_clients=int(meta["number_of_clients"]) if "number_of_clients" in meta else None,
        local_epochs=int(meta["local_epochs"]) if "local_epochs" in meta else None,
        dirichlet_alpha=float(meta["dirichlet_alpha"]) if "dirichlet_alpha" in meta else None,
        random_seed=int(meta["random_seed"]) if "random_seed" in meta else None,
        is_latest=is_latest,
    )


@router.get("", response_model=ExperimentsResponse, summary="List all persisted experiments")
async def list_experiments(db: AsyncSession = Depends(get_db)) -> ExperimentsResponse:
    """
    Returns metadata for every persisted CICIDS2017 experiment,
    newest-first.  All data is read from the ``experiment_metadata``
    metrics category — no records are created or modified.
    """
    repo = MetricRepo(db)
    exp_ids = await repo.get_experiment_ids_list()
    latest_id = exp_ids[0] if exp_ids else None

    summaries: list[ExperimentSummary] = []
    for i, exp_id in enumerate(exp_ids):
        meta = await repo.get_experiment_metadata(exp_id)
        summaries.append(_build_summary(exp_id, meta, is_latest=(i == 0)))

    return ExperimentsResponse(
        experiments=summaries,
        total=len(summaries),
        latest_experiment_id=latest_id,
    )


@router.get("/latest", response_model=ExperimentSummary, summary="Latest experiment metadata")
async def get_latest_experiment(db: AsyncSession = Depends(get_db)) -> ExperimentSummary:
    """
    Returns metadata for the most-recent CICIDS2017 experiment.
    Used by frontend pages to display the active experiment context.
    """
    repo = MetricRepo(db)
    exp_id = await repo.get_latest_experiment_id()
    if exp_id is None:
        raise HTTPException(status_code=404, detail="No experiment metadata found in database.")
    meta = await repo.get_experiment_metadata(exp_id)
    return _build_summary(exp_id, meta, is_latest=True)


@router.get("/{experiment_id}", response_model=ExperimentSummary, summary="Specific experiment metadata")
async def get_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)) -> ExperimentSummary:
    """
    Returns metadata for a specific experiment by ID.
    """
    repo = MetricRepo(db)
    exp_ids = await repo.get_experiment_ids_list()
    latest_id = exp_ids[0] if exp_ids else None
    if experiment_id not in exp_ids:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    meta = await repo.get_experiment_metadata(experiment_id)
    return _build_summary(experiment_id, meta, is_latest=(experiment_id == latest_id))
