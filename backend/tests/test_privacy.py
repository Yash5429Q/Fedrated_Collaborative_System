"""
Tests for the privacy-preserving mechanisms.

Verifies:
  1. Raw data is never transmitted (only model parameters).
  2. Clipping bounds update norms correctly.
  3. DP noise is added with correct calibration.
  4. Server-side validation rejects malformed/anomalous updates.
  5. Privacy boundary behavior is observable via the event log.

Run with:  pytest tests/test_privacy.py -v
"""
from __future__ import annotations

import copy
import math

import numpy as np
import pytest

from app.ml.model import ThreatNet, get_parameters, set_parameters, train_model
from app.ml.data import load_partition, NUM_FEATURES
from app.ml.privacy import (
    DEFAULT_PRIVACY_CONFIG,
    PrivacyConfig,
    PrivacyLogger,
    ValidationResult,
    add_dp_noise,
    apply_privacy,
    clip_update,
    compute_update,
    compute_update_norm,
    privacy_logger,
    validate_update,
)


@pytest.fixture(autouse=True)
def clear_privacy_log():
    """Clear the global privacy logger before each test."""
    privacy_logger.clear()
    yield
    privacy_logger.clear()


# ── Test 1: Raw data is NOT transmitted ────────────────────────

class TestRawDataNeverTransmitted:
    """Verify that the privacy pipeline only outputs model parameters,
    never raw training data."""

    def test_apply_privacy_returns_only_parameters(self):
        """apply_privacy() returns List[np.ndarray] of model weights only."""
        model = ThreatNet()
        original = get_parameters(model)
        # Simulate training by slightly perturbing
        trained = [(p + np.random.randn(*p.shape).astype(np.float32) * 0.01) if p.ndim > 0 else p.copy() for p in original]

        config = PrivacyConfig(enable_clipping=True, enable_dp_noise=True, noise_multiplier=0.1)
        result = apply_privacy(original, trained, config, org_id="test-org", round_number=1)

        # Result must be a list of numpy arrays matching model structure
        assert isinstance(result, list)
        assert len(result) == len(original)
        for r, o in zip(result, original):
            assert isinstance(r, np.ndarray)
            assert r.shape == o.shape
            assert r.dtype == o.dtype

    def test_no_training_data_in_output(self):
        """The output of apply_privacy cannot contain raw feature vectors."""
        train_loader, _, _ = load_partition(partition_id=0, n_samples=500)
        model = ThreatNet()
        original = get_parameters(model)

        # Train the model
        train_model(model, train_loader, epochs=1)
        trained = get_parameters(model)

        config = DEFAULT_PRIVACY_CONFIG
        protected = apply_privacy(original, trained, config, org_id="test-org", round_number=1)

        # Collect all raw feature vectors from training data
        raw_features = []
        for X_batch, _ in train_loader:
            raw_features.append(X_batch.numpy())
        raw_data = np.vstack(raw_features)

        # Verify none of the protected parameter arrays match any raw data shape
        for p in protected:
            # Model params are weight matrices/bias vectors, not (N, 13) data arrays
            if p.ndim == 2 and p.shape[1] == NUM_FEATURES:
                # Even the first layer weight (64x13) should not contain raw samples
                for row in raw_data:
                    assert not np.allclose(p, row.reshape(1, -1), atol=1e-6), \
                        "Protected parameters contain raw training data!"

    def test_transmitted_params_differ_from_raw_trained(self):
        """Privacy-protected params must differ from the raw trained params."""
        model = ThreatNet()
        original = get_parameters(model)
        trained = [(p + np.random.randn(*p.shape).astype(np.float32) * 0.1) if p.ndim > 0 else p.copy() for p in original]

        config = PrivacyConfig(enable_clipping=True, clip_norm=0.5,
                               enable_dp_noise=True, noise_multiplier=0.5)
        protected = apply_privacy(original, trained, config, org_id="test-org", round_number=1)

        # At least some arrays should differ due to clipping + noise
        any_different = False
        for p, t in zip(protected, trained):
            if not np.allclose(p, t, atol=1e-8):
                any_different = True
                break
        assert any_different, "Protected params should differ from raw trained params"


