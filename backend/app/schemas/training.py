"""Pydantic schemas for /api/training and /api/training/rounds endpoints."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ClientStatus(BaseModel):
    org_id: str
    org_name: str
    connection_status: str
    training_status: str
    local_accuracy: Optional[float]
    local_loss: Optional[float]
    samples: Optional[int]
    update_size_mb: Optional[float]
    duration_s: Optional[int]


class TrainingRound(BaseModel):
    round: int
    status: Literal["completed", "in_progress", "failed", "skipped"]
    participating_clients: int
    total_clients: int
    accuracy: float
    loss: float
    f1: float
    duration_s: int
    model_version: str
    started_at: str
    completed_at: Optional[str]


class ParticipationPoint(BaseModel):
    round: int
    participating: int
    total: int


class TrainingSummary(BaseModel):
    current_round: int
    total_rounds: int
    global_model_version: str
    training_status: str
    global_accuracy: float
    global_f1: float
    global_loss: float
    avg_round_duration_s: int
    aggregation_strategy: str
    active_clients: int
    total_clients: int


class TrainingResponse(BaseModel):
    summary: TrainingSummary
    client_statuses: List[ClientStatus]
    participation: List[ParticipationPoint]
    data_source: str = "database"


class TrainingRoundsResponse(BaseModel):
    rounds: List[TrainingRound]
    total: int
    data_source: str = "database"
