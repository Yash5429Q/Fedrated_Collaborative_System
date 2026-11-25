"""Read-only preflight for the exported capstone candidate. No training or DB writes."""
from pathlib import Path
from collections import Counter
import argparse
import json
import numpy as np


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_id")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    exp_id = args.experiment_id
    require(Path(exp_id).name == exp_id and exp_id.startswith("exp_"), "Invalid experiment ID")
    checkpoint = root / "models" / exp_id
    results = json.loads((root / f"{exp_id}_results.json").read_text(encoding="utf-8"))
    meta = json.loads((checkpoint / "metadata.json").read_text(encoding="utf-8"))
    require(results["experiment_id"] == meta["experiment_id"] == exp_id, "Experiment ID mismatch")
    mode = results["exported_mode"]
    require(mode in ("iid", "non_iid") and meta["mode"] == mode, "Export mode mismatch")
    exp = results[mode]
    require(meta["preprocessing"] == exp["preprocessing"], "Preprocessing mismatch")
    require(meta["decision_rule"]["attack_threshold"] == exp["decision_rule"]["attack_threshold"], "Threshold mismatch")
    require(meta["seed"] == exp["split_seed"] and meta["best_round"] == exp["best_round"], "Seed or best round mismatch")
    require(meta["split_counts"] == exp["split_counts"], "Split counts mismatch")
    from app.database.seed import build_experiment_rows
    rows = build_experiment_rows(results, deployment_mode=mode)
    keys = [(r.category, r.model_type, r.metric_name, r.org_id, r.round_number) for r in rows]
    require(len(keys) == len(set(keys)), "Duplicate metric keys")
    require(all(np.isfinite(r.metric_value) for r in rows), "Non-finite metric")
    print("Prepared metric rows:", len(rows))
    print("Categories:", dict(sorted(Counter(r.category for r in rows).items())))
    import app.ml.inference as inf
    from app.ml.data import create_benchmark_splits
    require(inf._inference.load(str(checkpoint)), "Checkpoint loading failed")
    require(Path(inf._inference.checkpoint_path).resolve() == checkpoint.resolve(), "Unexpected fallback checkpoint")
    require(inf._inference.has_normalization, "Missing normalization")
    s = create_benchmark_splits(seed=meta["seed"])
    require(np.array_equal(s["norm_mean"], inf._inference.norm_mean), "Normalization mean mismatch")
    require(np.array_equal(s["norm_std"], inf._inference.norm_std), "Normalization std mismatch")
    require(s["preprocessing"] == meta["preprocessing"], "Reconstructed preprocessing mismatch")
    require(len(s["y_test"]) == exp["split_counts"]["test"], "Test size mismatch")
    cm = np.zeros((5,5), dtype=int)
    for raw, label in zip(s["X_test"], s["y_test"]):
        prediction = inf.predict(raw.tolist())
        require(prediction["model"]["experiment_id"] == exp_id, "Prediction checkpoint mismatch")
        cm[int(label), int(prediction["prediction"]["class_id"])] += 1
    require(cm.tolist() == exp["confusion_matrix"], f"Raw inference confusion matrix differs: {cm.tolist()}")
    print("Raw inference records:", int(cm.sum()))
    print("Confusion matrix:", cm.tolist())
    print("Accuracy:", round(100*np.trace(cm)/cm.sum(), 2))
    print("Exported mode:", mode)
    print("Attack threshold:", meta["decision_rule"]["attack_threshold"])
    print("PREFLIGHT PASSED: no database or deployment files modified.")


if __name__ == "__main__":
    main()