# ── Test 2: Clipping ──────────────────────────────────────────

class TestClipping:
    def test_clip_reduces_large_update(self):
        """An update with norm > clip_norm should be scaled down."""
        # Create a large update
        update = [np.ones((64, 13), dtype=np.float32)]  # norm >> 1.0
        original_norm = compute_update_norm(update)
        assert original_norm > 1.0

        config = PrivacyConfig(enable_clipping=True, clip_norm=1.0, enable_dp_noise=False)
        clipped = clip_update(update, config, org_id="test", round_number=1)

        new_norm = compute_update_norm(clipped)
        assert new_norm <= 1.0 + 1e-6, f"Norm {new_norm} should be <= 1.0"

    def test_clip_preserves_small_update(self):
        """An update with norm <= clip_norm should not be changed."""
        update = [np.ones((3,), dtype=np.float32) * 0.01]
        config = PrivacyConfig(enable_clipping=True, clip_norm=10.0, enable_dp_noise=False)

        clipped = clip_update(update, config, org_id="test", round_number=1)
        for c, u in zip(clipped, update):
            np.testing.assert_array_almost_equal(c, u)

    def test_clip_disabled(self):
        """When clipping is disabled, update is returned unchanged."""
        update = [np.ones((100,), dtype=np.float32) * 100.0]
        config = PrivacyConfig(enable_clipping=False, enable_dp_noise=False)

        result = clip_update(update, config, org_id="test", round_number=1)
        for r, u in zip(result, update):
            np.testing.assert_array_equal(r, u)


# ── Test 3: DP Noise ──────────────────────────────────────────

class TestDPNoise:
    def test_noise_changes_update(self):
        """Adding noise should modify the update."""
        update = [np.zeros((64, 13), dtype=np.float32)]
        config = PrivacyConfig(enable_dp_noise=True, noise_multiplier=0.5, clip_norm=1.0,
                               enable_clipping=False)

        noised = add_dp_noise(update, config, org_id="test", round_number=1, seed=42)
        assert not np.allclose(noised[0], update[0]), "Noise should change the update"

    def test_noise_is_reproducible_with_seed(self):
        """Same seed should produce identical noise."""
        update = [np.zeros((10,), dtype=np.float32)]
        config = PrivacyConfig(enable_dp_noise=True, noise_multiplier=0.5, clip_norm=1.0,
                               enable_clipping=False)

        r1 = add_dp_noise(update, config, seed=123)
        r2 = add_dp_noise(update, config, seed=123)
        np.testing.assert_array_equal(r1[0], r2[0])

    def test_noise_disabled(self):
        """When noise is disabled, update is returned unchanged."""
        update = [np.ones((10,), dtype=np.float32)]
        config = PrivacyConfig(enable_dp_noise=False, enable_clipping=False)

        result = add_dp_noise(update, config)
        np.testing.assert_array_equal(result[0], update[0])

    def test_epsilon_computation(self):
        """Verify the epsilon calculation is correct."""
        config = PrivacyConfig(clip_norm=1.0, noise_multiplier=1.0)
        eps = config.epsilon(delta=1e-5)
        # epsilon = sqrt(2 * ln(1.25/1e-5)) * (1.0 / 1.0)
        expected = math.sqrt(2.0 * math.log(1.25 / 1e-5))
        assert abs(eps - expected) < 1e-6


# ── Test 4: Server-side validation ────────────────────────────

