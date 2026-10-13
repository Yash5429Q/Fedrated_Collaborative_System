"""
PyTorch model for network-threat classification.

A Multi-Layer Perceptron that takes 68 flow features
and outputs 5-class predictions (Normal, DoS, Brute Force, Port Scan, Malware).
Also provides standalone train() and test() helper functions.

CYBER-20 improvements:
  - Wider MLP with BatchNorm for better feature normalization.
  - Class-weighted CrossEntropyLoss for imbalanced classes.
  - AdamW optimizer with cosine annealing LR scheduler.
  - Early stopping based on validation macro-F1.
  - Reproducible seeded initialization.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from app.ml.data import NUM_FEATURES, NUM_CLASSES, CLASS_NAMES


class ThreatNet(nn.Module):
    """MLP for multi-class threat detection.

    Architecture: 68 → 256 → BN → ReLU → Drop
                      → 128 → BN → ReLU → Drop
                      → 64  → BN → ReLU → Drop
                      → 5
    """

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(NUM_FEATURES, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(64, NUM_CLASSES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # BatchNorm requires batch_size > 1 during training.
        # If we get a single sample, duplicate it, run, then take the first.
        if self.training and x.size(0) == 1:
            x = x.repeat(2, 1)
            out = self.net(x)
            return out[:1]
        return self.net(x)


# ── Flower helper utilities ────────────────────────────────────

def get_parameters(model: nn.Module) -> List[np.ndarray]:
    """Extract model parameters as a list of NumPy arrays."""
    return [val.cpu().numpy() for _, val in model.state_dict().items()]


def set_parameters(model: nn.Module, parameters: List[np.ndarray]) -> None:
    """Load parameters from a list of NumPy arrays into the model."""
    params_dict = zip(model.state_dict().keys(), parameters)
    state_dict = OrderedDict(
        {k: torch.tensor(v) for k, v in params_dict}
    )
    model.load_state_dict(state_dict, strict=True)


def _bn_buffer_keys(model: nn.Module) -> set:
    """Return the set of state_dict keys that are BatchNorm running buffers."""
    bn_keys = set()
    for name, module in model.named_modules():
        if isinstance(module, (nn.BatchNorm1d, nn.BatchNorm2d)):
            prefix = f"{name}." if name else ""
            bn_keys.add(f"{prefix}running_mean")
            bn_keys.add(f"{prefix}running_var")
            bn_keys.add(f"{prefix}num_batches_tracked")
    return bn_keys


def get_learnable_mask(model: nn.Module) -> List[bool]:
    """Return a boolean mask: True for learnable params, False for BN buffers."""
    bn_keys = _bn_buffer_keys(model)
    return [key not in bn_keys for key in model.state_dict().keys()]


# ── Detailed evaluation metrics ───────────────────────────────

@dataclass
class DetailedMetrics:
    """Full evaluation metrics from test_model_detailed."""
    loss: float = 0.0
    accuracy: float = 0.0
    precision: float = 0.0        # macro-averaged
    recall: float = 0.0           # macro-averaged
    f1: float = 0.0               # macro-averaged
    weighted_f1: float = 0.0      # weighted-averaged F1
    false_positive_rate: float = 0.0  # macro-averaged
    per_class: Dict[str, dict] = field(default_factory=dict)
    confusion_matrix: List[List[int]] = field(default_factory=list)
    num_samples: int = 0

    def to_dict(self) -> dict:
        return {
            "loss": round(self.loss, 4),
            "accuracy": round(self.accuracy * 100, 2),
            "precision": round(self.precision * 100, 2),
            "recall": round(self.recall * 100, 2),
            "f1": round(self.f1 * 100, 2),
            "weighted_f1": round(self.weighted_f1 * 100, 2),
            "false_positive_rate": round(self.false_positive_rate * 100, 2),
            "per_class": self.per_class,
            "num_samples": self.num_samples,
        }


# ── Training / evaluation ─────────────────────────────────────

DEVICE = torch.device("cpu")


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    epochs: int = 1,
    lr: float = 0.001,
    weight_decay: float = 1e-4,
    class_weights: Optional[np.ndarray] = None,
) -> Tuple[float, int]:
    """
    Train the model locally and return (avg_loss, num_samples).

    CYBER-20 improvements:
    - Uses AdamW with weight decay for regularization.
    - Supports class-weighted CrossEntropyLoss.
    - Lower default learning rate (0.001 vs 0.01).
    """
    model.to(DEVICE)
    model.train()

    if class_weights is not None:
        weight_tensor = torch.from_numpy(class_weights).float().to(DEVICE)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    else:
        criterion = nn.CrossEntropyLoss()

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=lr, weight_decay=weight_decay,
    )

    total_loss = 0.0
    total_samples = 0

    for _ in range(epochs):
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(X_batch)
            total_samples += len(X_batch)

    avg_loss = total_loss / total_samples if total_samples > 0 else 0.0
    return avg_loss, total_samples


def test_model(
    model: nn.Module,
    test_loader: DataLoader,
) -> Tuple[float, float, float, int]:
    """
    Evaluate the model and return (loss, accuracy, f1, num_samples).
    Backward compatible with Phase 12 callers.
    """
    metrics = test_model_detailed(model, test_loader)
    return metrics.loss, metrics.accuracy, metrics.f1, metrics.num_samples


def test_model_detailed(
    model: nn.Module,
    test_loader: DataLoader,
    class_weights: Optional[np.ndarray] = None,
) -> DetailedMetrics:
    """
    Full evaluation with per-class metrics, confusion matrix, and FPR.
    """
    model.to(DEVICE)
    model.eval()

    if class_weights is not None:
        weight_tensor = torch.from_numpy(class_weights).float().to(DEVICE)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    else:
        criterion = nn.CrossEntropyLoss()

    all_preds = []
    all_labels = []
    total_loss = 0.0
    total_samples = 0

    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            total_loss += loss.item() * len(X_batch)
            total_samples += len(X_batch)

            preds = outputs.argmax(dim=1)
            all_preds.append(preds.cpu().numpy())
            all_labels.append(y_batch.cpu().numpy())

    if total_samples == 0:
        return DetailedMetrics()

    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)

    avg_loss = total_loss / total_samples
    accuracy = (all_preds == all_labels).mean()

    # Confusion matrix
    cm = np.zeros((NUM_CLASSES, NUM_CLASSES), dtype=int)
    for t, p in zip(all_labels, all_preds):
        cm[t][p] += 1

    # Per-class metrics
    per_class = {}
    precisions = []
    recalls = []
    f1s = []
    fprs = []
    supports = []

    for cls_id in range(NUM_CLASSES):
        cls_name = CLASS_NAMES[cls_id]
        tp = cm[cls_id, cls_id]
        fp = cm[:, cls_id].sum() - tp
        fn = cm[cls_id, :].sum() - tp
        tn = total_samples - tp - fp - fn

        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        support = int(cm[cls_id, :].sum())

        per_class[cls_name] = {
            "precision": round(p * 100, 2),
            "recall": round(r * 100, 2),
            "f1": round(f * 100, 2),
            "fpr": round(fpr * 100, 2),
            "support": support,
        }
        precisions.append(p)
        recalls.append(r)
        f1s.append(f)
        fprs.append(fpr)
        supports.append(support)

    # Weighted F1
    total_support = sum(supports)
    weighted_f1 = sum(f * s for f, s in zip(f1s, supports)) / total_support if total_support > 0 else 0.0

    return DetailedMetrics(
        loss=avg_loss,
        accuracy=float(accuracy),
        precision=float(np.mean(precisions)),
        recall=float(np.mean(recalls)),
        f1=float(np.mean(f1s)),
        weighted_f1=float(weighted_f1),
        false_positive_rate=float(np.mean(fprs)),
        per_class=per_class,
        confusion_matrix=cm.tolist(),
        num_samples=total_samples,
    )
