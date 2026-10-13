"""
Privacy-preserving mechanisms for federated model updates.

Implements:
  1. Update Clipping — L2 norm clipping to bound individual contribution sensitivity.
  2. Differential Privacy — Gaussian noise calibrated to the clipping bound.
  3. Update Validation — Server-side structural and anomaly checks on incoming updates.

These mechanisms operate on model parameter arrays (List[np.ndarray]) —
the format used by Flower's NumPyClient for weight transmission.

Privacy guarantees:
  - Raw training data NEVER leaves the client.
  - Only model weight updates (clipped + noised) are transmitted.
  - The server validates update structure before aggregation.
  - The Gaussian noise provides (epsilon, delta)-differential privacy per round.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("privacy")


# ── Privacy configuration ──────────────────────────────────────

@dataclass
class PrivacyConfig:
    """
    Configuration for the privacy-preserving layer.

    Attributes
    ----------
    enable_clipping : bool
        Whether to clip model updates by L2 norm.
    clip_norm : float
        Maximum L2 norm for update clipping (sensitivity bound).
    enable_dp_noise : bool
        Whether to add Gaussian noise for differential privacy.
    noise_multiplier : float
        Ratio of noise std to clip_norm. Higher = more privacy, less utility.
        noise_std = noise_multiplier * clip_norm
    enable_validation : bool
        Whether the server validates incoming updates before aggregation.
    max_update_norm : float
        Server-side threshold: reject updates whose L2 norm exceeds this.
    max_param_value : float
        Server-side threshold: reject updates containing any value above this.
    """
    enable_clipping: bool = True
    clip_norm: float = 1.0
    enable_dp_noise: bool = True
    noise_multiplier: float = 0.1
    enable_validation: bool = True
    max_update_norm: float = 10.0
    max_param_value: float = 100.0

    @property
    def noise_std(self) -> float:
        return self.noise_multiplier * self.clip_norm

    def epsilon(self, delta: float = 1e-5) -> float:
        """
        Compute approximate per-round (epsilon, delta)-DP.

        Uses the Gaussian mechanism bound:
          epsilon = sqrt(2 * ln(1.25/delta)) * (sensitivity / noise_std)
        where sensitivity = clip_norm (L2 sensitivity after clipping).
        """
        if self.noise_std <= 0:
            return float("inf")
        return math.sqrt(2.0 * math.log(1.25 / delta)) * (self.clip_norm / self.noise_std)

    def to_dict(self) -> dict:
        return {
            "clipping_enabled": self.enable_clipping,
            "clip_norm": self.clip_norm,
            "dp_noise_enabled": self.enable_dp_noise,
            "noise_multiplier": self.noise_multiplier,
            "noise_std": round(self.noise_std, 6),
            "epsilon_per_round": round(self.epsilon(), 4),
            "delta": 1e-5,
            "validation_enabled": self.enable_validation,
            "max_update_norm": self.max_update_norm,
            "max_param_value": self.max_param_value,
        }


# ── Privacy event log ──────────────────────────────────────────

@dataclass
class PrivacyEvent:
    """A single logged privacy-related event."""
    stage: str          # "update_creation", "clipping", "noise_addition", "transmission", "validation", "aggregation"
    org_id: str
    round_number: int
    action: str         # Human-readable description
    details: Dict = field(default_factory=dict)


class PrivacyLogger:
    """Collects privacy events during FL rounds."""

    def __init__(self) -> None:
        self.events: List[PrivacyEvent] = []

    def log(self, stage: str, org_id: str, round_number: int, action: str, **details) -> None:
        event = PrivacyEvent(
            stage=stage, org_id=org_id, round_number=round_number,
            action=action, details=details,
        )
        self.events.append(event)
        logger.info(f"[Privacy] [{stage}] org={org_id} round={round_number}: {action}")
        if details:
            for k, v in details.items():
                logger.debug(f"  {k}: {v}")

    def get_events(self) -> List[dict]:
        return [
            {
                "stage": e.stage,
                "org_id": e.org_id,
                "round_number": e.round_number,
                "action": e.action,
                **e.details,
            }
            for e in self.events
        ]

    def clear(self) -> None:
        self.events.clear()


# Singleton
privacy_logger = PrivacyLogger()


# ── Client-side: Update creation & protection ──────────────────

def compute_update(
    original_params: List[np.ndarray],
    trained_params: List[np.ndarray],
) -> List[np.ndarray]:
    """
    Compute the model update (delta) between original and trained parameters.
    This is the raw gradient-like update before any privacy transformation.
    """
    return [np.asarray(t - o, dtype=o.dtype) for o, t in zip(original_params, trained_params)]


def compute_update_norm(update: List[np.ndarray], mask: Optional[List[bool]] = None) -> float:
    """Compute the L2 norm of a flattened update vector.
    
    If mask is provided, only include elements where mask[i] is True.
    """
    if mask is not None:
        parts = [u.flatten() for u, m in zip(update, mask) if m]
    else:
        parts = [u.flatten() for u in update]
    if not parts:
        return 0.0
    flat = np.concatenate(parts)
    return float(np.linalg.norm(flat))


def clip_update(
    update: List[np.ndarray],
    config: PrivacyConfig,
    org_id: str = "",
    round_number: int = 0,
    mask: Optional[List[bool]] = None,
) -> List[np.ndarray]:
    """
    Clip the model update to bound its L2 norm.

    If ||update||_2 > clip_norm, scale it down to clip_norm.
    This is the sensitivity bound for the Gaussian mechanism.
    
    If mask is provided, only clip/scale the learnable parameters
    (mask[i]=True), leaving BN buffers unchanged.
    """
    if not config.enable_clipping:
        return update

    norm = compute_update_norm(update, mask)
    privacy_logger.log(
        "clipping", org_id, round_number,
        f"Update norm before clipping: {norm:.6f}",
        original_norm=round(norm, 6),
        clip_norm=config.clip_norm,
    )

    if norm > config.clip_norm:
        scale = config.clip_norm / norm
        if mask is not None:
            clipped = [np.asarray(u * scale, dtype=u.dtype) if m else u for u, m in zip(update, mask)]
        else:
            clipped = [np.asarray(u * scale, dtype=u.dtype) for u in update]
        new_norm = compute_update_norm(clipped, mask)
        privacy_logger.log(
            "clipping", org_id, round_number,
            f"Clipped: {norm:.6f} -> {new_norm:.6f} (scale={scale:.6f})",
            clipped=True,
            new_norm=round(new_norm, 6),
            scale_factor=round(scale, 6),
        )
        return clipped
    else:
        privacy_logger.log(
            "clipping", org_id, round_number,
            f"No clipping needed (norm {norm:.6f} <= {config.clip_norm})",
            clipped=False,
        )
        return update


def add_dp_noise(
    update: List[np.ndarray],
    config: PrivacyConfig,
    org_id: str = "",
    round_number: int = 0,
    seed: Optional[int] = None,
    mask: Optional[List[bool]] = None,
) -> List[np.ndarray]:
    """
    Add calibrated Gaussian noise to the model update for differential privacy.

    noise ~ N(0, noise_std^2 * I)
    where noise_std = noise_multiplier * clip_norm
    
    If mask is provided, only add noise to learnable parameters.
    """
    if not config.enable_dp_noise:
        return update

    rng = np.random.RandomState(seed)
    noise_std = config.noise_std

    privacy_logger.log(
        "noise_addition", org_id, round_number,
        f"Adding Gaussian noise (std={noise_std:.6f}, epsilon={config.epsilon():.4f})",
        noise_std=round(noise_std, 6),
        epsilon=round(config.epsilon(), 4),
        delta=1e-5,
    )

    noised = []
    total_noise_norm = 0.0
    for i, u in enumerate(update):
        if mask is not None and not mask[i]:
            noised.append(u)  # Skip noise for BN buffers
            continue
        noise = np.asarray(rng.normal(0.0, noise_std, size=u.shape), dtype=u.dtype)
        total_noise_norm += float(np.linalg.norm(noise.flatten()) ** 2)
        noised.append(np.asarray(u + noise, dtype=u.dtype))

    total_noise_norm = math.sqrt(total_noise_norm)
    new_norm = compute_update_norm(noised, mask)
    privacy_logger.log(
        "noise_addition", org_id, round_number,
        f"Noise applied: noise_norm={total_noise_norm:.6f}, update_norm_after={new_norm:.6f}",
        noise_norm=round(total_noise_norm, 6),
        update_norm_after=round(new_norm, 6),
    )

    return noised


def apply_privacy(
    original_params: List[np.ndarray],
    trained_params: List[np.ndarray],
    config: PrivacyConfig,
    org_id: str = "",
    round_number: int = 0,
    seed: Optional[int] = None,
    learnable_mask: Optional[List[bool]] = None,
) -> List[np.ndarray]:
    """
    Full client-side privacy pipeline:
      1. Compute update (delta)
      2. Clip update (learnable params only)
      3. Add DP noise (learnable params only)
      4. Reconstruct parameters (original + protected_delta)

    Returns the privacy-protected model parameters ready for transmission.
    
    If learnable_mask is provided, BN running buffers (mask[i]=False) are
    passed through without clipping or noise.
    """
    privacy_logger.log(
        "update_creation", org_id, round_number,
        "Computing model update (trained - original)",
    )

    update = compute_update(original_params, trained_params)
    update = clip_update(update, config, org_id, round_number, mask=learnable_mask)
    update = add_dp_noise(update, config, org_id, round_number, seed, mask=learnable_mask)

    # Reconstruct full parameters
    protected_params = [np.asarray(o + u, dtype=o.dtype) for o, u in zip(original_params, update)]

    privacy_logger.log(
        "transmission", org_id, round_number,
        "Privacy-protected parameters ready for transmission (raw data NOT included)",
        num_layers=len(protected_params),
        total_params=sum(p.size for p in protected_params),
    )

    return protected_params


# ── Server-side: Update validation ─────────────────────────────

@dataclass
class ValidationResult:
    """Result of server-side update validation."""
    valid: bool
    org_id: str
    round_number: int
    checks: Dict[str, bool] = field(default_factory=dict)
    reason: str = ""


def validate_update(
    update_params: List[np.ndarray],
    reference_params: List[np.ndarray],
    config: PrivacyConfig,
    org_id: str = "",
    round_number: int = 0,
    learnable_mask: Optional[List[bool]] = None,
) -> ValidationResult:
    """
    Server-side validation of incoming model updates.

    Checks:
      1. Structural match (same number of layers, same shapes)
      2. No NaN or Inf values
      3. Update norm within bounds (learnable params only)
      4. No extreme parameter values
    """
    if not config.enable_validation:
        return ValidationResult(valid=True, org_id=org_id, round_number=round_number,
                                checks={"validation_enabled": False}, reason="Validation disabled")

    checks = {}
    reasons = []

    # Check 1: Structural match
    if len(update_params) != len(reference_params):
        checks["structure"] = False
        reasons.append(f"Layer count mismatch: got {len(update_params)}, expected {len(reference_params)}")
    else:
        shapes_match = all(
            u.shape == r.shape for u, r in zip(update_params, reference_params)
        )
        checks["structure"] = shapes_match
        if not shapes_match:
            reasons.append("Layer shape mismatch detected")

    # Check 2: No NaN/Inf
    has_nan = any(np.isnan(u).any() for u in update_params)
    has_inf = any(np.isinf(u).any() for u in update_params)
    checks["finite_values"] = not (has_nan or has_inf)
    if has_nan:
        reasons.append("Update contains NaN values")
    if has_inf:
        reasons.append("Update contains Inf values")

    # Check 3: Update norm (only for learnable params, not BN buffers)
    delta = [u - r for u, r in zip(update_params, reference_params)]
    norm = compute_update_norm(delta, mask=learnable_mask)
    checks["norm_bound"] = norm <= config.max_update_norm
    if not checks["norm_bound"]:
        reasons.append(f"Update norm {norm:.4f} exceeds max {config.max_update_norm}")

    # Check 4: Extreme values (only check learnable params, not BN counters)
    if learnable_mask is not None:
        learnable_params = [u for u, m in zip(update_params, learnable_mask) if m]
    else:
        learnable_params = update_params
    max_val = max(float(np.abs(u).max()) for u in learnable_params) if learnable_params else 0.0
    checks["value_bound"] = max_val <= config.max_param_value
    if not checks["value_bound"]:
        reasons.append(f"Max parameter value {max_val:.4f} exceeds limit {config.max_param_value}")

    valid = all(checks.values())
    reason = "; ".join(reasons) if reasons else "All checks passed"

    action = f"Validation {'PASSED' if valid else 'REJECTED'}: {reason}"
    privacy_logger.log(
        "validation", org_id, round_number,
        action,
        valid=valid,
        checks=checks,
        update_norm=round(norm, 6),
        max_param_value=round(max_val, 6),
    )

    return ValidationResult(
        valid=valid,
        org_id=org_id,
        round_number=round_number,
        checks=checks,
        reason=reason,
    )


# ── Default configuration ─────────────────────────────────────

DEFAULT_PRIVACY_CONFIG = PrivacyConfig(
    enable_clipping=True,
    clip_norm=5.0,
    enable_dp_noise=True,
    noise_multiplier=0.1,
    enable_validation=True,
    max_update_norm=200.0,
    max_param_value=100.0,
)
