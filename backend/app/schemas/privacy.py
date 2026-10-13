"""Pydantic schemas for the /api/privacy endpoint."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel


PrivacyPropertyStatus = Literal["enforced", "planned", "not_implemented", "n/a"]


class PrivacyProperty(BaseModel):
    id: str
    label: str
    category: str
    description: str
    status: PrivacyPropertyStatus
    detail: str
    planned: bool


class OrgUpdateStatus(BaseModel):
    org_id: str
    org_name: str
    round: int
    update_status: Literal["submitted", "pending", "rejected", "not_sent"]
    update_size: Optional[str]
    submitted_at: Optional[str]
    validation_passed: Optional[bool]
    notes: str


class SecurityEvent(BaseModel):
    id: str
    timestamp: str
    organization: Optional[str]
    event: str
    category: str
    severity: Literal["info", "warning", "critical"]
    status: Literal["resolved", "monitoring", "open"]
    detail: str


class PrivacySummary(BaseModel):
    raw_data_shared: bool
    model_updates_only: bool
    privacy_mechanisms_implemented: int
    privacy_mechanisms_planned: int
    security_events_last_24h: int
    unauthorized_attempts_blocked: int


class PrivacyResponse(BaseModel):
    summary: PrivacySummary
    properties: List[PrivacyProperty]
    org_update_statuses: List[OrgUpdateStatus]
    security_events: List[SecurityEvent]
    data_source: str = "database"
