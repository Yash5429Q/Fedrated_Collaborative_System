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

from app.ml.data import CLASS_NAMES, NUM_CLASSES, NUM_FEATURES
from app.ml.model import ThreatNet

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
        self.norm_mean: Optional[np.ndarray] = None
        self.norm_std: Optional[np.ndarray] = None
        self.norm_feature_names: Optional[list] = None
        self.has_normalization: bool = False

    def load(self, checkpoint_dir: Optional[str] = None) -> bool:
        """Load model weights and normalization from a checkpoint directory.

        Tries ``checkpoint_dir`` first, then ``models/latest/``.
        Returns True on success, False on failure.
        """
        search_dirs = []
        if checkpoint_dir:
            search_dirs.append(Path(checkpoint_dir))
        search_dirs.append(_LATEST_DIR)

        # Also scan models/ for the most recent experiment folder
        if _MODELS_DIR.exists():
            exp_dirs = sorted(
                [d for d in _MODELS_DIR.iterdir()
                 if d.is_dir() and d.name != "latest" and (d / "global_model.pt").exists()],
                key=lambda d: d.name,
                reverse=True,
            )
            search_dirs.extend(exp_dirs)

        for cdir in search_dirs:
            model_file = cdir / "global_model.pt"
            meta_file = cdir / "metadata.json"
            norm_file = cdir / "normalization.npz"
            if not model_file.exists():
                continue

            try:
                # Load metadata
                meta = {}
                if meta_file.exists():
                    with open(meta_file) as f:
                        meta = json.load(f)

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

                # Load normalization parameters
                norm_mean = None
                norm_std = None
                norm_feature_names = None
                has_norm = False

                if norm_file.exists():
                    norm_data = np.load(norm_file, allow_pickle=True)
                    nm = norm_data["mean"]
                    ns = norm_data["std"]

                    # Validate shapes
                    if nm.shape != (NUM_FEATURES,):
                        self.load_error = (
                            f"Normalization mean has shape {nm.shape}, "
                            f"expected ({NUM_FEATURES},)"
                        )
                        logger.error(self.load_error)
                        continue
                    if ns.shape != (NUM_FEATURES,):
                        self.load_error = (
                            f"Normalization std has shape {ns.shape}, "
                            f"expected ({NUM_FEATURES},)"
                        )
                        logger.error(self.load_error)
                        continue

                    norm_mean = nm.astype(np.float32)
                    norm_std = ns.astype(np.float32)
                    if "feature_names" in norm_data:
                        norm_feature_names = norm_data["feature_names"].tolist()
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
                        "inference will feed RAW features to model "
                        "(predictions may be meaningless)",
                        cdir,
                    )

                self.model = model
                self.metadata = meta
                self.checkpoint_path = str(cdir)
                self.is_loaded = True
                self.load_error = None
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
                self.load_error = "No checkpoint found in models/ directory"
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
        if not isinstance(v, (int, float)):
            return f"Feature at index {i} is not a number: {type(v).__name__}"
        if math.isnan(v):
            return f"Feature at index {i} is NaN"
        if math.isinf(v):
            return f"Feature at index {i} is Inf"
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

    # Apply normalization (critical: must match training preprocessing)
    if inf.has_normalization and inf.norm_mean is not None and inf.norm_std is not None:
        normalized = normalise_features(raw, inf.norm_mean, inf.norm_std)
    else:
        # No normalization available — use raw values and warn
        logger.warning(
            "Running inference WITHOUT normalization — "
            "predictions are likely meaningless"
        )
        normalized = raw

    tensor = torch.from_numpy(normalized).unsqueeze(0)

    with torch.no_grad():
        logits = inf.model(tensor)
        probs = F.softmax(logits, dim=1)[0]

    class_id = int(probs.argmax().item())
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
        "model": {
            "name": "ThreatNet",
            "input_features": NUM_FEATURES,
            "classes": NUM_CLASSES,
            "experiment_id": (inf.metadata or {}).get("experiment_id", "unknown"),
            "checkpoint_path": inf.checkpoint_path,
            "normalization": inf.has_normalization,
        },
    }
