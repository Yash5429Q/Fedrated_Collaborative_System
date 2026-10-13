"""Pydantic schemas for the /api/performance endpoint."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MetricComparison(BaseModel):
    label: str
    local: float
    federated: float
    unit: str
    higher_is_better: bool


class OrgPerformanceRow(BaseModel):
    org_id: str
    org_name: str
    local_accuracy: float
    local_f1: float
    local_precision: float
    local_recall: float
    federated_accuracy: float
    federated_f1: float
    gain: float


class NonIIDResult(BaseModel):
    scenario: str
    alpha: float
    local_avg_accuracy: float
    federated_accuracy: float
    robustness_score: int = Field(ge=0, le=100)


class PerfRoundMetric(BaseModel):
    round: int
    local_avg_accuracy: float
    federated_accuracy: float
    local_avg_f1: float
    federated_f1: float


class CollaborationBenefit(BaseModel):
    metric: str
    local_avg: float
    federated: float
    improvement: float
    improvement_pct: float


class ConfusionCell(BaseModel):
    actual: str
    predicted: str
    value: int


class ConfusionMatrix(BaseModel):
    labels: List[str]
    cells: List[ConfusionCell]
    model_type: str   # 'local' | 'federated'


class PerformanceSummary(BaseModel):
    federated_accuracy: float
    local_avg_accuracy: float
    accuracy_gain: float
    federated_f1: float
    local_avg_f1: float
    f1_gain: float
    federated_fpr: float
    local_avg_fpr: float
    fpr_reduction: float


class PerformanceResponse(BaseModel):
    summary: PerformanceSummary
    metric_comparisons: List[MetricComparison]
    org_performance: List[OrgPerformanceRow]
    non_iid_results: List[NonIIDResult]
    round_metrics: List[PerfRoundMetric]
    collaboration_benefit: List[CollaborationBenefit]
    local_confusion_matrix: ConfusionMatrix
    federated_confusion_matrix: ConfusionMatrix
    data_source: str = "database"
    experiment_id: Optional[str] = None
