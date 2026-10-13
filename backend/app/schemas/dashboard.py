"""Pydantic schemas for the /api/dashboard endpoint."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TrainingRoundMetric(BaseModel):
    round: int
    accuracy: float
    # fpr is the only per-round metric stored; labelled correctly for the chart
    fpr: float
    f1: float


class ModelComparisonMetric(BaseModel):
    metric: str
    local: float
    federated: float


class ThreatCategory(BaseModel):
    name: str
    count: int
    color: str


class OrgActivityItem(BaseModel):
    org_id: str
    name: str
    status: str
    # current_round is the experiment round this org participated up to (None if not a participant)
    current_round: Optional[int]
    last_update: str
    # True if the org participated in the selected experiment
    is_experiment_participant: bool = False


class RecentThreat(BaseModel):
    id: str
    timestamp: str
    organization: str
    threat_type: str
    severity: Literal["critical", "high", "medium", "low"]
    confidence: float
    status: str
    model_version: str


class SystemComponent(BaseModel):
    name: str
    status: Literal["healthy", "degraded", "offline", "unknown"]
    detail: str


class DashboardResponse(BaseModel):
    # Registered organisations in the registry (may differ from experiment participants)
    total_organizations: int
    active_organizations: int
    # Clients that actually participated in the selected experiment
    experiment_clients: int
    current_round: int
    total_rounds: int
    threats_detected: int
    global_model_accuracy: float
    f1_score: float
    false_positive_rate: float
    # Structured privacy status drawn from verified experiment config
    privacy_status: str
    privacy_detail: Optional[str] = None
    training_rounds: List[TrainingRoundMetric]
    model_comparison: List[ModelComparisonMetric]
    threat_categories: List[ThreatCategory]
    # All registered orgs, with is_experiment_participant flag
    org_activity: List[OrgActivityItem]
    recent_threats: List[RecentThreat]
    system_components: List[SystemComponent]
    experiment_id: Optional[str] = None
    data_source: str = Field(default="database", description="'demo' until real data is connected")
