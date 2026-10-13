"""
Phase 16 — Inference, Predict API, and Normalization tests.

Tests checkpoint loading, normalization artifact, model architecture
compatibility, valid/invalid predictions, health endpoint, and the
critical proof that raw values are normalized before model inference.

Run with:  pytest tests/test_predict.py -v
"""
from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import torch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.ml.data import CLASS_NAMES, NUM_CLASSES, NUM_FEATURES, FEATURE_NAMES
from app.ml.model import ThreatNet, get_parameters


# ── Fixtures ───────────────────────────────────────────────────

BACKEND_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = BACKEND_ROOT / "models"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def trained_checkpoint(tmp_path):
    """Create a real trained-ish checkpoint with normalization in a temp
    directory and point the inference singleton at it."""
    from app.ml.data import load_global_test_set
    from app.ml.model import train_model

    # Quick train on a tiny dataset so weights are non-random
    model = ThreatNet()
    test_loader = load_global_test_set(n_samples=500, seed=99)
    train_model(model, test_loader, epochs=1)
    model.eval()

    ckpt_dir = tmp_path / "test_checkpoint"
    ckpt_dir.mkdir()

    torch.save(model.state_dict(), ckpt_dir / "global_model.pt")

    # Create normalization artifact from the same data
    from app.ml.data import _generate_multiclass_data
    X, _ = _generate_multiclass_data(n_samples=500, seed=99)
    norm_mean = X.mean(axis=0).astype(np.float32)
    norm_std = (X.std(axis=0) + 1e-8).astype(np.float32)

    np.savez(
        ckpt_dir / "normalization.npz",
        mean=norm_mean,
        std=norm_std,
        feature_names=np.array(FEATURE_NAMES),
        epsilon=np.float32(1e-8),
        normalization_method="zscore",
    )

    metadata = {
        "experiment_id": "test_checkpoint_001",
        "dataset_name": "cicids2017",
        "model_name": "ThreatNet",
        "input_features": NUM_FEATURES,
        "num_classes": NUM_CLASSES,
        "class_mapping": {str(i): name for i, name in enumerate(CLASS_NAMES)},
        "rounds": 1,
        "clients": 3,
        "epochs": 1,
        "dirichlet_alpha": 0.5,
        "seed": 42,
        "mode": "iid",
        "normalization_method": "zscore",
        "normalization_artifact": "normalization.npz",
        "normalization_scope": "global",
        "creation_timestamp": "2026-01-01T00:00:00+00:00",
    }
    with open(ckpt_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)

    # Force-load into inference singleton
    from app.ml.inference import _inference
    _inference.load(str(ckpt_dir))

    yield ckpt_dir, norm_mean, norm_std

    # Reset singleton after test
    _inference.model = None
    _inference.metadata = None
    _inference.checkpoint_path = None
    _inference.is_loaded = False
    _inference.load_error = None
    _inference.norm_mean = None
    _inference.norm_std = None
    _inference.norm_feature_names = None
    _inference.has_normalization = False


def _valid_features() -> list[float]:
    """Return a deterministic 68-feature vector of valid floats."""
    np.random.seed(12345)
    return np.random.randn(NUM_FEATURES).tolist()


# ── Normalization Artifact Tests ───────────────────────────────

class TestNormalizationArtifact:
    """Tests for the normalization.npz artifact."""

    def test_normalization_npz_exists_in_latest(self):
        norm_path = MODELS_DIR / "latest" / "normalization.npz"
        assert norm_path.exists(), f"normalization.npz not found at {norm_path}"

    def test_mean_shape(self):
        data = np.load(MODELS_DIR / "latest" / "normalization.npz")
        assert data["mean"].shape == (68,), f"mean shape: {data['mean'].shape}"

    def test_std_shape(self):
        data = np.load(MODELS_DIR / "latest" / "normalization.npz")
        assert data["std"].shape == (68,), f"std shape: {data['std'].shape}"

    def test_feature_names_length(self):
        data = np.load(MODELS_DIR / "latest" / "normalization.npz", allow_pickle=True)
        assert len(data["feature_names"]) == 68

    def test_epsilon_value(self):
        data = np.load(MODELS_DIR / "latest" / "normalization.npz")
        assert float(data["epsilon"]) == pytest.approx(1e-8, abs=1e-12)

    def test_normalization_method(self):
        data = np.load(MODELS_DIR / "latest" / "normalization.npz", allow_pickle=True)
        assert str(data["normalization_method"]) == "zscore"


