"""Pydantic schemas for the /api/predict endpoint."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    """Request body for POST /api/predict."""
    features: List[float] = Field(
        ...,
        description="Exactly 68 numerical feature values from a network flow.",
        min_length=1,
        max_length=200,  # upper guard; validated strictly as ==68 in the service
    )

    @field_validator("features", mode="before")
    @classmethod
    def reject_non_numeric(cls, v):
        if not isinstance(v, list):
            raise ValueError("features must be a list")
        for i, item in enumerate(v):
            if not isinstance(item, (int, float)):
                raise ValueError(f"Feature at index {i} must be a number, got {type(item).__name__}")
        return v


class PredictionResult(BaseModel):
    class_id: int
    label: str
    confidence: float


class ModelInfo(BaseModel):
    name: str
    input_features: int
    classes: int
    experiment_id: str = "unknown"
    checkpoint_path: Optional[str] = None
    normalization: bool = False


class PredictResponse(BaseModel):
    """Response body for POST /api/predict."""
    prediction: PredictionResult
    probabilities: Dict[str, float]
    model: ModelInfo


class PredictHealthResponse(BaseModel):
    """Response body for GET /api/predict/health."""
    model_loaded: bool
    model_name: str = "ThreatNet"
    input_features: int
    num_classes: int
    class_names: List[str]
    experiment_id: Optional[str] = None
    checkpoint_path: Optional[str] = None
    normalization_loaded: bool = False
    error: Optional[str] = None
