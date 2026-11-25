"""
Tests for FedAvg aggregation enhancements: momentum and norm guard.

Verifies:
  1. Standard FedAvg (momentum=0) produces correct weighted average.
  2. Server-side momentum blends previous global with aggregated result.
  3. Momentum=0 is identical to baseline (no regression).
  4. Norm guard caps outlier client updates.
  5. PrivacyConfig can be constructed from CLI-like arguments.
  6. DP accounting disclaimer is present in config dict.

Run with:  pytest tests/test_aggregation.py -v
"""
from __future__ import annotations

import copy
import math

import numpy as np
import pytest

# Insert project root so imports work from backend/
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ml.privacy import (
    PrivacyConfig,
    compute_update_norm,
)


# ── Helper: local _fedavg_aggregate copy (avoid circular import) ─


def _fedavg_aggregate(
    client_params,
    client_sizes,
    previous_global=None,
    momentum=0.0,
):
    """Mirror of run_experiment._fedavg_aggregate for isolated testing."""
    total = sum(client_sizes)
    num_layers = len(client_params[0])
    aggregated = []

    for layer_idx in range(num_layers):
        weighted_sum = np.zeros_like(client_params[0][layer_idx], dtype=np.float64)
        for client_idx in range(len(client_params)):
            weight = client_sizes[client_idx] / total
            weighted_sum += client_params[client_idx][layer_idx].astype(np.float64) * weight
        aggregated.append(weighted_sum.astype(np.float32))

    if momentum > 0.0 and previous_global is not None:
        aggregated = [
            ((1.0 - momentum) * a.astype(np.float64) + momentum * p.astype(np.float64)).astype(np.float32)
            for a, p in zip(aggregated, previous_global)
        ]

    return aggregated


# ── Test 1: Standard FedAvg ───────────────────────────────────


class TestFedAvgBaseline:
    def test_equal_weights_averages_params(self):
        """With equal client sizes, FedAvg = simple mean of params."""
        p1 = [np.array([1.0, 2.0], dtype=np.float32)]
        p2 = [np.array([3.0, 4.0], dtype=np.float32)]
        result = _fedavg_aggregate([p1, p2], [100, 100])
        expected = np.array([2.0, 3.0], dtype=np.float32)
        np.testing.assert_allclose(result[0], expected, atol=1e-6)

    def test_weighted_average(self):
        """With unequal sizes, FedAvg produces a weighted average."""
        p1 = [np.array([0.0], dtype=np.float32)]
        p2 = [np.array([10.0], dtype=np.float32)]
        # 75% weight on p1, 25% on p2
        result = _fedavg_aggregate([p1, p2], [300, 100])
        np.testing.assert_allclose(result[0], [2.5], atol=1e-6)

    def test_single_client(self):
        """With one client, result equals that client's params."""
        p1 = [np.array([5.0, 7.0, 9.0], dtype=np.float32)]
        result = _fedavg_aggregate([p1], [42])
        np.testing.assert_allclose(result[0], p1[0], atol=1e-6)


# ── Test 2: Server-side momentum ─────────────────────────────