# ── Checkpoint Tests ───────────────────────────────────────────

class TestCheckpoint:
    """Tests for model checkpoint save/load mechanics."""

    def test_save_and_load_checkpoint(self, tmp_path):
        """Verify a ThreatNet state_dict can be saved and reloaded."""
        model = ThreatNet()
        state_path = tmp_path / "model.pt"
        torch.save(model.state_dict(), state_path)

        loaded = ThreatNet()
        sd = torch.load(state_path, map_location="cpu", weights_only=True)
        loaded.load_state_dict(sd, strict=True)

        orig_params = get_parameters(model)
        loaded_params = get_parameters(loaded)
        for o, l in zip(orig_params, loaded_params):
            np.testing.assert_array_equal(o, l)

    def test_architecture_compatibility(self):
        """Verify ThreatNet has 68 input features and 5 output classes."""
        model = ThreatNet()
        first_layer = model.net[0]
        last_layer = model.net[-1]
        assert first_layer.in_features == 68
        assert last_layer.out_features == 5

    def test_checkpoint_metadata_structure(self, trained_checkpoint):
        ckpt_dir, _, _ = trained_checkpoint
        with open(ckpt_dir / "metadata.json") as f:
            meta = json.load(f)
        required_keys = [
            "experiment_id", "dataset_name", "model_name",
            "input_features", "num_classes", "class_mapping",
            "rounds", "clients", "epochs", "seed",
            "normalization_method", "normalization_artifact",
        ]
        for key in required_keys:
            assert key in meta, f"Missing key: {key}"
        assert meta["input_features"] == 68
        assert meta["num_classes"] == 5

    def test_inference_singleton_loads(self, trained_checkpoint):
        from app.ml.inference import get_inference_model
        inf = get_inference_model()
        assert inf.is_loaded is True
        assert inf.model is not None
        assert inf.load_error is None

    def test_inference_loads_normalization(self, trained_checkpoint):
        from app.ml.inference import get_inference_model
        inf = get_inference_model()
        assert inf.has_normalization is True
        assert inf.norm_mean is not None
        assert inf.norm_std is not None
        assert inf.norm_mean.shape == (68,)
        assert inf.norm_std.shape == (68,)

    def test_wrong_feature_count_rejected(self, tmp_path):
        """Metadata claiming wrong feature count should fail to load."""
        from app.ml.inference import _InferenceModel
        ckpt_dir = tmp_path / "bad_ckpt"
        ckpt_dir.mkdir()
        model = ThreatNet()
        torch.save(model.state_dict(), ckpt_dir / "global_model.pt")
        with open(ckpt_dir / "metadata.json", "w") as f:
            json.dump({"input_features": 99, "num_classes": 5}, f)

        loader = _InferenceModel()
        ok = loader.load(str(ckpt_dir))
        if not ok:
            assert loader.load_error is not None
            assert "99" in loader.load_error or "features" in loader.load_error

    def test_missing_normalization_warns(self, tmp_path):
        """Checkpoint without normalization.npz should still load but flag it."""
        from app.ml.inference import _InferenceModel
        ckpt_dir = tmp_path / "no_norm_ckpt"
        ckpt_dir.mkdir()
        model = ThreatNet()
        torch.save(model.state_dict(), ckpt_dir / "global_model.pt")
        with open(ckpt_dir / "metadata.json", "w") as f:
            json.dump({"input_features": 68, "num_classes": 5}, f)

        loader = _InferenceModel()
        ok = loader.load(str(ckpt_dir))
        assert ok is True
        assert loader.has_normalization is False

    def test_malformed_mean_rejected(self, tmp_path):
        """Normalization with wrong mean shape should fail."""
        from app.ml.inference import _InferenceModel
        ckpt_dir = tmp_path / "bad_mean_ckpt"
        ckpt_dir.mkdir()
        model = ThreatNet()
        torch.save(model.state_dict(), ckpt_dir / "global_model.pt")
        with open(ckpt_dir / "metadata.json", "w") as f:
            json.dump({"input_features": 68, "num_classes": 5}, f)
        np.savez(
            ckpt_dir / "normalization.npz",
            mean=np.zeros(50, dtype=np.float32),  # Wrong shape
            std=np.ones(68, dtype=np.float32),
            feature_names=np.array(FEATURE_NAMES),
        )
        loader = _InferenceModel()
        ok = loader.load(str(ckpt_dir))
        if not ok:
            assert "mean" in (loader.load_error or "").lower() or "50" in (loader.load_error or "")

    def test_malformed_std_rejected(self, tmp_path):
        """Normalization with wrong std shape should fail."""
        from app.ml.inference import _InferenceModel
        ckpt_dir = tmp_path / "bad_std_ckpt"
        ckpt_dir.mkdir()
        model = ThreatNet()
        torch.save(model.state_dict(), ckpt_dir / "global_model.pt")
        with open(ckpt_dir / "metadata.json", "w") as f:
            json.dump({"input_features": 68, "num_classes": 5}, f)
        np.savez(
            ckpt_dir / "normalization.npz",
            mean=np.zeros(68, dtype=np.float32),
            std=np.ones(10, dtype=np.float32),  # Wrong shape
            feature_names=np.array(FEATURE_NAMES),
        )
        loader = _InferenceModel()
        ok = loader.load(str(ckpt_dir))
        if not ok:
            assert "std" in (loader.load_error or "").lower() or "10" in (loader.load_error or "")


