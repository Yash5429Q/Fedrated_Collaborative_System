"""
Inference service — loads a trained ThreatNet checkpoint and runs predictions.

The model is loaded ONCE at import time (singleton) and reused for every
request.  It stays in eval mode on CPU with torch.no_grad().

Normalization:
  The checkpoint directory must contain ``normalization.npz`` with the exact
  mean/std that were used during training.  Every incoming feature vector is
  z-score normalized using those parameters **before** being fed to ThreatNet.

  formula:  normalized = (raw - mean) / std
  where std already includes the 1e-8 epsilon from training.
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn.functional as F

# Limit PyTorch CPU threads for low-memory hosting compatibility
if hasattr(torch, "set_num_threads"):
    try:
        torch.set_num_threads(1)
    except Exception:
        pass

from app.ml.data import CLASS_NAMES, NUM_CLASSES, NUM_FEATURES, FEATURE_NAMES
from app.ml.model import ThreatNet, predict_classes, validate_attack_threshold
from app.ml.data import apply_robust_preprocessing, validate_preprocessing

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/
_MODELS_DIR = _BACKEND_ROOT / "models"
_LATEST_DIR = _MODELS_DIR / "latest"


# ── Singleton model holder ─────────────────────────────────────

class _InferenceModel:
    """Thread-safe singleton that holds the loaded ThreatNet."""

    def __init__(self) -> None:
        self.model: Optional[ThreatNet] = None
        self.metadata: Optional[dict] = None
        self.checkpoint_path: Optional[str] = None
        self.is_loaded: bool = False
        self.load_error: Optional[str] = None
        # Normalization parameters
        self.preprocessing = None
        self.norm_mean: Optional[np.ndarray] = None
        self.norm_std: Optional[np.ndarray] = None
        self.norm_feature_names: Optional[list] = None
        self.has_normalization: bool = False

    def load(self, checkpoint_dir: Optional[str] = None) -> bool:
        """Load model weights and normalization from a checkpoint directory.

        Loads only the explicit directory, or models/latest if omitted.
        Returns True on success, False on failure.
        """
        # A failed reload must never leave a previous model marked ready.
        self.__init__()
        search_dirs = [Path(checkpoint_dir) if checkpoint_dir is not None else _LATEST_DIR]

        for cdir in search_dirs:
            model_file = cdir / "global_model.pt"
            meta_file = cdir / "metadata.json"
            norm_file = cdir / "normalization.npz"
            if not model_file.is_file():
                self.load_error = f"Missing checkpoint weights: {model_file}"
                continue

            try:
                # Load metadata
                meta = {}
                if meta_file.exists():
                    with open(meta_file) as f:
                        meta = json.load(f)

                if not isinstance(meta, dict):
                    raise ValueError("Invalid checkpoint metadata")
                mapping = meta.get("class_mapping")
                if mapping is not None and mapping != {str(i): name for i, name in enumerate(CLASS_NAMES)}:
                    raise ValueError("Checkpoint class mapping mismatch")
                rule = meta.get("decision_rule")
                if rule is not None:
                    if not isinstance(rule, dict) or rule.get("version") != "attack_gate_v1" or "attack_threshold" not in rule:
                        raise ValueError("Invalid checkpoint decision rule")
                    validate_attack_threshold(rule["attack_threshold"])

                # Verify dimensions
                stored_features = meta.get("input_features", NUM_FEATURES)
                stored_classes = meta.get("num_classes", NUM_CLASSES)
                if stored_features != NUM_FEATURES:
                    self.load_error = (
                        f"Checkpoint expects {stored_features} features "
                        f"but current pipeline has {NUM_FEATURES}"
                    )
                    logger.error(self.load_error)
                    continue
                if stored_classes != NUM_CLASSES:
                    self.load_error = (
                        f"Checkpoint expects {stored_classes} classes "
                        f"but current pipeline has {NUM_CLASSES}"
                    )
                    logger.error(self.load_error)
                    continue

                # Load weights
                model = ThreatNet()
                state_dict = torch.load(model_file, map_location="cpu", weights_only=True)
                model.load_state_dict(state_dict, strict=True)
                model.eval()
                if not all(torch.isfinite(t).all().item() for t in model.state_dict().values()):
                    raise ValueError("Checkpoint contains non-finite model values")

                # Load normalization parameters
                norm_mean = None
                norm_std = None
                norm_feature_names = None
                has_norm = False
                preprocessing = None

                if norm_file.exists():
                    with np.load(norm_file, allow_pickle=True) as norm_data:
                        if "preprocessing_json" in norm_data:
                            preprocessing = json.loads(str(norm_data["preprocessing_json"].item()))
                            if preprocessing is not None:
                                validate_preprocessing(preprocessing)
                        if meta.get("preprocessing") != preprocessing:
                            raise ValueError("Checkpoint preprocessing metadata mismatch")
                        nm = norm_data["mean"].astype(np.float32)
                        ns = norm_data["std"].astype(np.float32)
                        if "feature_names" in norm_data:
                            norm_feature_names = norm_data["feature_names"].tolist()
                    if nm.shape != (NUM_FEATURES,) or ns.shape != (NUM_FEATURES,):
                        raise ValueError("Normalization mean/std shape mismatch")
                    if not np.isfinite(nm).all() or not np.isfinite(ns).all() or np.any(ns <= 0):
                        raise ValueError("Normalization requires finite mean and positive finite std")
                    if norm_feature_names != list(FEATURE_NAMES):
                        raise ValueError("Normalization feature order does not match dataset schema")
                    if "feature_order" in meta and meta["feature_order"] != list(FEATURE_NAMES):
                        raise ValueError("Checkpoint metadata feature order mismatch")
                    norm_mean, norm_std = nm, ns
                    has_norm = True
                    logger.info(
                        "Loaded normalization params from %s "
                        "(mean range=[%.4f, %.4f], std range=[%.4f, %.4f])",
                        norm_file,
                        float(nm.min()), float(nm.max()),
                        float(ns.min()), float(ns.max()),
                    )
                else:
                    logger.warning(
                        "No normalization.npz found in %s — "
                        "prediction will be disabled "
                        "(normalization required)",
                        cdir,
                    )

                self.model = model
                self.metadata = meta
                self.checkpoint_path = str(cdir)
                self.is_loaded = True
                self.load_error = None
                self.preprocessing = preprocessing
                self.norm_mean = norm_mean
                self.norm_std = norm_std
                self.norm_feature_names = norm_feature_names
                self.has_normalization = has_norm

                logger.info(
                    "Loaded ThreatNet checkpoint from %s "
                    "(features=%d, classes=%d, experiment=%s, normalization=%s)",
                    cdir, NUM_FEATURES, NUM_CLASSES,
                    meta.get("experiment_id", "unknown"),
                    "yes" if has_norm else "NO",
                )
                return True

            except Exception as exc:
                self.load_error = f"Failed to load {model_file}: {exc}"
                logger.error(self.load_error)
                continue

        if not self.is_loaded:
            if not self.load_error:
                self.load_error = "Requested checkpoint unavailable"
            logger.warning("No valid ThreatNet checkpoint found")
        return False


# Module-level singleton
_inference = _InferenceModel()


def get_inference_model() -> _InferenceModel:
    """Return the singleton.  Attempts loading once if not yet loaded."""
    if not _inference.is_loaded:
        _inference.load()
    return _inference


# ── Normalization ──────────────────────────────────────────────

def normalise_features(
    features: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
) -> np.ndarray:
    """Apply z-score normalization: (features - mean) / std.

    ``std`` already includes the 1e-8 epsilon from training.
    """
    return ((features - mean) / std).astype(np.float32)


# ── Prediction ─────────────────────────────────────────────────

def validate_features(features: list) -> str | None:
    """Validate a feature vector.  Returns an error string, or None if OK."""
    if not isinstance(features, (list, tuple)):
        return "features must be a list of numbers"
    if len(features) != NUM_FEATURES:
        return f"Expected {NUM_FEATURES} features, got {len(features)}"
    for i, v in enumerate(features):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return f"Feature at index {i} is not a number: {type(v).__name__}"
        if isinstance(v, int) and abs(v) > float(np.finfo(np.float32).max):
            return f"Feature at index {i} exceeds finite float32 range"
        if math.isnan(v):
            return f"Feature at index {i} is NaN"
        if math.isinf(v):
            return f"Feature at index {i} is Inf"
        if abs(v) > float(np.finfo(np.float32).max):
            return f"Feature at index {i} exceeds finite float32 range"
    return None


def predict(features: List[float]) -> dict:
    """Run inference on a single 68-feature vector.

    The input should be **raw** CICIDS2017-scale feature values.
    They are z-score normalized using the checkpoint's saved mean/std
    before being fed to ThreatNet.

    Feature order must match the CICIDS2017 ordering stored in
    ``normalization.npz["feature_names"]``:
    Destination Port, Flow Duration, Total Fwd Packets, ...

    Returns a dict with prediction, probabilities, and model info.
    Raises RuntimeError if the model is not loaded.
    Raises ValueError if input is invalid.
    """
    started = time.perf_counter()
    inf = get_inference_model()
    if not inf.is_loaded or inf.model is None:
        raise RuntimeError(
            "ThreatNet model is not loaded. "
            "Run an experiment first to create a checkpoint."
        )

    err = validate_features(features)
    if err:
        raise ValueError(err)

    raw = np.array(features, dtype=np.float32)

    if not inf.has_normalization or inf.norm_mean is None or inf.norm_std is None:
        raise RuntimeError("Prediction unavailable: checkpoint normalization is missing")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if getattr(inf, "preprocessing", None) is not None:
            normalized = apply_robust_preprocessing(raw, inf.norm_mean, inf.norm_std, inf.preprocessing)
        else:
            normalized = normalise_features(raw, inf.norm_mean, inf.norm_std)
    if not np.isfinite(normalized).all():
        raise ValueError("Input produces non-finite normalized features")

    tensor = torch.from_numpy(normalized).unsqueeze(0)

    with torch.no_grad():
        logits = inf.model(tensor)
        if logits.shape != (1, NUM_CLASSES) or not torch.isfinite(logits).all().item():
            raise RuntimeError("Model produced invalid logits")
        probs = F.softmax(logits, dim=1)[0]
        if not torch.isfinite(probs).all().item():
            raise RuntimeError("Model produced invalid probabilities")

    rule = (inf.metadata or {}).get("decision_rule")
    threshold = rule["attack_threshold"] if rule else None
    class_id = int(predict_classes(logits, threshold).item())
    confidence = float(probs[class_id].item())

    probabilities = {
        CLASS_NAMES[i]: round(float(probs[i].item()), 6)
        for i in range(NUM_CLASSES)
    }

    return {
        "prediction": {
            "class_id": class_id,
            "label": CLASS_NAMES[class_id],
            "confidence": round(confidence, 6),
        },
        "probabilities": probabilities,
        "attack_score": round(float(probs[1:].sum().item()), 6),
        "attack_threshold": threshold,
        "decision_rule": "attack_gate_v1" if threshold is not None else "argmax",
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "model": {
            "name": "ThreatNet",
            "input_features": NUM_FEATURES,
            "classes": NUM_CLASSES,
            "experiment_id": (inf.metadata or {}).get("experiment_id", "unknown"),
            "checkpoint_path": inf.checkpoint_path,
            "normalization": inf.has_normalization,
        },
    }