class TestValidation:
    def test_valid_update_passes(self):
        """A normal update should pass all validation checks."""
        model = ThreatNet()
        reference = get_parameters(model)
        update = [(p + np.random.randn(*p.shape).astype(np.float32) * 0.001) if p.ndim > 0 else p.copy() for p in reference]

        config = PrivacyConfig(enable_validation=True, max_update_norm=10.0, max_param_value=100.0)
        result = validate_update(update, reference, config, org_id="test", round_number=1)

        assert result.valid is True
        assert all(result.checks.values())

    def test_nan_update_rejected(self):
        """An update containing NaN should be rejected."""
        model = ThreatNet()
        reference = get_parameters(model)
        bad_update = copy.deepcopy(reference)
        bad_update[0][0, 0] = float("nan")

        config = PrivacyConfig(enable_validation=True)
        result = validate_update(bad_update, reference, config, org_id="test", round_number=1)

        assert result.valid is False
        assert result.checks["finite_values"] is False

    def test_inf_update_rejected(self):
        """An update containing Inf should be rejected."""
        model = ThreatNet()
        reference = get_parameters(model)
        bad_update = copy.deepcopy(reference)
        bad_update[0][0, 0] = float("inf")

        config = PrivacyConfig(enable_validation=True)
        result = validate_update(bad_update, reference, config, org_id="test", round_number=1)

        assert result.valid is False
        assert result.checks["finite_values"] is False

    def test_excessive_norm_rejected(self):
        """An update with very large norm should be rejected."""
        model = ThreatNet()
        reference = get_parameters(model)
        big_update = [p + np.ones_like(p) * 1000.0 for p in reference]

        config = PrivacyConfig(enable_validation=True, max_update_norm=1.0)
        result = validate_update(big_update, reference, config, org_id="test", round_number=1)

        assert result.valid is False
        assert result.checks["norm_bound"] is False

    def test_shape_mismatch_rejected(self):
        """An update with wrong layer count should be rejected."""
        model = ThreatNet()
        reference = get_parameters(model)
        short_update = reference[:2]  # missing layers

        config = PrivacyConfig(enable_validation=True)
        result = validate_update(short_update, reference, config, org_id="test", round_number=1)

        assert result.valid is False
        assert result.checks["structure"] is False

    def test_validation_disabled_always_passes(self):
        """With validation disabled, even bad updates pass."""
        model = ThreatNet()
        reference = get_parameters(model)
        bad_update = copy.deepcopy(reference)
        bad_update[0][0, 0] = float("nan")

        config = PrivacyConfig(enable_validation=False)
        result = validate_update(bad_update, reference, config, org_id="test", round_number=1)

        assert result.valid is True


# ── Test 5: Privacy boundary logging ──────────────────────────

class TestPrivacyLogging:
    def test_full_pipeline_logs_all_stages(self):
        """apply_privacy should log: update_creation, clipping, noise_addition, transmission."""
        model = ThreatNet()
        original = get_parameters(model)
        trained = [(p + np.random.randn(*p.shape).astype(np.float32) * 0.1) if p.ndim > 0 else p.copy() for p in original]

        config = PrivacyConfig(enable_clipping=True, enable_dp_noise=True, noise_multiplier=0.1)
        apply_privacy(original, trained, config, org_id="test-org", round_number=1)

        events = privacy_logger.get_events()
        stages = [e["stage"] for e in events]

        assert "update_creation" in stages
        assert "clipping" in stages
        assert "noise_addition" in stages
        assert "transmission" in stages

    def test_validation_logs_event(self):
        """validate_update should log a validation event."""
        model = ThreatNet()
        params = get_parameters(model)
        config = PrivacyConfig(enable_validation=True)

        validate_update(params, params, config, org_id="test-org", round_number=1)

        events = privacy_logger.get_events()
        stages = [e["stage"] for e in events]
        assert "validation" in stages

    def test_events_contain_org_and_round(self):
        """All events should record the org_id and round_number."""
        model = ThreatNet()
        original = get_parameters(model)
        trained = [(p + np.random.randn(*p.shape).astype(np.float32) * 0.01) if p.ndim > 0 else p.copy() for p in original]

        config = DEFAULT_PRIVACY_CONFIG
        apply_privacy(original, trained, config, org_id="org-alpha", round_number=5)

        for event in privacy_logger.get_events():
            assert event["org_id"] == "org-alpha"
            assert event["round_number"] == 5
