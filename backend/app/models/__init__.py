"""
ORM Models package.
Import all models here so SQLAlchemy's Base.metadata knows about every table.
"""
from __future__ import annotations

from app.models.organization import Organization
from app.models.training_round import TrainingRound
from app.models.client_participation import ClientParticipation
from app.models.model_version import ModelVersion
from app.models.threat_detection import ThreatDetection
from app.models.metric import Metric
from app.models.privacy_event import PrivacyEvent
from app.models.validation_test import ValidationTest

__all__ = [
    "Organization",
    "TrainingRound",
    "ClientParticipation",
    "ModelVersion",
    "ThreatDetection",
    "Metric",
    "PrivacyEvent",
    "ValidationTest",
]
