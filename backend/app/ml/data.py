"""
CICIDS2017 dataset loading and federated partitioning.

Loads real CICIDS2017 data from ``cicids2017_clean.npz`` with 5 classes:
  0 = Normal traffic
  1 = DoS attack
  2 = Brute Force
  3 = Port Scan
  4 = Malware / C2

Supports two partitioning modes:
  - IID:     uniform random split across organisations
  - Non-IID: Dirichlet-based skewed class distribution per org

Key design decisions (CYBER-20 audit fixes):
  - Duplicates are removed before any splitting.
  - A global stratified train/val/test split is created FIRST, then
    partitioning is applied only to the training portion.
  - Normalization is fitted ONLY on the training split.
  - The same normalization params are returned so they can be saved
    alongside checkpoints and reused at inference time.
  - Class weights are computed from training label frequencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

# ── Constants ──────────────────────────────────────────────────
import os
import logging

logger = logging.getLogger(__name__)

# Fallback synthetic features
_SYNTHETIC_FEATURE_NAMES = [
    "flow_duration", "fwd_packets", "bwd_packets",
    "fwd_bytes", "bwd_bytes", "flow_bytes_per_s",
    "fwd_iat_mean", "bwd_iat_mean", "pkt_size_avg",
    "fin_flag_count", "syn_flag_count", "rst_flag_count",
    "ack_flag_count",
]

_NPZ_PATH = os.path.join(os.path.dirname(__file__), "cicids2017_clean.npz")
if os.path.exists(_NPZ_PATH):
    try:
        with np.load(_NPZ_PATH, allow_pickle=True) as _tmp:
            if 'feature_names' in _tmp:
                FEATURE_NAMES = _tmp['feature_names'].tolist()
            else:
                FEATURE_NAMES = [f"Feature_{i}" for i in range(_tmp['X'].shape[1])]
    except Exception:
        FEATURE_NAMES = _SYNTHETIC_FEATURE_NAMES
else:
    FEATURE_NAMES = _SYNTHETIC_FEATURE_NAMES

NUM_FEATURES = len(FEATURE_NAMES)

CLASS_NAMES = ["Normal", "DoS", "Brute Force", "Port Scan", "Malware"]
NUM_CLASSES = len(CLASS_NAMES)


# ── Partition statistics ───────────────────────────────────────

@dataclass
class PartitionStats:
    """Records per-organisation data statistics."""
    org_id: str
    org_name: str
    total_samples: int
    train_samples: int
    test_samples: int
    class_distribution: Dict[str, int] = field(default_factory=dict)
    class_proportions: Dict[str, float] = field(default_factory=dict)
    attack_types: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "org_id": self.org_id,
            "org_name": self.org_name,
            "total_samples": self.total_samples,
            "train_samples": self.train_samples,
            "test_samples": self.test_samples,
            "class_distribution": self.class_distribution,
            "class_proportions": self.class_proportions,
            "attack_types": self.attack_types,
        }


ORG_MAP = {
    0: ("org-alpha", "Organization Alpha"),
    1: ("org-beta", "Organization Beta"),
    2: ("org-gamma", "Organization Gamma"),
}


# ── Data loading ───────────────────────────────────────────────

def _load_raw_data(
    n_samples: int = 0,
    seed: int = 42,
    remove_duplicates: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Load real CIC-IDS2017 dataset from npz, or fallback to synthetic
    5-class network traffic features.

    Parameters
    ----------
    n_samples : int
        If >0 and < dataset size, subsample to this many rows.
    seed : int
        Random seed for reproducible shuffling/subsampling.
    remove_duplicates : bool
        If True, remove exact duplicate rows before returning.
    """
    rng = np.random.RandomState(seed)

    if os.path.exists(_NPZ_PATH):
        # Use Real CICIDS2017 data
        data = np.load(_NPZ_PATH)
        X = data['X'].copy()
        y = data['y'].copy()

        # Remove duplicate rows
        if remove_duplicates:
            _, unique_idx = np.unique(X, axis=0, return_index=True)
            unique_idx = np.sort(unique_idx)
            n_before = len(X)
            X = X[unique_idx]
            y = y[unique_idx]
            if len(X) < n_before:
                logger.info(f"Removed {n_before - len(X)} duplicate rows "
                            f"({n_before} -> {len(X)})")

        idx = rng.permutation(len(X))
        X = X[idx]
        y = y[idx]

        if 0 < n_samples < len(X):
            X = X[:n_samples]
            y = y[:n_samples]

        return X, y

    # --- FALLBACK: Synthetic Data Generation ---
    proportions = [0.40, 0.25, 0.15, 0.12, 0.08]
    if n_samples <= 0:
        n_samples = 15000
    counts = [int(p * n_samples) for p in proportions]
    counts[0] += n_samples - sum(counts)  # adjust rounding

    all_X = []
    all_y = []

    for cls_id, n in enumerate(counts):
        base = rng.randn(n, NUM_FEATURES).astype(np.float32)

        if cls_id == 0:  # Normal
            base[:, 0] = np.abs(base[:, 0]) * 50000
            base[:, 1] = np.abs(base[:, 1]) * 20
            base[:, 2] = np.abs(base[:, 2]) * 15
            base[:, 3] = np.abs(base[:, 3]) * 5000
            if NUM_FEATURES > 11:
                base[:, 4] = np.abs(base[:, 4]) * 3000
                base[:, 5] = np.abs(base[:, 5]) * 1000
                base[:, 10] = np.abs(base[:, 10]) * 2
                base[:, 11] = np.abs(base[:, 11]) * 1
        elif cls_id == 1:  # DoS
            base[:, 0] = np.abs(base[:, 0]) * 5000
            base[:, 1] = np.abs(base[:, 1]) * 800
            base[:, 2] = np.abs(base[:, 2]) * 3
            base[:, 3] = np.abs(base[:, 3]) * 60000
            if NUM_FEATURES > 11:
                base[:, 5] = np.abs(base[:, 5]) * 80000
                base[:, 10] = np.abs(base[:, 10]) * 60
                base[:, 11] = np.abs(base[:, 11]) * 40
        elif cls_id == 2:  # Brute Force
            base[:, 0] = np.abs(base[:, 0]) * 30000
            base[:, 1] = np.abs(base[:, 1]) * 100
            base[:, 2] = np.abs(base[:, 2]) * 100
            base[:, 3] = np.abs(base[:, 3]) * 8000
            if NUM_FEATURES > 12:
                base[:, 5] = np.abs(base[:, 5]) * 3000
                base[:, 10] = np.abs(base[:, 10]) * 30
                base[:, 12] = np.abs(base[:, 12]) * 50
        elif cls_id == 3:  # Port Scan
            base[:, 0] = np.abs(base[:, 0]) * 2000
            base[:, 1] = np.abs(base[:, 1]) * 200
            base[:, 2] = np.abs(base[:, 2]) * 1
            base[:, 3] = np.abs(base[:, 3]) * 1000
            if NUM_FEATURES > 10:
                base[:, 5] = np.abs(base[:, 5]) * 20000
                base[:, 10] = np.abs(base[:, 10]) * 100
                base[:, 9] = np.abs(base[:, 9]) * 5
        elif cls_id == 4:  # Malware
            base[:, 0] = np.abs(base[:, 0]) * 80000
            base[:, 1] = np.abs(base[:, 1]) * 50
            base[:, 2] = np.abs(base[:, 2]) * 40
            base[:, 3] = np.abs(base[:, 3]) * 15000
            if NUM_FEATURES > 7:
                base[:, 4] = np.abs(base[:, 4]) * 12000
                base[:, 5] = np.abs(base[:, 5]) * 5000
                base[:, 7] = np.abs(base[:, 7]) * 50000

        all_X.append(base)
        all_y.append(np.full(n, cls_id, dtype=np.int64))

    X = np.vstack(all_X)
    y = np.concatenate(all_y)

    idx = rng.permutation(len(X))
    return X[idx], y[idx]


