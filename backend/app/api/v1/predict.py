"""POST /api/predict  — real-time threat detection inference."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.ml.data import CLASS_NAMES, NUM_CLASSES, NUM_FEATURES
from app.ml.inference import get_inference_model, predict, validate_features
from app.schemas.predict import (
    PredictHealthResponse,
    PredictRequest,
    PredictResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predict", tags=["predict"])


@router.post(
    "",
    response_model=PredictResponse,
    summary="Run real-time threat detection inference",
    responses={
        400: {"description": "Invalid input features"},
        503: {"description": "Model not loaded"},
    },
)
async def run_prediction(body: PredictRequest) -> PredictResponse:
    """Classify a single network flow using the trained ThreatNet model.

    Requires exactly 68 numerical features. Returns the predicted class,
    confidence, and per-class probabilities.
    """
    # Additional validation beyond Pydantic (exact count, NaN, Inf)
    err = validate_features(body.features)
    if err:
        raise HTTPException(status_code=400, detail=err)

    inf = get_inference_model()
    if not inf.is_loaded:
        raise HTTPException(
            status_code=503,
            detail=(
                "ThreatNet model is not loaded. "
                "Run an experiment first to create a checkpoint. "
                f"Error: {inf.load_error or 'No checkpoint found'}"
            ),
        )

    try:
        result = predict(body.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return PredictResponse(**result)


@router.get(
    "/health",
    response_model=PredictHealthResponse,
    summary="Inference model health check",
)
async def predict_health() -> PredictHealthResponse:
    """Report whether the ThreatNet inference model is loaded and ready."""
    inf = get_inference_model()
    return PredictHealthResponse(
        model_loaded=inf.is_loaded,
        model_name="ThreatNet",
        input_features=NUM_FEATURES,
        num_classes=NUM_CLASSES,
        class_names=CLASS_NAMES,
        experiment_id=(inf.metadata or {}).get("experiment_id"),
        checkpoint_path=inf.checkpoint_path,
        normalization_loaded=inf.has_normalization,
        error=inf.load_error if not inf.is_loaded else None,
    )
