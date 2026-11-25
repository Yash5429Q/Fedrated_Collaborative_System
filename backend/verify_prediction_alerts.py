"""Verify the running local backend. With --record-one, intentionally save one dataset-based alert."""
from argparse import ArgumentParser
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

BASE = "http://127.0.0.1:8000"
EXPERIMENT = "exp_20261125_173246_9acfd8aa"


def request(path, payload=None):
    req = Request(BASE + path, data=None if payload is None else json.dumps(payload, allow_nan=False).encode(), headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--record-one", action="store_true", help="Save one DoS prediction alert from the frozen test dataset. Each run creates a new alert.")
    args = parser.parse_args()
    h = request("/api/predict/health")
    require(h["model_loaded"] and h["experiment_id"] == EXPERIMENT and h["mode"] == "non_iid" and h["attack_threshold"] == .75, "Wrong running checkpoint")
    before = request("/api/threats")
    n = before["summary"]["total"]
    require(before["historical_demo_count"] == 5 and before["summary"]["blocked"] == 0, "Demo separation failed")
    dash = request("/api/dashboard")
    require(dash["threats_detected"] == n and dash["historical_demo_threat_count"] == 5, "Dashboard counts do not match")
    privacy = request("/api/privacy")
    require(privacy["historical_demo_event_count"] == 4 and not any(e["id"] in {"sec-001","sec-002","sec-003","sec-004"} for e in privacy["security_events"]), "Demo security events are still visible")
    perf = request("/api/performance")
    require(perf["summary"]["federated_accuracy"] == 94.48, "Wrong performance data")
    scores = {r["scenario"]: r["robustness_score"] for r in perf["non_iid_results"]}
    require(scores.get("IID") == 100 and scores.get("Non-IID (alpha=0.5)") == 97.45, "Wrong accuracy retention")
    from app.ml.data import create_benchmark_splits
    splits = create_benchmark_splits(seed=42)
    features = {c: splits["X_test"][next(i for i,y in enumerate(splits["y_test"]) if int(y)==c)].tolist() for c in (0,1)}
    for c in (0,1):
        result = request("/api/predict", {"features": features[c], "record_alert": False})
        require(result["model"]["experiment_id"] == EXPERIMENT and result["prediction"]["class_id"] == c and result["alert_id"] is None, "Read-only prediction failed")
        print("Read-only prediction:", result["prediction"]["label"], "score:", result["prediction"]["confidence"])
    # Recording enabled for normal traffic still must not create an alert.
    result = request("/api/predict", {"features": features[0], "record_alert": True})
    require(result["prediction"]["class_id"] == 0 and result["alert_id"] is None, "Normal input incorrectly saved")
    try:
        request("/api/predict", {"features": [0.0]*67, "record_alert": True})
    except HTTPError as exc:
        require(exc.code in (400,422), "Unexpected validation status")
        print("Invalid input rejected:", exc.code)
    else:
        raise RuntimeError("Invalid input accepted")
    require(request("/api/threats")["summary"]["total"] == n, "Unexpected alert side effect")
    print("Read-only checks passed. Historical demo threats: 5; historical demo security events: 4; accuracy retention: 97.45%.")
    if not args.record_one:
        print("PASS: no new alert saved. Use --record-one to test persistence explicitly.")
        return
    result = request("/api/predict", {"features": features[1], "record_alert": True})
    aid = result["alert_id"]
    require(result["prediction"]["class_id"] == 1 and aid and aid.startswith("pred-"), "Attack prediction not saved")
    print("Saved dataset-based alert:", aid)
    data = request("/api/threats?"+urlencode({"search":aid}))
    require(data["total"] == 1 and data["summary"]["total"] == n+1, "Persisted alert not found or count incorrect")
    row = data["detections"][0]
    require(row["id"] == aid and row["threat_type"] == "DoS" and row["status"] == "detected" and row["raw_features"] == {} and row["organization_id"] == "" and row["source_ip"] == row["destination_ip"] == row["protocol"] == "" and row["port"] == 0 and EXPERIMENT in row["description"], "Stored alert is inconsistent")
    require(request("/api/dashboard")["threats_detected"] == n+1, "Dashboard did not reflect saved alert")
    print("Alert count:", n, "->", n+1)
    print("PASS: prediction alert persistence, privacy-safe storage and dashboard integration.")


if __name__ == "__main__":
    main()