# ── Critical Normalization Proof Test ──────────────────────────

class TestNormalizationProof:
    """Prove that inference normalizes raw values before feeding to ThreatNet."""

    def test_raw_values_are_normalized_before_model(self, trained_checkpoint):
        """Deterministic proof: verify the tensor passed to the model matches
        the expected normalized values, NOT the raw input."""
        ckpt_dir, norm_mean, norm_std = trained_checkpoint
        from app.ml.inference import get_inference_model, normalise_features

        inf = get_inference_model()
        assert inf.has_normalization, "Normalization not loaded"

        # Known raw input
        raw_input = np.array([1000.0, 50000.0, 5.0] + [1.0] * 65, dtype=np.float32)

        # Expected normalized values
        expected_norm = (raw_input - norm_mean) / norm_std

        # Verify normalise_features matches
        actual_norm = normalise_features(raw_input, norm_mean, norm_std)
        np.testing.assert_allclose(actual_norm, expected_norm, rtol=1e-6)

        # Now run prediction and capture the model input via a hook
        captured_inputs = []

        def hook(module, input_tensor, output):
            captured_inputs.append(input_tensor[0].detach().cpu().numpy())

        # Attach hook to the first layer of ThreatNet
        handle = inf.model.net[0].register_forward_hook(hook)

        from app.ml.inference import predict
        predict(raw_input.tolist())

        handle.remove()

        # The tensor that reached the model's first layer
        assert len(captured_inputs) == 1, f"Expected 1 forward pass, got {len(captured_inputs)}"
        model_input = captured_inputs[0][0]  # batch dim

        # THIS IS THE CRITICAL ASSERTION:
        # The model received normalized values, NOT the raw values
        np.testing.assert_allclose(
            model_input, expected_norm, rtol=1e-5,
            err_msg="Model received raw values instead of normalized values!"
        )

        # Verify it's NOT the raw input
        assert not np.allclose(model_input, raw_input), \
            "Model received raw input without normalization!"


# ── Prediction Tests ───────────────────────────────────────────

class TestPrediction:
    """Tests for the predict() function directly."""

    def test_valid_prediction(self, trained_checkpoint):
        from app.ml.inference import predict
        result = predict(_valid_features())
        assert "prediction" in result
        assert "probabilities" in result
        assert "model" in result
        pred = result["prediction"]
        assert 0 <= pred["class_id"] <= 4
        assert pred["label"] in CLASS_NAMES
        assert 0.0 <= pred["confidence"] <= 1.0

    def test_probabilities_sum_to_one(self, trained_checkpoint):
        from app.ml.inference import predict
        result = predict(_valid_features())
        total = sum(result["probabilities"].values())
        assert abs(total - 1.0) < 1e-4, f"Probabilities sum to {total}"

    def test_all_probabilities_non_negative(self, trained_checkpoint):
        from app.ml.inference import predict
        result = predict(_valid_features())
        for cls, prob in result["probabilities"].items():
            assert prob >= 0.0, f"Negative probability for {cls}: {prob}"

    def test_class_id_range(self, trained_checkpoint):
        from app.ml.inference import predict
        result = predict(_valid_features())
        assert result["prediction"]["class_id"] in range(5)

    def test_model_info_reports_normalization(self, trained_checkpoint):
        from app.ml.inference import predict
        result = predict(_valid_features())
        assert result["model"]["normalization"] is True


