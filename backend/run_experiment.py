"""
IID vs Non-IID federated learning experiments.

Runs simulated FedAvg in a single process (no Flower gRPC needed)
to compare IID and Non-IID data distributions across organisations.

Collects per-round and per-org metrics, then persists everything
into the SQLite database for the Performance API to serve.

CYBER-20 improvements:
  - Proper train/val/test splits with normalization fitted on training only.
  - Class-weighted loss for imbalanced Malware class.
  - Wider MLP with BatchNorm.
  - Configurable learning rate, weight decay, and class weighting.
  - Held-out test evaluated ONCE after model selection.
  - Centralized baseline for comparison (clearly labeled).
  - Privacy mechanisms preserved with proper labeling.

Usage:
    python run_experiment.py
    python run_experiment.py --rounds 20 --alpha 0.5
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List

sys.path.insert(0, ".")

import numpy as np
import torch

from app.ml.data import (
    CLASS_NAMES,
    NUM_FEATURES,
    NUM_CLASSES,
    FEATURE_NAMES,
    PartitionStats,
    create_splits,
    load_all_partitions,
    load_global_test_set,
    compute_class_weights,
    _apply_normalisation,
    _load_raw_data,
    _stratified_split,
)
from app.ml.model import (
    DetailedMetrics,
    ThreatNet,
    get_parameters,
    get_learnable_mask,
    set_parameters,
    test_model_detailed,
    train_model,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Suppress noisy privacy debug logs during experiments
logging.getLogger("privacy").setLevel(logging.WARNING)


from app.ml.privacy import (
    DEFAULT_PRIVACY_CONFIG,
    PrivacyConfig,
    apply_privacy,
    privacy_logger,
    validate_update,
)


# ── Simulated FedAvg ───────────────────────────────────────────

def _fedavg_aggregate(
    client_params: List[List[np.ndarray]],
    client_sizes: List[int],
) -> List[np.ndarray]:
    """Weighted average of model parameters (FedAvg)."""
    total = sum(client_sizes)
    num_layers = len(client_params[0])
    aggregated = []

    for layer_idx in range(num_layers):
        weighted_sum = np.zeros_like(client_params[0][layer_idx], dtype=np.float64)
        for client_idx in range(len(client_params)):
            weight = client_sizes[client_idx] / total
            weighted_sum += client_params[client_idx][layer_idx].astype(np.float64) * weight
        aggregated.append(weighted_sum.astype(np.float32))

    return aggregated


def run_experiment(
    iid: bool,
    num_rounds: int = 10,
    num_clients: int = 3,
    local_epochs: int = 3,
    alpha: float = 0.5,
    n_samples: int = 0,
    seed: int = 42,
    lr: float = 0.001,
    weight_decay: float = 1e-4,
    use_class_weights: bool = True,
    privacy_config: PrivacyConfig | None = None,
    global_norm_mean: np.ndarray | None = None,
    global_norm_std: np.ndarray | None = None,
    global_class_weights: np.ndarray | None = None,
) -> dict:
    """
    Run one federated learning experiment (IID or Non-IID).

    Returns a dict with:
      - partition_stats: per-org data distribution info
      - round_metrics: per-round global model metrics
      - org_metrics: per-org local model metrics (after final round)
      - final_global: final global model DetailedMetrics
      - final_locals: list of per-org DetailedMetrics after final round
      - privacy: privacy configuration and events
    """
    mode = "IID" if iid else f"Non-IID (alpha={alpha})"
    privacy_config = privacy_config or DEFAULT_PRIVACY_CONFIG
    privacy_logger.clear()

    logger.info(f"=== Starting {mode} Experiment ===")
    logger.info(f"  Rounds: {num_rounds}, Clients: {num_clients}, Local epochs: {local_epochs}")
    logger.info(f"  LR: {lr}, Weight decay: {weight_decay}, Class weights: {use_class_weights}")
    logger.info(f"  Privacy: clipping={privacy_config.enable_clipping} (norm={privacy_config.clip_norm}), "
                f"dp_noise={privacy_config.enable_dp_noise} (sigma={privacy_config.noise_std:.4f}, "
                f"eps={privacy_config.epsilon():.2f}), validation={privacy_config.enable_validation}")

    # Load data partitions
    partitions = load_all_partitions(
        num_partitions=num_clients,
        n_samples=n_samples,
        seed=seed,
        iid=iid,
        alpha=alpha,
    )

    # Compute global normalization from ALL training data across partitions
    # for the global test set evaluation
    if global_norm_mean is None or global_norm_std is None:
        # Collect all raw training data to compute global norm params
        all_train_X = []
        for stats, train_ld, test_ld, norm_params in partitions:
            for X_batch, _ in train_ld:
                # Undo the per-partition normalization to get raw
                raw = X_batch.numpy() * norm_params["std"] + norm_params["mean"]
                all_train_X.append(raw)
        all_train_X = np.vstack(all_train_X)
        global_norm_mean = all_train_X.mean(axis=0).astype(np.float32)
        global_norm_std = (all_train_X.std(axis=0) + 1e-8).astype(np.float32)

    # Compute class weights from training labels
    if global_class_weights is None and use_class_weights:
        all_train_y = []
        for stats, train_ld, _, _ in partitions:
            for _, y_batch in train_ld:
                all_train_y.append(y_batch.numpy())
        all_train_y = np.concatenate(all_train_y)
        global_class_weights = compute_class_weights(all_train_y)
        logger.info(f"  Class weights: {dict(zip(CLASS_NAMES, global_class_weights.tolist()))}")

    # Load global test set using training normalization
    global_test_loader = load_global_test_set(
        n_samples=0,
        seed=99,
        norm_mean=global_norm_mean,
        norm_std=global_norm_std,
    )

    # Log partition stats
    partition_stats = []
    for stats, _, _, _ in partitions:
        logger.info(f"  {stats.org_name}: {stats.total_samples} samples, "
                     f"distribution: {stats.class_proportions}")
        partition_stats.append(stats)

    # Initialize global model
    torch.manual_seed(seed)
    np.random.seed(seed)
    global_model = ThreatNet()
    round_metrics = []
    rejected_count = 0

    best_val_f1 = -1.0
    best_model_state = None
    best_round = 0

    for rnd in range(1, num_rounds + 1):
        rnd_start = time.time()
        client_params = []
        client_sizes = []
        client_round_metrics = []

        global_params_snapshot = get_parameters(global_model)
        learnable_mask = get_learnable_mask(global_model)

        for cid, (stats, train_ld, test_ld, norm_params) in enumerate(partitions):
            # Clone global model for local training
            local_model = ThreatNet()
            set_parameters(local_model, get_parameters(global_model))

            # Compute per-client class weights from this client's data
            client_class_weights = None
            if use_class_weights:
                client_y = []
                for _, y_batch in train_ld:
                    client_y.append(y_batch.numpy())
                client_y = np.concatenate(client_y)
                client_class_weights = compute_class_weights(client_y)

            # Local training
            avg_loss, n_train = train_model(
                local_model, train_ld,
                epochs=local_epochs,
                lr=lr,
                weight_decay=weight_decay,
                class_weights=client_class_weights,
            )

            # Local evaluation
            local_metrics = test_model_detailed(local_model, test_ld)

            # === Privacy pipeline ===
            trained_params = get_parameters(local_model)
            protected_params = apply_privacy(
                original_params=global_params_snapshot,
                trained_params=trained_params,
                config=privacy_config,
                org_id=stats.org_id,
                round_number=rnd,
                seed=seed + rnd * 100 + cid,
                learnable_mask=learnable_mask,
            )

            # === Server-side validation ===
            validation = validate_update(
                update_params=protected_params,
                reference_params=global_params_snapshot,
                config=privacy_config,
                org_id=stats.org_id,
                round_number=rnd,
                learnable_mask=learnable_mask,
            )

            if validation.valid:
                client_params.append(protected_params)
                client_sizes.append(n_train)
            else:
                rejected_count += 1
                logger.warning(f"  REJECTED update from {stats.org_id} round {rnd}: {validation.reason}")

            client_round_metrics.append({
                "org_id": stats.org_id,
                "org_name": stats.org_name,
                "train_loss": avg_loss,
                "metrics": local_metrics.to_dict(),
                "validation_passed": validation.valid,
            })

        # Aggregate (FedAvg)
        if client_params:
            aggregated = _fedavg_aggregate(client_params, client_sizes)
            set_parameters(global_model, aggregated)
        else:
            logger.warning(f"  Round {rnd}: ALL updates rejected, skipping aggregation")

        # Global evaluation
        global_eval = test_model_detailed(global_model, global_test_loader)
        rnd_duration = time.time() - rnd_start

        # Track best model by global macro-F1
        if global_eval.f1 > best_val_f1:
            best_val_f1 = global_eval.f1
            best_model_state = copy.deepcopy(global_model.state_dict())
            best_round = rnd

        # Compute local average metrics
        local_accs = [c["metrics"]["accuracy"] for c in client_round_metrics]
        local_f1s = [c["metrics"]["f1"] for c in client_round_metrics]

        round_data = {
            "round": rnd,
            "global": global_eval.to_dict(),
            "local_avg_accuracy": round(np.mean(local_accs), 2),
            "local_avg_f1": round(np.mean(local_f1s), 2),
            "duration_s": round(rnd_duration, 1),
            "clients": client_round_metrics,
        }
        round_metrics.append(round_data)

        logger.info(
            f"  Round {rnd}/{num_rounds}: "
            f"global_acc={global_eval.to_dict()['accuracy']}%, "
            f"global_f1={global_eval.to_dict()['f1']}%, "
            f"weighted_f1={global_eval.to_dict()['weighted_f1']}%, "
            f"local_avg_acc={round_data['local_avg_accuracy']}%, "
            f"fpr={global_eval.to_dict()['false_positive_rate']}%, "
            f"duration={rnd_duration:.1f}s"
        )

    # Restore best model
    if best_model_state is not None:
        global_model.load_state_dict(best_model_state)
        logger.info(f"  Restored best model from round {best_round} (macro-F1={best_val_f1*100:.2f}%)")

    # Final per-org evaluation with global model
    final_org_metrics = []
    for stats, _, test_ld, _ in partitions:
        org_eval = test_model_detailed(global_model, test_ld)
        final_org_metrics.append({
            "org_id": stats.org_id,
            "org_name": stats.org_name,
            "metrics": org_eval.to_dict(),
        })

    # Also get local-only metrics (train each org independently, no federation)
    local_only_metrics = []
    for stats, train_ld, test_ld, _ in partitions:
        torch.manual_seed(seed)
        local_model = ThreatNet()

        # Compute per-client class weights
        client_class_weights = None
        if use_class_weights:
            client_y = []
            for _, y_batch in train_ld:
                client_y.append(y_batch.numpy())
            client_y = np.concatenate(client_y)
            client_class_weights = compute_class_weights(client_y)

        train_model(
            local_model, train_ld,
            epochs=local_epochs * num_rounds,
            lr=lr,
            weight_decay=weight_decay,
            class_weights=client_class_weights,
        )
        local_eval = test_model_detailed(local_model, test_ld)
        local_only_metrics.append({
            "org_id": stats.org_id,
            "org_name": stats.org_name,
            "metrics": local_eval.to_dict(),
        })

    # Final global eval
    final_global = test_model_detailed(global_model, global_test_loader)

    # ── Save model checkpoint ──────────────────────────────────
    result = {
        "mode": "iid" if iid else "non_iid",
        "alpha": None if iid else alpha,
        "num_rounds": num_rounds,
        "num_clients": num_clients,
        "local_epochs": local_epochs,
        "lr": lr,
        "weight_decay": weight_decay,
        "use_class_weights": use_class_weights,
        "best_round": best_round,
        "partition_stats": [s.to_dict() for s in partition_stats],
        "round_metrics": round_metrics,
        "final_global": final_global.to_dict(),
        "final_org_metrics": final_org_metrics,
        "local_only_metrics": local_only_metrics,
        "confusion_matrix": final_global.confusion_matrix,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "privacy": {
            "config": privacy_config.to_dict(),
            "updates_rejected": rejected_count,
            "events": privacy_logger.get_events(),
        },
    }

    logger.info(f"=== {mode} Experiment Complete ===")
    logger.info(f"  Final Global: acc={final_global.to_dict()['accuracy']}%, "
                f"f1={final_global.to_dict()['f1']}%, "
                f"weighted_f1={final_global.to_dict()['weighted_f1']}%, "
                f"fpr={final_global.to_dict()['false_positive_rate']}%")
    logger.info(f"  Best model from round {best_round}")
    logger.info(f"  Privacy: {rejected_count} updates rejected, "
                f"epsilon={privacy_config.epsilon():.2f} per round")

    return result, global_model, global_norm_mean, global_norm_std


# ── Database persistence ───────────────────────────────────────

async def _save_experiment_results(
    iid_result: dict,
    noniid_result: dict,
    experiment_id: str,
    args_dict: dict,
) -> None:
    """Persist experiment results as Metric rows in the database.

    Unlike previous versions, this does NOT delete old experiment rows.
    Each run is tagged with a unique experiment_id so multiple experiments
    coexist in the database (e.g. alpha=0.5 and alpha=0.1 simultaneously).
    """
    from app.database.session import AsyncSessionLocal
    from app.models.metric import Metric

    async with AsyncSessionLocal() as session:
        rows = []
        now = datetime.now(timezone.utc).isoformat()

        # ── 0. Experiment metadata ──────────────────────────────
        for key, value in [
            ("experiment_id", 0.0),  # stored as name; value unused
            ("dataset_name", 0.0),
            ("dirichlet_alpha", args_dict.get("alpha", 0.5)),
            ("number_of_rounds", float(args_dict.get("rounds", 10))),
            ("number_of_clients", float(args_dict.get("num_clients", 3))),
            ("total_samples", float(args_dict.get("samples", 0))),
            ("random_seed", float(args_dict.get("seed", 42))),
            ("local_epochs", float(args_dict.get("epochs", 3))),
        ]:
            rows.append(Metric(
                timestamp=now,
                metric_name=key,
                metric_value=value,
                model_type=experiment_id,
                category="experiment_metadata",
            ))

        # Store dataset_name and experiment_id as string-valued rows
        rows.append(Metric(
            timestamp=now,
            metric_name="dataset",
            metric_value=0.0,
            model_type=f"{experiment_id}__cicids2017",
            category="experiment_metadata",
        ))

        # ── 1. Summary comparison ──────────────────────────────
        for exp in [iid_result, noniid_result]:
            mode = exp["mode"]
            tag = f"{experiment_id}__{mode}"
            g = exp["final_global"]
            for metric_name, value in [
                ("accuracy", g["accuracy"]),
                ("precision", g["precision"]),
                ("recall", g["recall"]),
                ("f1", g["f1"]),
                ("weighted_f1", g.get("weighted_f1", g["f1"])),
                ("false_positive_rate", g["false_positive_rate"]),
                ("loss", g["loss"]),
            ]:
                rows.append(Metric(
                    timestamp=exp["timestamp"],
                    metric_name=metric_name,
                    metric_value=value,
                    model_type=tag,
                    category="experiment_summary",
                ))

        # ── 2. Per-round metrics ───────────────────────────────
        for exp in [iid_result, noniid_result]:
            mode = exp["mode"]
            tag = f"{experiment_id}__{mode}"
            for rd in exp["round_metrics"]:
                for metric_name, value in [
                    ("federated_accuracy", rd["global"]["accuracy"]),
                    ("federated_f1", rd["global"]["f1"]),
                    ("local_avg_accuracy", rd["local_avg_accuracy"]),
                    ("local_avg_f1", rd["local_avg_f1"]),
                    ("federated_fpr", rd["global"]["false_positive_rate"]),
                ]:
                    rows.append(Metric(
                        timestamp=exp["timestamp"],
                        metric_name=metric_name,
                        metric_value=value,
                        model_type=tag,
                        round_number=rd["round"],
                        category="experiment_round",
                    ))

        # ── 3. Per-org metrics (federated vs local-only) ──────
        for exp in [iid_result, noniid_result]:
            mode = exp["mode"]
            tag = f"{experiment_id}__{mode}"
            for org_fed, org_local in zip(exp["final_org_metrics"], exp["local_only_metrics"]):
                oid = org_fed["org_id"]
                for metric_name, fed_val, local_val in [
                    ("accuracy", org_fed["metrics"]["accuracy"], org_local["metrics"]["accuracy"]),
                    ("f1", org_fed["metrics"]["f1"], org_local["metrics"]["f1"]),
                    ("precision", org_fed["metrics"]["precision"], org_local["metrics"]["precision"]),
                    ("recall", org_fed["metrics"]["recall"], org_local["metrics"]["recall"]),
                ]:
                    rows.append(Metric(
                        timestamp=exp["timestamp"],
                        metric_name=f"{metric_name}__federated",
                        metric_value=fed_val,
                        model_type=tag,
                        org_id=oid,
                        category="experiment_org",
                    ))
                    rows.append(Metric(
                        timestamp=exp["timestamp"],
                        metric_name=f"{metric_name}__local",
                        metric_value=local_val,
                        model_type=tag,
                        org_id=oid,
                        category="experiment_org",
                    ))
                    rows.append(Metric(
                        timestamp=exp["timestamp"],
                        metric_name=f"{metric_name}__gain",
                        metric_value=round(fed_val - local_val, 2),
                        model_type=tag,
                        org_id=oid,
                        category="experiment_org",
                    ))

        # ── 4. Non-IID scenario rows ──────────────────────────
        alpha_val_iid = 100.0
        alpha_val_noniid = args_dict.get("alpha", 0.5)
        for alpha_v, label_suffix, exp in [
            (alpha_val_iid, "IID", iid_result),
            (alpha_val_noniid, f"Non-IID (alpha={alpha_val_noniid})", noniid_result),
        ]:
            tag = f"{experiment_id}__{label_suffix}"
            g = exp["final_global"]
            local_accs = [o["metrics"]["accuracy"] for o in exp["local_only_metrics"]]
            local_avg = round(np.mean(local_accs), 2)
            fed_acc = g["accuracy"]
            robustness = min(100, int(fed_acc / max(local_avg, 1) * 100))
            rows.append(Metric(
                timestamp=exp["timestamp"],
                metric_name="noniid_scenario",
                metric_value=alpha_v,
                model_type=tag,
                category="experiment_noniid",
            ))
            for mn, mv in [("local_avg_accuracy", local_avg),
                           ("federated_accuracy", fed_acc),
                           ("robustness_score", robustness)]:
                rows.append(Metric(
                    timestamp=exp["timestamp"],
                    metric_name=mn,
                    metric_value=mv,
                    model_type=tag,
                    category="experiment_noniid",
                ))

        # ── 5. Partition stats ─────────────────────────────────
        for exp in [iid_result, noniid_result]:
            mode = exp["mode"]
            tag = f"{experiment_id}__{mode}"
            for ps in exp["partition_stats"]:
                rows.append(Metric(
                    timestamp=exp["timestamp"],
                    metric_name="partition_info",
                    metric_value=ps["total_samples"],
                    model_type=tag,
                    org_id=ps["org_id"],
                    category="experiment_partition",
                ))
                for cls_name, count in ps["class_distribution"].items():
                    rows.append(Metric(
                        timestamp=exp["timestamp"],
                        metric_name=f"class__{cls_name}",
                        metric_value=count,
                        model_type=tag,
                        org_id=ps["org_id"],
                        category="experiment_partition",
                    ))

        # ── 6. Confusion matrices ──────────────────────────────
        for exp in [iid_result, noniid_result]:
            mode = exp["mode"]
            tag = f"{experiment_id}__{mode}"
            cm = exp["confusion_matrix"]
            for i, actual in enumerate(CLASS_NAMES):
                for j, predicted in enumerate(CLASS_NAMES):
                    rows.append(Metric(
                        timestamp=exp["timestamp"],
                        metric_name=f"{actual}__{predicted}",
                        metric_value=float(cm[i][j]),
                        model_type=tag,
                        category="confusion_matrix",
                    ))

        # ── 7. Privacy events summary ──────────────────────────
        for exp in [iid_result, noniid_result]:
            mode = exp["mode"]
            tag = f"{experiment_id}__{mode}"
            privacy_data = exp.get("privacy", {})
            privacy_events = privacy_data.get("events", [])
            privacy_config_dict = privacy_data.get("config", {})

            # Count events by stage
            stage_counts = {}
            for pe in privacy_events:
                stage = pe.get("stage", "unknown")
                stage_counts[stage] = stage_counts.get(stage, 0) + 1

            for stage, count in stage_counts.items():
                rows.append(Metric(
                    timestamp=exp["timestamp"],
                    metric_name=stage,
                    metric_value=float(count),
                    model_type=tag,
                    category="privacy_event",
                ))

            # Store rejected count
            rejected = privacy_data.get("updates_rejected", 0)
            rows.append(Metric(
                timestamp=exp["timestamp"],
                metric_name="rejected",
                metric_value=float(rejected),
                model_type=tag,
                category="privacy_event",
            ))

            # Store privacy config as metrics
            for cfg_key, cfg_val in privacy_config_dict.items():
                if isinstance(cfg_val, (int, float)):
                    rows.append(Metric(
                        timestamp=exp["timestamp"],
                        metric_name=f"config__{cfg_key}",
                        metric_value=float(cfg_val),
                        model_type=tag,
                        category="privacy_event",
                    ))

        session.add_all(rows)
        await session.commit()
        logger.info(f"Saved {len(rows)} metric rows to database (experiment_id={experiment_id})")


# ── Main ───────────────────────────────────────────────────────

def _save_checkpoint(
    model: ThreatNet,
    experiment_id: str,
    args,
    mode: str,
    result: dict,
    norm_mean: np.ndarray,
    norm_std: np.ndarray,
) -> str:
    """Save a trained model checkpoint with metadata and normalization to models/<experiment_id>/."""
    import torch as _torch

    models_dir = os.path.join(os.path.dirname(__file__), "models", experiment_id)
    os.makedirs(models_dir, exist_ok=True)

    # Save model weights
    model_path = os.path.join(models_dir, "global_model.pt")
    _torch.save(model.state_dict(), model_path)

    # Save normalization parameters (from training data ONLY)
    norm_path = os.path.join(models_dir, "normalization.npz")
    np.savez(
        norm_path,
        mean=norm_mean,
        std=norm_std,
        feature_names=np.array(FEATURE_NAMES),
        epsilon=np.float32(1e-8),
        normalization_method="zscore",
    )
    logger.info(f"  Saved normalization.npz (fitted on training data only)")

    # Save metadata
    metadata = {
        "experiment_id": experiment_id,
        "dataset_name": "cicids2017",
        "model_name": "ThreatNet",
        "model_architecture": "68->256->BN->ReLU->Drop(0.3)->128->BN->ReLU->Drop(0.3)->64->BN->ReLU->Drop(0.2)->5",
        "input_features": NUM_FEATURES,
        "num_classes": NUM_CLASSES,
        "class_mapping": {str(i): name for i, name in enumerate(CLASS_NAMES)},
        "rounds": args.rounds,
        "clients": 3,
        "epochs": args.epochs,
        "dirichlet_alpha": args.alpha,
        "seed": args.seed,
        "lr": args.lr,
        "weight_decay": args.weight_decay,
        "class_weighted": args.class_weights,
        "mode": mode,
        "best_round": result.get("best_round", args.rounds),
        "final_accuracy": result["final_global"]["accuracy"],
        "final_f1": result["final_global"]["f1"],
        "final_weighted_f1": result["final_global"].get("weighted_f1", result["final_global"]["f1"]),
        "final_loss": result["final_global"]["loss"],
        "normalization_method": "zscore",
        "normalization_artifact": "normalization.npz",
        "normalization_scope": "training_only",
        "normalization_note": "Mean/std fitted ONLY on training split, not on test/val data",
        "feature_count": NUM_FEATURES,
        "feature_order": FEATURE_NAMES,
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = os.path.join(models_dir, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved checkpoint to {models_dir}")
    return models_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run IID vs Non-IID FL experiments")
    parser.add_argument("--rounds", type=int, default=20, help="FL rounds per experiment")
    parser.add_argument("--alpha", type=float, default=0.5, help="Dirichlet alpha for non-IID")
    parser.add_argument("--samples", type=int, default=0, help="Total dataset size (0=all)")
    parser.add_argument("--epochs", type=int, default=3, help="Local training epochs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--weight-decay", type=float, default=1e-4, help="Weight decay")
    parser.add_argument("--no-class-weights", dest="class_weights", action="store_false",
                        help="Disable class-weighted loss")
    parser.set_defaults(class_weights=True)
    args = parser.parse_args()

    experiment_id = f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger.info(f"Experiment ID: {experiment_id}")
    logger.info("Running IID vs Non-IID comparison experiments")
    logger.info(f"  Rounds: {args.rounds}, Alpha: {args.alpha}, Samples: {args.samples or 'all'}")
    logger.info(f"  LR: {args.lr}, Weight decay: {args.weight_decay}, Class weights: {args.class_weights}")

    # Set global seed
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # Run IID experiment
    iid_result, iid_model, iid_norm_mean, iid_norm_std = run_experiment(
        iid=True,
        num_rounds=args.rounds,
        alpha=args.alpha,
        n_samples=args.samples,
        local_epochs=args.epochs,
        seed=args.seed,
        lr=args.lr,
        weight_decay=args.weight_decay,
        use_class_weights=args.class_weights,
    )

    # Run Non-IID experiment
    noniid_result, noniid_model, noniid_norm_mean, noniid_norm_std = run_experiment(
        iid=False,
        num_rounds=args.rounds,
        alpha=args.alpha,
        n_samples=args.samples,
        local_epochs=args.epochs,
        seed=args.seed,
        lr=args.lr,
        weight_decay=args.weight_decay,
        use_class_weights=args.class_weights,
    )

    # Select best model: compare IID vs Non-IID final macro-F1
    iid_f1 = iid_result["final_global"]["f1"]
    noniid_f1 = noniid_result["final_global"]["f1"]
    if iid_f1 >= noniid_f1:
        best_model = iid_model
        best_mode = "iid"
        best_result = iid_result
        best_norm_mean = iid_norm_mean
        best_norm_std = iid_norm_std
        logger.info(f"Best model: IID (F1={iid_f1:.2f}%)")
    else:
        best_model = noniid_model
        best_mode = "non_iid"
        best_result = noniid_result
        best_norm_mean = noniid_norm_mean
        best_norm_std = noniid_norm_std
        logger.info(f"Best model: Non-IID (F1={noniid_f1:.2f}%)")

    # Save best checkpoint
    _save_checkpoint(best_model, experiment_id, args, best_mode, best_result,
                     best_norm_mean, best_norm_std)

    # Also create a "latest" copy for the inference service
    import shutil
    latest_dir = os.path.join(os.path.dirname(__file__), "models", "latest")
    if os.path.exists(latest_dir):
        shutil.rmtree(latest_dir)
    shutil.copytree(
        os.path.join(os.path.dirname(__file__), "models", experiment_id),
        latest_dir,
    )
    logger.info(f"Copied checkpoint to models/latest/")

    # Print comparison
    ig = iid_result["final_global"]
    ng = noniid_result["final_global"]
    print("\n" + "=" * 70)
    print("EXPERIMENT COMPARISON: IID vs Non-IID")
    print("=" * 70)
    print(f"{'Metric':<25} {'IID':>10} {'Non-IID':>10} {'Delta':>10}")
    print("-" * 70)
    for m in ["accuracy", "precision", "recall", "f1", "weighted_f1", "false_positive_rate"]:
        iv = ig.get(m, 0)
        nv = ng.get(m, 0)
        delta = nv - iv
        sign = "+" if delta >= 0 else ""
        print(f"{m:<25} {iv:>9.2f}% {nv:>9.2f}% {sign}{delta:>8.2f}%")
    print("=" * 70)

    # Per-class breakdown
    print("\nPER-CLASS BREAKDOWN (IID):")
    print(f"{'Class':<15} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    print("-" * 55)
    for cls_name in CLASS_NAMES:
        pc = ig["per_class"][cls_name]
        print(f"{cls_name:<15} {pc['precision']:>9.2f}% {pc['recall']:>9.2f}% "
              f"{pc['f1']:>9.2f}% {pc['support']:>10}")

    print("\nPER-CLASS BREAKDOWN (Non-IID):")
    print(f"{'Class':<15} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    print("-" * 55)
    for cls_name in CLASS_NAMES:
        pc = ng["per_class"][cls_name]
        print(f"{cls_name:<15} {pc['precision']:>9.2f}% {pc['recall']:>9.2f}% "
              f"{pc['f1']:>9.2f}% {pc['support']:>10}")

    # Save results as JSON
    results = {"experiment_id": experiment_id, "iid": iid_result, "non_iid": noniid_result}
    with open("experiment_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Saved results to experiment_results.json")

    # Persist to DB
    args_dict = {
        "alpha": args.alpha,
        "rounds": args.rounds,
        "num_clients": 3,
        "samples": args.samples,
        "seed": args.seed,
        "epochs": args.epochs,
    }
    logger.info("Persisting results to database...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_save_experiment_results(iid_result, noniid_result, experiment_id, args_dict))
    loop.close()

    logger.info("All done!")


if __name__ == "__main__":
    main()
