"""POST /api/predict  — real-time threat detection inference."""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.schemas.predict import (
    PredictHealthResponse,
    PredictRequest,
    PredictResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predict", tags=["predict"])


# ── Feature Metadata Resolution (Without PyTorch / Heavy Dataset Load) ──────

def _resolve_feature_metadata() -> tuple[int, int, List[str]]:
    """Determine feature count, class count, and class names from model metadata
    or dataset headers without importing PyTorch or loading dataset arrays.
    """
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    latest_meta = backend_dir / "models" / "latest" / "metadata.json"
    if latest_meta.is_file():
        try:
            with open(latest_meta, "r", encoding="utf-8") as f:
                meta = json.load(f)
            num_features = meta.get("input_features", meta.get("feature_count"))
            num_classes = meta.get("num_classes")
            mapping = meta.get("class_mapping", {})
            if mapping:
                class_names = [mapping[str(i)] for i in range(len(mapping))]
            else:
                class_names = ["Normal", "DoS", "Brute Force", "Port Scan", "Malware"]
            if num_features and num_classes:
                return int(num_features), int(num_classes), class_names
        except Exception as exc:
            logger.debug("Failed reading metadata.json for feature specs: %s", exc)

    # Secondary check: normalization artifact header
    norm_file = backend_dir / "models" / "latest" / "normalization.npz"
    if norm_file.is_file():
        try:
            import numpy as np
            with np.load(norm_file, allow_pickle=True) as norm_data:
                if "feature_names" in norm_data:
                    names = list(norm_data["feature_names"])
                    return len(names), 5, ["Normal", "DoS", "Brute Force", "Port Scan", "Malware"]
        except Exception as exc:
            logger.debug("Failed reading normalization.npz for feature specs: %s", exc)

    # Tertiary check: cicids2017_clean.npz feature_names header only
    dataset_file = backend_dir / "app" / "ml" / "cicids2017_clean.npz"
    if dataset_file.is_file():
        try:
            import numpy as np
            with np.load(dataset_file, allow_pickle=True) as ds:
                if "feature_names" in ds:
                    names = list(ds["feature_names"])
                    return len(names), 5, ["Normal", "DoS", "Brute Force", "Port Scan", "Malware"]
        except Exception as exc:
            logger.debug("Failed reading cicids2017_clean.npz for feature specs: %s", exc)

    # Canonical fallback for ThreatNet architecture
    return 68, 5, ["Normal", "DoS", "Brute Force", "Port Scan", "Malware"]


NUM_FEATURES, NUM_CLASSES, CLASS_NAMES = _resolve_feature_metadata()


# ── Feature Validation (Pure Python, Zero Torch Overhead) ───────────────────

def validate_features(features: list) -> str | None:
    """Validate a feature vector. Returns an error string, or None if valid."""
    if not isinstance(features, (list, tuple)):
        return "features must be a list of numbers"
    if len(features) != NUM_FEATURES:
        return f"Expected {NUM_FEATURES} features, got {len(features)}"
    for i, v in enumerate(features):
        if not isinstance(v, (int, float)):
            return f"Feature at index {i} is not a number: {type(v).__name__}"
        if math.isnan(v):
            return f"Feature at index {i} is NaN"
        if math.isinf(v):
            return f"Feature at index {i} is Inf"
    return None


# ── Lazy Prediction Helpers (Preserves Function Contracts) ─────────────────

def get_inference_model():
    """Lazily load and return the inference model singleton."""
    from app.ml.inference import get_inference_model as _get_inf
    return _get_inf()


def predict(features: List[float]) -> dict:
    """Lazily load inference engine and execute prediction."""
    from app.ml.inference import predict as _predict
    return _predict(features)


# ── Endpoints ──────────────────────────────────────────────────────────────

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