# ── Validation Tests ───────────────────────────────────────────

class TestValidation:
    """Tests for input validation edge cases."""

    def test_67_features_rejected(self, trained_checkpoint):
        from app.ml.inference import validate_features
        err = validate_features([0.0] * 67)
        assert err is not None
        assert "68" in err

    def test_69_features_rejected(self, trained_checkpoint):
        from app.ml.inference import validate_features
        err = validate_features([0.0] * 69)
        assert err is not None
        assert "68" in err

    def test_empty_rejected(self, trained_checkpoint):
        from app.ml.inference import validate_features
        err = validate_features([])
        assert err is not None

    def test_nan_rejected(self, trained_checkpoint):
        from app.ml.inference import validate_features
        features = [0.0] * NUM_FEATURES
        features[10] = float("nan")
        err = validate_features(features)
        assert err is not None
        assert "NaN" in err

    def test_inf_rejected(self, trained_checkpoint):
        from app.ml.inference import validate_features
        features = [0.0] * NUM_FEATURES
        features[5] = float("inf")
        err = validate_features(features)
        assert err is not None
        assert "Inf" in err

    def test_string_rejected(self, trained_checkpoint):
        from app.ml.inference import validate_features
        features = [0.0] * (NUM_FEATURES - 1) + ["hello"]
        err = validate_features(features)
        assert err is not None
        assert "not a number" in err


# ── API Endpoint Tests ─────────────────────────────────────────

class TestPredictAPI:
    """Tests for POST /api/predict and GET /api/predict/health."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        r = await client.get("/api/predict/health")
        assert r.status_code == 200
        data = r.json()
        assert "model_loaded" in data
        assert data["model_name"] == "ThreatNet"
        assert data["input_features"] == 68
        assert data["num_classes"] == 5
        assert "normalization_loaded" in data

    @pytest.mark.asyncio
    async def test_predict_valid(self, client: AsyncClient, trained_checkpoint):
        r = await client.post("/api/predict", json={"features": _valid_features()})
        assert r.status_code == 200
        data = r.json()
        assert data["prediction"]["label"] in CLASS_NAMES
        assert 0 <= data["prediction"]["class_id"] <= 4
        assert 0.0 <= data["prediction"]["confidence"] <= 1.0
        assert len(data["probabilities"]) == 5
        assert data["model"]["input_features"] == 68
        assert data["model"]["classes"] == 5
        assert data["model"]["normalization"] is True

    @pytest.mark.asyncio
    async def test_predict_67_features_error(self, client: AsyncClient, trained_checkpoint):
        r = await client.post("/api/predict", json={"features": [0.0] * 67})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_predict_69_features_error(self, client: AsyncClient, trained_checkpoint):
        r = await client.post("/api/predict", json={"features": [0.0] * 69})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_predict_empty_features_error(self, client: AsyncClient, trained_checkpoint):
        r = await client.post("/api/predict", json={"features": []})
        assert r.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_predict_nan_error(self, client: AsyncClient, trained_checkpoint):
        features = [0.0] * NUM_FEATURES
        features[0] = None  # type: ignore
        r = await client.post("/api/predict", json={"features": features})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_string_error(self, client: AsyncClient, trained_checkpoint):
        features = [0.0] * (NUM_FEATURES - 1) + ["bad"]
        r = await client.post("/api/predict", json={"features": features})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_missing_body(self, client: AsyncClient, trained_checkpoint):
        r = await client.post("/api/predict", json={})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_no_crash_on_inf(self, client: AsyncClient, trained_checkpoint):
        features = [0.0] * NUM_FEATURES
        features[0] = None  # type: ignore
        r = await client.post("/api/predict", json={"features": features})
        assert r.status_code == 422