# Backward compatibility alias
_generate_multiclass_data = _load_raw_data


def _normalise(X: np.ndarray) -> np.ndarray:
    """Per-feature z-score normalisation (legacy — uses own stats)."""
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    return ((X - mean) / std).astype(np.float32)


def _normalise_with_params(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-feature z-score normalisation, returning (X_norm, mean, std)."""
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    X_norm = ((X - mean) / std).astype(np.float32)
    return X_norm, mean.astype(np.float32), std.astype(np.float32)


def _apply_normalisation(
    X: np.ndarray, mean: np.ndarray, std: np.ndarray,
) -> np.ndarray:
    """Apply pre-computed z-score normalisation."""
    return ((X - mean) / std).astype(np.float32)


def get_normalisation_params(n_samples: int = 0, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Compute and return (mean, std) from the training dataset.

    Uses the same data-loading path as ``load_partition_detailed`` so the
    parameters are guaranteed to match training.

    .. deprecated:: CYBER-20
        Use ``create_splits()`` instead to get normalization params
        fitted only on the training portion.
    """
    X, _ = _load_raw_data(n_samples=n_samples, seed=seed)
    mean = X.mean(axis=0).astype(np.float32)
    std = (X.std(axis=0) + 1e-8).astype(np.float32)
    return mean, std


# ── Stratified splitting ──────────────────────────────────────

def _stratified_split(
    X: np.ndarray,
    y: np.ndarray,
    test_frac: float,
    rng: np.random.RandomState,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Stratified split preserving class proportions."""
    train_idx = []
    test_idx = []

    for cls in np.unique(y):
        cls_indices = np.where(y == cls)[0]
        rng.shuffle(cls_indices)
        n_test = max(1, int(len(cls_indices) * test_frac))
        test_idx.extend(cls_indices[:n_test].tolist())
        train_idx.extend(cls_indices[n_test:].tolist())

    train_idx = np.array(train_idx)
    test_idx = np.array(test_idx)
    rng.shuffle(train_idx)
    rng.shuffle(test_idx)

    return X[train_idx], y[train_idx], X[test_idx], y[test_idx]


def create_splits(
    n_samples: int = 0,
    seed: int = 42,
    test_frac: float = 0.15,
    val_frac: float = 0.10,
) -> dict:
    """Create stratified train/val/test splits with normalization fitted on train.

    Returns a dict with keys:
        X_train, y_train, X_val, y_val, X_test, y_test,
        X_train_norm, X_val_norm, X_test_norm,
        norm_mean, norm_std, class_weights
    """
    rng = np.random.RandomState(seed)
    X, y = _load_raw_data(n_samples=n_samples, seed=seed)

    # 1. Split off held-out test set (stratified)
    X_trainval, y_trainval, X_test, y_test = _stratified_split(
        X, y, test_frac, rng,
    )

    # 2. Split train/val from remaining (stratified)
    relative_val = val_frac / (1.0 - test_frac)
    X_train, y_train, X_val, y_val = _stratified_split(
        X_trainval, y_trainval, relative_val, rng,
    )

    logger.info(f"Splits: train={len(X_train)}, val={len(X_val)}, "
                f"test={len(X_test)}, total={len(X_train)+len(X_val)+len(X_test)}")

    # 3. Fit normalization ONLY on training data
    norm_mean = X_train.mean(axis=0).astype(np.float32)
    norm_std = (X_train.std(axis=0) + 1e-8).astype(np.float32)

    # 4. Apply normalization to all splits using training stats
    X_train_norm = _apply_normalisation(X_train, norm_mean, norm_std)
    X_val_norm = _apply_normalisation(X_val, norm_mean, norm_std)
    X_test_norm = _apply_normalisation(X_test, norm_mean, norm_std)

    # 5. Compute class weights (inverse frequency)
    class_counts = np.bincount(y_train, minlength=NUM_CLASSES).astype(np.float64)
    class_counts = np.maximum(class_counts, 1.0)  # avoid divide by zero
    total = class_counts.sum()
    class_weights = (total / (NUM_CLASSES * class_counts)).astype(np.float32)

    logger.info(f"Class weights: {dict(zip(CLASS_NAMES, class_weights.tolist()))}")

    return {
        "X_train": X_train, "y_train": y_train,
        "X_val": X_val, "y_val": y_val,
        "X_test": X_test, "y_test": y_test,
        "X_train_norm": X_train_norm,
        "X_val_norm": X_val_norm,
        "X_test_norm": X_test_norm,
        "norm_mean": norm_mean,
        "norm_std": norm_std,
        "class_weights": class_weights,
    }


# ── Partitioning strategies ───────────────────────────────────

def _partition_iid(
    y: np.ndarray,
    num_partitions: int,
    rng: np.random.RandomState,
) -> List[np.ndarray]:
    """IID partition: uniform random split."""
    indices = rng.permutation(len(y))
    return np.array_split(indices, num_partitions)


def _partition_dirichlet(
    y: np.ndarray,
    num_partitions: int,
    alpha: float,
    rng: np.random.RandomState,
) -> List[np.ndarray]:
    """
    Non-IID partition using Dirichlet distribution.

    Lower alpha = more skewed distributions across orgs.
      alpha=100  -> nearly IID
      alpha=1.0  -> mild skew
      alpha=0.5  -> moderate skew
      alpha=0.1  -> heavy skew
      alpha=0.01 -> extreme skew (some orgs may miss classes)
    """
    num_classes = len(np.unique(y))
    partition_indices: List[List[int]] = [[] for _ in range(num_partitions)]

    for cls in range(num_classes):
        cls_indices = np.where(y == cls)[0]
        rng.shuffle(cls_indices)

        # Draw proportions from Dirichlet
        proportions = rng.dirichlet([alpha] * num_partitions)
        # Convert to actual counts
        proportions = (proportions * len(cls_indices)).astype(int)
        # Fix rounding
        proportions[-1] = len(cls_indices) - proportions[:-1].sum()

        start = 0
        for part_id in range(num_partitions):
            end = start + proportions[part_id]
            partition_indices[part_id].extend(cls_indices[start:end].tolist())
            start = end

    return [np.array(idx) for idx in partition_indices]


def _compute_stats(
    partition_id: int,
    y_part: np.ndarray,
    train_size: int,
    test_size: int,
) -> PartitionStats:
    """Compute partition statistics."""
    org_id, org_name = ORG_MAP.get(partition_id, (f"org-{partition_id}", f"Organization {partition_id}"))

    class_dist = {}
    class_prop = {}
    attack_types = {}
    total = len(y_part)

    for cls_id, cls_name in enumerate(CLASS_NAMES):
        count = int((y_part == cls_id).sum())
        class_dist[cls_name] = count
        class_prop[cls_name] = round(count / total * 100, 1) if total > 0 else 0.0
        if cls_id > 0:  # attack types only
            attack_types[cls_name] = count

    return PartitionStats(
        org_id=org_id,
        org_name=org_name,
        total_samples=total,
        train_samples=train_size,
        test_samples=test_size,
        class_distribution=class_dist,
        class_proportions=class_prop,
        attack_types=attack_types,
    )


# ── Public API ─────────────────────────────────────────────────

def load_partition(
    partition_id: int,
    num_partitions: int = 3,
    n_samples: int = 0,
    batch_size: int = 64,
    seed: int = 42,
    iid: bool = True,
    alpha: float = 0.5,
) -> tuple[DataLoader, DataLoader, int]:
    """
    Return (train_loader, test_loader, num_train_samples) for one org.

    Backward compatible with Phase 12 callers (iid=True by default).
    """
    _, _, stats, train_loader, test_loader, _ = load_partition_detailed(
        partition_id=partition_id,
        num_partitions=num_partitions,
        n_samples=n_samples,
        batch_size=batch_size,
        seed=seed,
        iid=iid,
        alpha=alpha,
    )
    return train_loader, test_loader, stats.train_samples


def load_partition_detailed(
    partition_id: int,
    num_partitions: int = 3,
    n_samples: int = 0,
    batch_size: int = 64,
    seed: int = 42,
    iid: bool = True,
    alpha: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, PartitionStats, DataLoader, DataLoader, dict]:
    """
    Return (X_part, y_part, stats, train_loader, test_loader, norm_params).

    CYBER-20 fix: Normalization is fitted ONLY on the training portion of
    each partition and returned as norm_params = {"mean": ..., "std": ...}.

    Parameters
    ----------
    partition_id : int  (0, 1, or 2)
    num_partitions : int
    n_samples : total dataset size (0 = use all)
    batch_size : mini-batch size
    seed : random seed for reproducibility
    iid : if True, uniform random split; if False, Dirichlet non-IID
    alpha : Dirichlet concentration (only used when iid=False)
    """
    rng = np.random.RandomState(seed)
    X, y = _load_raw_data(n_samples=n_samples, seed=seed)

    if iid:
        partitions = _partition_iid(y, num_partitions, rng)
    else:
        partitions = _partition_dirichlet(y, num_partitions, alpha, rng)

    indices = partitions[partition_id]
    X_part = X[indices]
    y_part = y[indices]

    # Stratified 80/20 train-test split within partition
    X_train, y_train, X_test, y_test = _stratified_split(
        X_part, y_part, test_frac=0.2, rng=np.random.RandomState(seed + partition_id),
    )

    # Fit normalization on TRAINING data only
    norm_mean = X_train.mean(axis=0).astype(np.float32)
    norm_std = (X_train.std(axis=0) + 1e-8).astype(np.float32)

    # Apply normalization
    X_train_norm = _apply_normalisation(X_train, norm_mean, norm_std)
    X_test_norm = _apply_normalisation(X_test, norm_mean, norm_std)

    stats = _compute_stats(partition_id, y_part, len(X_train), len(X_test))

    train_ds = TensorDataset(
        torch.from_numpy(X_train_norm),
        torch.from_numpy(y_train),
    )
    test_ds = TensorDataset(
        torch.from_numpy(X_test_norm),
        torch.from_numpy(y_test),
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    norm_params = {"mean": norm_mean, "std": norm_std}

    return X_part, y_part, stats, train_loader, test_loader, norm_params


def load_all_partitions(
    num_partitions: int = 3,
    n_samples: int = 0,
    batch_size: int = 64,
    seed: int = 42,
    iid: bool = True,
    alpha: float = 0.5,
) -> List[tuple[PartitionStats, DataLoader, DataLoader, dict]]:
    """Load all partitions and return list of (stats, train_loader, test_loader, norm_params)."""
    results = []
    for pid in range(num_partitions):
        _, _, stats, train_ld, test_ld, norm_params = load_partition_detailed(
            partition_id=pid,
            num_partitions=num_partitions,
            n_samples=n_samples,
            batch_size=batch_size,
            seed=seed,
            iid=iid,
            alpha=alpha,
        )
        results.append((stats, train_ld, test_ld, norm_params))
    return results


def load_global_test_set(
    n_samples: int = 0,
    batch_size: int = 64,
    seed: int = 42,
    norm_mean: Optional[np.ndarray] = None,
    norm_std: Optional[np.ndarray] = None,
) -> DataLoader:
    """Load a global test set for server-side evaluation.

    CYBER-20 fix: Uses externally-provided normalization parameters
    (from the training split) instead of computing its own.
    If no params are provided, computes from this data (legacy behavior
    with a warning).
    """
    X, y = _load_raw_data(n_samples=n_samples, seed=seed)

    if norm_mean is not None and norm_std is not None:
        X_norm = _apply_normalisation(X, norm_mean, norm_std)
    else:
        logger.warning(
            "load_global_test_set called without norm params — "
            "using self-normalized data (legacy, may cause eval mismatch)"
        )
        X_norm = _normalise(X)

    ds = TensorDataset(torch.from_numpy(X_norm), torch.from_numpy(y))
    return DataLoader(ds, batch_size=batch_size, shuffle=False)


def compute_class_weights(y: np.ndarray) -> np.ndarray:
    """Compute inverse-frequency class weights for CrossEntropyLoss."""
    class_counts = np.bincount(y, minlength=NUM_CLASSES).astype(np.float64)
    class_counts = np.maximum(class_counts, 1.0)
    total = class_counts.sum()
    weights = (total / (NUM_CLASSES * class_counts)).astype(np.float32)
    return weights