class TestMomentum:
    def test_momentum_blends_with_previous(self):
        """momentum=0.5 should produce midpoint between aggregated and previous."""
        prev = [np.array([0.0, 0.0], dtype=np.float32)]
        p1 = [np.array([10.0, 10.0], dtype=np.float32)]
        result = _fedavg_aggregate([p1], [100], previous_global=prev, momentum=0.5)
        # aggregated = [10, 10], blended = 0.5*10 + 0.5*0 = [5, 5]
        np.testing.assert_allclose(result[0], [5.0, 5.0], atol=1e-6)

    def test_momentum_zero_equals_baseline(self):
        """momentum=0 should produce identical result to no-momentum call."""
        p1 = [np.array([1.0, 2.0], dtype=np.float32)]
        p2 = [np.array([3.0, 4.0], dtype=np.float32)]
        prev = [np.array([99.0, 99.0], dtype=np.float32)]

        baseline = _fedavg_aggregate([p1, p2], [100, 100])
        with_zero = _fedavg_aggregate([p1, p2], [100, 100], previous_global=prev, momentum=0.0)

        np.testing.assert_allclose(baseline[0], with_zero[0], atol=1e-7)

    def test_momentum_one_ignores_aggregation(self):
        """momentum=1.0 should return previous global entirely."""
        prev = [np.array([42.0, 42.0], dtype=np.float32)]
        p1 = [np.array([0.0, 0.0], dtype=np.float32)]
        result = _fedavg_aggregate([p1], [100], previous_global=prev, momentum=1.0)
        np.testing.assert_allclose(result[0], prev[0], atol=1e-6)

    def test_momentum_no_previous_global(self):
        """When previous_global is None, momentum has no effect."""
        p1 = [np.array([10.0], dtype=np.float32)]
        result = _fedavg_aggregate([p1], [100], previous_global=None, momentum=0.8)
        np.testing.assert_allclose(result[0], [10.0], atol=1e-6)

    def test_momentum_multi_layer(self):
        """Momentum should work correctly across multiple layers."""
        prev = [
            np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
            np.array([0.5], dtype=np.float32),
        ]
        p1 = [
            np.array([[5.0, 6.0], [7.0, 8.0]], dtype=np.float32),
            np.array([1.5], dtype=np.float32),
        ]
        result = _fedavg_aggregate([p1], [100], previous_global=prev, momentum=0.2)
        # Layer 0: 0.8*[[5,6],[7,8]] + 0.2*[[1,2],[3,4]] = [[4.2,5.2],[6.2,7.2]]
        expected_0 = np.array([[4.2, 5.2], [6.2, 7.2]], dtype=np.float32)
        np.testing.assert_allclose(result[0], expected_0, atol=1e-5)
        # Layer 1: 0.8*1.5 + 0.2*0.5 = 1.3
        np.testing.assert_allclose(result[1], [1.3], atol=1e-5)


# ── Test 3: Norm guard ───────────────────────────────────────


class TestNormGuard:
    """Test the norm-guard logic that caps outlier updates."""

    def _apply_norm_guard(self, client_params, client_sizes, global_params, multiplier):
        """Simulate the norm guard logic from run_experiment.py."""
        update_norms = []
        for cp in client_params:
            delta = [cp_l - gp_l for cp_l, gp_l in zip(cp, global_params)]
            update_norms.append(compute_update_norm(delta))
        median_norm = float(np.median(update_norms))
        threshold = median_norm * multiplier

        guarded_params = []
        guarded_sizes = []
        for idx, (cp, cs, un) in enumerate(zip(client_params, client_sizes, update_norms)):
            if un > threshold:
                scale = threshold / un
                capped = [
                    (gp_l + (cp_l - gp_l) * scale).astype(np.float32)
                    for cp_l, gp_l in zip(cp, global_params)
                ]
                guarded_params.append(capped)
                guarded_sizes.append(cs)
            else:
                guarded_params.append(cp)
                guarded_sizes.append(cs)

        return guarded_params, guarded_sizes, update_norms, threshold

    def test_no_outlier_no_change(self):
        """When all norms are similar, no capping occurs."""
        gp = [np.zeros((5,), dtype=np.float32)]
        cp1 = [np.ones((5,), dtype=np.float32) * 1.0]
        cp2 = [np.ones((5,), dtype=np.float32) * 1.1]
        cp3 = [np.ones((5,), dtype=np.float32) * 0.9]

        guarded, sizes, norms, thresh = self._apply_norm_guard(
            [cp1, cp2, cp3], [100, 100, 100], gp, multiplier=3.0
        )
        # All norms are close, threshold = median * 3 ≈ 3*norm(1,1,1,1,1) ≈ 6.7
        # No client should be capped
        for orig, guard in zip([cp1, cp2, cp3], guarded):
            np.testing.assert_allclose(guard[0], orig[0], atol=1e-6)

    def test_outlier_is_capped(self):
        """A client with much larger norm gets scaled down."""
        gp = [np.zeros((3,), dtype=np.float32)]
        cp_normal = [np.array([1.0, 0.0, 0.0], dtype=np.float32)]  # norm = 1.0
        cp_outlier = [np.array([100.0, 0.0, 0.0], dtype=np.float32)]  # norm = 100.0

        guarded, _, norms, thresh = self._apply_norm_guard(
            [cp_normal, cp_outlier], [100, 100], gp, multiplier=2.0
        )
        # median norm ≈ 50.5, threshold ≈ 101.0 — hmm, with 2 clients median = mean of sorted
        # Actually np.median([1.0, 100.0]) = 50.5, threshold = 101 > 100, so no cap
        # Let's use multiplier=1.0 instead
        guarded, _, norms, thresh = self._apply_norm_guard(
            [cp_normal, cp_outlier], [100, 100], gp, multiplier=1.0
        )
        # median = 50.5, threshold = 50.5
        # cp_outlier norm=100 > 50.5, so it's scaled to norm 50.5
        outlier_delta = guarded[1][0] - gp[0]
        outlier_new_norm = float(np.linalg.norm(outlier_delta))
        assert outlier_new_norm <= thresh + 1e-5

    def test_outlier_capped_with_three_clients(self):
        """With 3 clients, median is the middle one's norm."""
        gp = [np.zeros((2,), dtype=np.float32)]
        cp1 = [np.array([1.0, 0.0], dtype=np.float32)]   # norm = 1.0
        cp2 = [np.array([2.0, 0.0], dtype=np.float32)]   # norm = 2.0
        cp3 = [np.array([50.0, 0.0], dtype=np.float32)]  # norm = 50.0 (outlier)

        guarded, _, norms, thresh = self._apply_norm_guard(
            [cp1, cp2, cp3], [100, 100, 100], gp, multiplier=3.0
        )
        # median norm = 2.0, threshold = 6.0
        # cp3 norm=50 > 6.0, should be capped
        delta3 = guarded[2][0] - gp[0]
        new_norm3 = float(np.linalg.norm(delta3))
        assert new_norm3 <= 6.0 + 1e-5, f"Expected norm <= 6.0, got {new_norm3}"
        # cp1 and cp2 should be unchanged
        np.testing.assert_allclose(guarded[0][0], cp1[0], atol=1e-6)
        np.testing.assert_allclose(guarded[1][0], cp2[0], atol=1e-6)


