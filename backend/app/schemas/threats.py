"""Pydantic schemas for the /api/threats endpoint."""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Severity       = Literal["critical", "high", "medium", "low"]
DetectionStatus = Literal["detected", "blocked", "investigating", "resolved"]


class ThreatDetection(BaseModel):
    id: str
    timestamp: str
    organization: str
    organization_id: str
    threat_type: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=100.0)
    status: DetectionStatus
    model_version: str
    source_ip: str
    destination_ip: str
    protocol: str
    port: int
    description: str
    raw_features: Dict[str, float]
    detection_method: Literal["federated", "local"]


class ThreatTimelinePoint(BaseModel):
    hour: str
    critical: int
    high: int
    medium: int
    low: int


class ThreatTypeCount(BaseModel):
    type: str
    count: int
    color: str


class ThreatSummary(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    blocked: int
    investigating: int
    avg_confidence: float


class ThreatsResponse(BaseModel):
    summary: ThreatSummary
    detections: List[ThreatDetection]
    distribution: List[ThreatTypeCount]
    timeline: List[ThreatTimelinePoint]
    total: int
    page: int = 1
    page_size: int = 50
    data_source: str = "database"


class ThreatsQueryParams(BaseModel):
    """Query parameters for filtering threats."""
    organization: Optional[str] = None
    threat_type: Optional[str] = None
    severity: Optional[Severity] = None
    status: Optional[DetectionStatus] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
