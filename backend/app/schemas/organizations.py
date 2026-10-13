"""Pydantic schemas for the /api/organizations endpoint."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class DataSlice(BaseModel):
    label: str
    value: float
    color: str


class OrgTrainingRound(BaseModel):
    round: int
    status: str
    accuracy: Optional[float]
    duration_s: Optional[int]


class Organization(BaseModel):
    org_id: str
    name: str
    status: Literal["active", "training", "idle", "offline"]
    dataset_size: int
    local_model_status: str
    local_model_accuracy: Optional[float] = None
    current_round: Optional[int] = None
    last_update: str
    data_distribution: List[DataSlice]
    participation_rate: float = Field(ge=0.0, le=1.0)
    recent_rounds: List[OrgTrainingRound]


class OrganizationSummary(BaseModel):
    total: int
    active: int
    training: int
    idle: int
    offline: int


class OrganizationsResponse(BaseModel):
    summary: OrganizationSummary
    organizations: List[Organization]
    data_source: str = "database"