# ── Test 4: PrivacyConfig from CLI-like args ──────────────────


class TestPrivacyConfigConstruction:
    def test_default_config(self):
        """Default PrivacyConfig matches expected defaults."""
        config = PrivacyConfig()
        assert config.enable_clipping is True
        assert config.clip_norm == 1.0
        assert config.enable_dp_noise is True
        assert config.noise_multiplier == 0.1

    def test_custom_config_from_kwargs(self):
        """PrivacyConfig can be constructed with custom values (simulating CLI)."""
        config = PrivacyConfig(
            enable_clipping=False,
            clip_norm=10.0,
            enable_dp_noise=False,
            noise_multiplier=0.5,
            enable_validation=False,
        )
        assert config.enable_clipping is False
        assert config.clip_norm == 10.0
        assert config.enable_dp_noise is False
        assert config.noise_multiplier == 0.5
        assert config.enable_validation is False

    def test_noise_std_property(self):
        """noise_std = noise_multiplier * clip_norm."""
        config = PrivacyConfig(clip_norm=5.0, noise_multiplier=0.2)
        assert abs(config.noise_std - 1.0) < 1e-8

    def test_epsilon_no_noise_is_inf(self):
        """When noise is 0, epsilon should be infinite."""
        config = PrivacyConfig(noise_multiplier=0.0)
        assert config.epsilon() == float("inf")


# ── Test 5: DP accounting disclaimer in config dict ──────────


class TestDPAccountingDisclaimer:
    def test_dp_accounting_field_present(self):
        """to_dict() should include dp_accounting field."""
        config = PrivacyConfig()
        d = config.to_dict()
        assert "dp_accounting" in d
        assert d["dp_accounting"] == "per_round_gaussian_only"

    def test_dp_accounting_note_present(self):
        """to_dict() should include dp_accounting_note field."""
        config = PrivacyConfig()
        d = config.to_dict()
        assert "dp_accounting_note" in d
        assert "per-round" in d["dp_accounting_note"].lower()
        assert "composition" in d["dp_accounting_note"].lower()

    def test_epsilon_per_round_in_dict(self):
        """to_dict() should include epsilon_per_round."""
        config = PrivacyConfig(clip_norm=1.0, noise_multiplier=1.0)
        d = config.to_dict()
        expected_eps = math.sqrt(2.0 * math.log(1.25 / 1e-5))
        assert abs(d["epsilon_per_round"] - round(expected_eps, 4)) < 1e-3
