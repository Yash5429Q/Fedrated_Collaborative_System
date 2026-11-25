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
    create_benchmark_splits,
    build_benchmark_partitions,
    benchmark_eval_loader,
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
    compute_update_norm,
    privacy_logger,
    validate_update,
)


# ── Simulated FedAvg ───────────────────────────────────────────

def _fedavg_aggregate(
    client_params: List[List[np.ndarray]],
    client_sizes: List[int],
    previous_global: List[np.ndarray] | None = None,
    momentum: float = 0.0,
) -> List[np.ndarray]:
    """Weighted average of model parameters (FedAvg) with optional momentum.

    When momentum > 0 and previous_global is provided, the aggregated
    result is blended with the previous global model:
        new = (1 - momentum) * aggregated + momentum * previous_global

    This smooths round-to-round oscillations without changing the
    underlying FedAvg semantics (momentum=0 is standard FedAvg).
    """
    total = sum(client_sizes)
    num_layers = len(client_params[0])
    aggregated = []

    for layer_idx in range(num_layers):
        weighted_sum = np.zeros_like(client_params[0][layer_idx], dtype=np.float64)
        for client_idx in range(len(client_params)):
            weight = client_sizes[client_idx] / total
            weighted_sum += client_params[client_idx][layer_idx].astype(np.float64) * weight
        aggregated.append(weighted_sum.astype(np.float32))

    # Apply server-side momentum (EMA blending with previous global)
    if momentum > 0.0 and previous_global is not None:
        aggregated = [
            ((1.0 - momentum) * a.astype(np.float64) + momentum * p.astype(np.float64)).astype(np.float32)
            for a, p in zip(aggregated, previous_global)
        ]

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
    momentum: float = 0.0,
    norm_guard_multiplier: float = 0.0,
    proximal_mu: float = 0.0,
    splits: dict | None = None,
) -> tuple:
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
                f"formal_dp=not_established), validation={privacy_config.enable_validation}")
    logger.info(f"  Momentum: {momentum}, Norm guard multiplier: {norm_guard_multiplier}")

    # Use one frozen split for both modes. Shared scaler is a simulation choice.
    if splits is None:
        splits = create_benchmark_splits(n_samples=n_samples, seed=seed)
    global_norm_mean = splits["norm_mean"]
    global_norm_std = splits["norm_std"]
    global_class_weights = splits["class_weights"] if use_class_weights else None
    partitions = build_benchmark_partitions(
        splits, num_partitions=num_clients, seed=seed, iid=iid, alpha=alpha)
    val_loader = benchmark_eval_loader(splits, "val")
    test_loader = benchmark_eval_loader(splits, "test")
    partition_stats = [stats for stats, _ in partitions]
    for stats in partition_stats:
        logger.info("  %s: %s training samples", stats.org_name, stats.train_samples)

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

        for cid, (stats, train_ld) in enumerate(partitions):
            client_start = time.perf_counter()
            # Clone global model for local training
            local_model = ThreatNet()
            set_parameters(local_model, get_parameters(global_model))

            # Same class weights and preprocessing across clients and baselines.
            avg_loss, n_train = train_model(
                local_model, train_ld, epochs=local_epochs, lr=lr,
                weight_decay=weight_decay, class_weights=global_class_weights,
                proximal_mu=proximal_mu)
            local_metrics = test_model_detailed(local_model, val_loader)

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
                "samples_used": n_train,
                "duration_s": round(time.perf_counter() - client_start, 3),
                "update_size_bytes": sum(p.nbytes for p in protected_params),
            })

        # ── Norm guard: flag / down-weight outlier updates ────
        if norm_guard_multiplier > 0.0 and len(client_params) > 1:
            update_norms = []
            for cp in client_params:
                delta = [cp_l - gp_l for cp_l, gp_l in zip(cp, global_params_snapshot)]
                update_norms.append(compute_update_norm(delta, learnable_mask))
            median_norm = float(np.median(update_norms))
            threshold = median_norm * norm_guard_multiplier
            guarded_params = []
            guarded_sizes = []
            for idx, (cp, cs, un) in enumerate(zip(client_params, client_sizes, update_norms)):
                if un > threshold:
                    # Down-weight: scale the update to the threshold, keep the client
                    scale = threshold / un
                    capped = [
                        (gp_l + (cp_l - gp_l) * scale).astype(np.float32)
                        for cp_l, gp_l in zip(cp, global_params_snapshot)
                    ]
                    guarded_params.append(capped)
                    guarded_sizes.append(cs)
                    logger.info(f"    Norm guard: client {idx} norm {un:.4f} > threshold {threshold:.4f}, scaled to {threshold:.4f}")
                else:
                    guarded_params.append(cp)
                    guarded_sizes.append(cs)
            client_params = guarded_params
            client_sizes = guarded_sizes

        # Aggregate (FedAvg + optional momentum)
        if client_params:
            aggregated = _fedavg_aggregate(
                client_params, client_sizes,
                previous_global=global_params_snapshot,
                momentum=momentum,
            )
            set_parameters(global_model, aggregated)
        else:
            logger.warning(f"  Round {rnd}: ALL updates rejected, skipping aggregation")

        # Global evaluation
        global_eval = test_model_detailed(global_model, val_loader)
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
            "evaluation_split": "validation",
            "accepted_clients": len(client_params),
            "attempted_clients": len(partitions),
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

    # The final test set is not used to choose rounds or the deployment mode.
    final_global = test_model_detailed(global_model, test_loader)
    final_org_metrics = [
        {"org_id": stats.org_id, "org_name": stats.org_name,
         "metrics": final_global.to_dict(), "evaluation_split": "common_test"}
        for stats, _ in partitions]

    # Standalone baselines: same starting seed, client data, optimizer restart
    # schedule, class weights and number of local epochs. No aggregation.
    local_only_metrics = []
    baseline_partitions = build_benchmark_partitions(
        splits, num_partitions=num_clients, seed=seed, iid=iid, alpha=alpha)
    for stats, train_ld in baseline_partitions:
        torch.manual_seed(seed)
        local_model = ThreatNet()
        best_local_f1 = -1.0
        best_local_state = None
        best_local_round = 0
        for rnd in range(1, num_rounds + 1):
            train_model(local_model, train_ld, epochs=local_epochs, lr=lr,
                        weight_decay=weight_decay, class_weights=global_class_weights)
            local_val = test_model_detailed(local_model, val_loader)
            if local_val.f1 > best_local_f1:
                best_local_f1 = local_val.f1
                best_local_state = copy.deepcopy(local_model.state_dict())
                best_local_round = rnd
        local_model.load_state_dict(best_local_state)
        local_eval = test_model_detailed(local_model, test_loader)
        local_only_metrics.append({
            "org_id": stats.org_id, "org_name": stats.org_name,
            "metrics": local_eval.to_dict(),
            "confusion_matrix": local_eval.confusion_matrix,
            "best_round": best_local_round,
            "evaluation_split": "common_test",
        })

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
        "momentum": momentum,
        "norm_guard_multiplier": norm_guard_multiplier,
        "best_round": best_round,
        "best_validation_f1": best_val_f1 * 100,
        "proximal_mu": proximal_mu,
        "evaluation_protocol": "common_held_out_v1",
        "preprocessing": splits.get("preprocessing"),
        "split_seed": seed,
        "split_counts": {k: len(splits["y_" + k]) for k in ("train", "val", "test")},
        "round_evaluation_split": "validation",
        "final_evaluation_split": "common_test",
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
                "formal DP guarantee not established")

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
            ("total_samples", float(sum(iid_result["split_counts"].values()) if "split_counts" in iid_result else sum(p["total_samples"] for p in iid_result["partition_stats"]))),
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
                    ("duration_s", rd["duration_s"]),
                    *(([("accepted_clients", rd["accepted_clients"])] if "accepted_clients" in rd else [])),
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
                    ("false_positive_rate", org_fed["metrics"]["false_positive_rate"], org_local["metrics"]["false_positive_rate"]),
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
        normalization_method="robust_zscore_v1" if result.get("preprocessing") else "zscore",
        preprocessing_json=np.array(json.dumps(result.get("preprocessing"))),
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
        "momentum": getattr(args, 'momentum', 0.0),
        "norm_guard_multiplier": getattr(args, 'norm_guard', 0.0),
        "privacy_clipping_enabled": getattr(args, 'enable_clipping', True),
        "privacy_clip_norm": getattr(args, 'clip_norm', 5.0),
        "privacy_dp_noise_enabled": getattr(args, 'enable_dp_noise', True),
        "privacy_noise_multiplier": getattr(args, 'noise_multiplier', 0.1),
        "mode": mode,
        "best_round": result.get("best_round", args.rounds),
        "final_accuracy": result["final_global"]["accuracy"],
        "final_f1": result["final_global"]["f1"],
        "final_weighted_f1": result["final_global"].get("weighted_f1", result["final_global"]["f1"]),
        "final_loss": result["final_global"]["loss"],
        "proximal_mu": result.get("proximal_mu", 0.0),
        "evaluation_protocol": result.get("evaluation_protocol"),
        "split_counts": result.get("split_counts"),
        "best_validation_f1": result.get("best_validation_f1"),
        "normalization_method": "robust_zscore_v1" if result.get("preprocessing") else "zscore",
        "preprocessing": result.get("preprocessing"),
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
    # Privacy flags
    parser.add_argument("--clip-norm", type=float, default=5.0,
                        help="L2 clip norm for update clipping (default: 5.0)")
    parser.add_argument("--noise-multiplier", type=float, default=0.1,
                        help="Noise multiplier for DP (noise_std = multiplier * clip_norm, default: 0.1)")
    parser.add_argument("--no-clipping", dest="enable_clipping", action="store_false",
                        help="Disable update clipping")
    parser.add_argument("--no-dp-noise", dest="enable_dp_noise", action="store_false",
                        help="Disable DP noise addition")
    parser.add_argument("--no-validation", dest="enable_validation", action="store_false",
                        help="Disable server-side update validation")
    parser.add_argument("--max-update-norm", type=float, default=200.0,
                        help="Max update norm threshold for server validation (default: 200.0)")
    # Stabilization flags
    parser.add_argument("--momentum", type=float, default=0.0,
                        help="Server-side momentum (EMA blending weight for previous global model, 0=off, suggested: 0.2)")
    parser.add_argument("--norm-guard", type=float, default=0.0, dest="norm_guard",
                        help="Norm guard multiplier: cap client updates whose norm exceeds median*multiplier (0=off, suggested: 3.0)")
    parser.add_argument("--proximal-mu", type=float, default=0.0)
    parser.add_argument("--no-publish", action="store_true", help="Save separate JSON only; do not change latest checkpoint or database")
    parser.set_defaults(class_weights=True, enable_clipping=True, enable_dp_noise=True, enable_validation=True)
    args = parser.parse_args()

    if args.rounds < 1 or args.epochs < 1 or args.samples < 0 or not np.isfinite(args.proximal_mu) or args.proximal_mu < 0:
        parser.error("Invalid rounds, epochs, samples or proximal-mu")
    if not np.isfinite(args.alpha) or args.alpha <= 0:
        parser.error("alpha must be positive")
    if not 0 <= args.momentum < 1:
        parser.error("momentum must be in [0, 1)")
    # Build privacy config from CLI flags
    privacy_config = PrivacyConfig(
        enable_clipping=args.enable_clipping,
        clip_norm=args.clip_norm,
        enable_dp_noise=args.enable_dp_noise,
        noise_multiplier=args.noise_multiplier,
        enable_validation=args.enable_validation,
        max_update_norm=args.max_update_norm,
    )

    experiment_id = f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger.info(f"Experiment ID: {experiment_id}")
    logger.info("Running IID vs Non-IID comparison experiments")
    logger.info(f"  Rounds: {args.rounds}, Alpha: {args.alpha}, Samples: {args.samples or 'all'}")
    logger.info(f"  LR: {args.lr}, Weight decay: {args.weight_decay}, Class weights: {args.class_weights}")
    logger.info(f"  Privacy: clipping={args.enable_clipping} (norm={args.clip_norm}), "
                f"dp_noise={args.enable_dp_noise} (multiplier={args.noise_multiplier})")
    logger.info(f"  Momentum: {args.momentum}, Norm guard: {args.norm_guard}")

    # Set global seed
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    splits = create_benchmark_splits(n_samples=args.samples, seed=args.seed)

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
        privacy_config=privacy_config,
        momentum=args.momentum,
        norm_guard_multiplier=args.norm_guard,
        proximal_mu=args.proximal_mu,
        splits=splits,
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
        privacy_config=privacy_config,
        momentum=args.momentum,
        norm_guard_multiplier=args.norm_guard,
        proximal_mu=args.proximal_mu,
        splits=splits,
    )

    # Select deployment model using validation macro-F1, never test metrics
    iid_f1 = iid_result["best_validation_f1"]
    noniid_f1 = noniid_result["best_validation_f1"]
    if iid_f1 >= noniid_f1:
        best_model = iid_model
        best_mode = "iid"
        best_result = iid_result
        best_norm_mean = iid_norm_mean
        best_norm_std = iid_norm_std
        logger.info(f"Best model: IID (validation F1={iid_f1:.2f}%)")
    else:
        best_model = noniid_model
        best_mode = "non_iid"
        best_result = noniid_result
        best_norm_mean = noniid_norm_mean
        best_norm_std = noniid_norm_std
        logger.info(f"Best model: Non-IID (validation F1={noniid_f1:.2f}%)")

    if not args.no_publish:
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
    results["selected_mode"] = best_mode
    results["selection_metric"] = "validation_macro_f1"
    output_path = f"{experiment_id}_results.json" if args.no_publish else "experiment_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Saved results to %s", output_path)
    if args.no_publish:
        return

    # Persist to DB
    args_dict = {
        "alpha": args.alpha,
        "rounds": args.rounds,
        "num_clients": 3,
        "samples": args.samples,
        "seed": args.seed,
        "epochs": args.epochs,
        "momentum": args.momentum,
        "norm_guard": args.norm_guard,
        "clip_norm": args.clip_norm,
        "noise_multiplier": args.noise_multiplier,
        "enable_clipping": args.enable_clipping,
        "enable_dp_noise": args.enable_dp_noise,
    }
    logger.info("Persisting results to database...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_save_experiment_results(iid_result, noniid_result, experiment_id, args_dict))
    loop.close()

    logger.info("All done!")


if __name__ == "__main__":
    main()
