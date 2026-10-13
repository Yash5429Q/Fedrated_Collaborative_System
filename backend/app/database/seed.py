"""
Database seed — inserts demo data into SQLite on first startup.
Safe to call on every restart: checks if the organizations table is
empty and exits immediately if data already exists (idempotent).
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client_participation import ClientParticipation
from app.models.metric import Metric
from app.models.model_version import ModelVersion
from app.models.organization import Organization
from app.models.privacy_event import PrivacyEvent
from app.models.threat_detection import ThreatDetection
from app.models.training_round import TrainingRound
from app.models.validation_test import ValidationTest
from app.repositories.organization_repo import OrganizationRepo

logger = logging.getLogger(__name__)


async def seed_if_empty(db: AsyncSession) -> None:
    """Insert demo data only if the database is empty."""
    repo = OrganizationRepo(db)
    if await repo.count() > 0:
        logger.info("Database already seeded — skipping.")
        return
    logger.info("Seeding database with demo data …")
    await _seed_organizations(db)
    await _seed_training_rounds(db)
    await _seed_client_participations(db)
    await _seed_model_versions(db)
    await _seed_threat_detections(db)
    await _seed_metrics(db)
    await _seed_privacy_events(db)
    await _seed_validation_tests(db)
    await db.commit()
    logger.info("Database seeded successfully.")


# ── Organizations ──────────────────────────────────────────────

async def _seed_organizations(db: AsyncSession) -> None:
    orgs = [
        Organization(
            id="org-alpha", name="Organization Alpha", status="active",
            description="Federated participant — 45,000 samples",
            dataset_size=45000, participation_rate=1.0,
            local_model_status="trained", local_model_accuracy=88.2,
            current_round=12, last_update="2026-08-31T11:24:12Z",
            joined_at="2026-01-01T00:00:00Z", privacy_mode="Model updates only",
            data_distribution_json=json.dumps([
                {"label": "DoS/DDoS",    "value": 38.0, "color": "#f87171"},
                {"label": "Brute Force", "value": 22.0, "color": "#fb923c"},
                {"label": "Port Scan",   "value": 18.0, "color": "#fbbf24"},
                {"label": "Malware",     "value": 12.0, "color": "#a78bfa"},
                {"label": "Normal",      "value": 10.0, "color": "#6b7280"},
            ]),
        ),
        Organization(
            id="org-beta", name="Organization Beta", status="active",
            description="Federated participant — 32,000 samples",
            dataset_size=32000, participation_rate=1.0,
            local_model_status="trained", local_model_accuracy=83.7,
            current_round=12, last_update="2026-08-31T11:19:44Z",
            joined_at="2026-01-01T00:00:00Z", privacy_mode="Model updates only",
            data_distribution_json=json.dumps([
                {"label": "Normal",      "value": 45.0, "color": "#6b7280"},
                {"label": "Port Scan",   "value": 25.0, "color": "#fbbf24"},
                {"label": "DoS/DDoS",    "value": 15.0, "color": "#f87171"},
                {"label": "Brute Force", "value": 10.0, "color": "#fb923c"},
                {"label": "Malware",     "value":  5.0, "color": "#a78bfa"},
            ]),
        ),
        Organization(
            id="org-gamma", name="Organization Gamma", status="active",
            description="Federated participant — 28,000 samples",
            dataset_size=28000, participation_rate=1.0,
            local_model_status="trained", local_model_accuracy=85.9,
            current_round=12, last_update="2026-08-31T11:24:01Z",
            joined_at="2026-01-01T00:00:00Z", privacy_mode="Model updates only",
            data_distribution_json=json.dumps([
                {"label": "Brute Force", "value": 40.0, "color": "#fb923c"},
                {"label": "Malware",     "value": 28.0, "color": "#a78bfa"},
                {"label": "DoS/DDoS",    "value": 15.0, "color": "#f87171"},
                {"label": "Normal",      "value": 12.0, "color": "#6b7280"},
                {"label": "Port Scan",   "value":  5.0, "color": "#fbbf24"},
            ]),
        ),
        Organization(
            id="org-delta", name="Organization Delta", status="active",
            description="Federated participant — 18,000 samples",
            dataset_size=18000, participation_rate=0.92,
            local_model_status="trained", local_model_accuracy=81.3,
            current_round=12, last_update="2026-08-31T11:05:38Z",
            joined_at="2026-01-01T00:00:00Z", privacy_mode="Model updates only",
            data_distribution_json=json.dumps([
                {"label": "Normal",      "value": 50.0, "color": "#6b7280"},
                {"label": "Malware",     "value": 30.0, "color": "#a78bfa"},
                {"label": "DoS/DDoS",    "value": 12.0, "color": "#f87171"},
                {"label": "Brute Force", "value":  5.0, "color": "#fb923c"},
                {"label": "Port Scan",   "value":  3.0, "color": "#fbbf24"},
            ]),
        ),
        Organization(
            id="org-epsilon", name="Organization Epsilon", status="offline",
            description="Federated participant — 12,000 samples",
            dataset_size=12000, participation_rate=0.83,
            local_model_status="pending", local_model_accuracy=None,
            current_round=11, last_update="2026-08-31T09:48:22Z",
            joined_at="2026-01-01T00:00:00Z", privacy_mode="Model updates only",
            data_distribution_json=json.dumps([
                {"label": "Port Scan",   "value": 55.0, "color": "#fbbf24"},
                {"label": "Normal",      "value": 30.0, "color": "#6b7280"},
                {"label": "DoS/DDoS",    "value": 10.0, "color": "#f87171"},
                {"label": "Brute Force", "value":  5.0, "color": "#fb923c"},
            ]),
        ),
    ]
    for org in orgs:
        db.add(org)
    await db.flush()


# ── Training Rounds ────────────────────────────────────────────

_ROUND_DATA = [
    (1,  68.2, 0.89, 62.1, 41, "v1.0",  "2026-08-31T07:00:00Z", "2026-08-31T07:00:41Z", 5),
    (2,  73.5, 0.76, 69.8, 38, "v2.0",  "2026-08-31T07:01:00Z", "2026-08-31T07:01:38Z", 5),
    (3,  78.1, 0.64, 74.5, 36, "v3.0",  "2026-08-31T07:02:00Z", "2026-08-31T07:02:36Z", 5),
    (4,  81.4, 0.54, 78.2, 39, "v4.0",  "2026-08-31T07:03:00Z", "2026-08-31T07:03:39Z", 5),
    (5,  84.6, 0.46, 81.9, 37, "v5.0",  "2026-08-31T07:04:00Z", "2026-08-31T07:04:37Z", 5),
    (6,  87.0, 0.40, 84.3, 35, "v6.0",  "2026-08-31T07:05:00Z", "2026-08-31T07:05:35Z", 5),
    (7,  89.2, 0.34, 86.8, 40, "v7.0",  "2026-08-31T07:06:00Z", "2026-08-31T07:06:40Z", 5),
    (8,  90.8, 0.29, 88.6, 38, "v8.0",  "2026-08-31T07:07:00Z", "2026-08-31T07:07:38Z", 5),
    (9,  92.1, 0.25, 89.9, 36, "v9.0",  "2026-08-31T07:08:00Z", "2026-08-31T07:08:36Z", 5),
    (10, 93.3, 0.22, 91.0, 39, "v10.0", "2026-08-31T07:09:00Z", "2026-08-31T07:09:39Z", 5),
    (11, 94.1, 0.20, 91.8, 37, "v11.0", "2026-08-31T07:10:00Z", "2026-08-31T07:10:37Z", 4),
    (12, 94.7, 0.19, 92.3, 42, "v12.0", "2026-08-31T07:11:00Z", "2026-08-31T07:11:42Z", 4),
]


async def _seed_training_rounds(db: AsyncSession) -> None:
    for rn, acc, loss, f1, dur, ver, sa, ca, pc in _ROUND_DATA:
        tr = TrainingRound(
            round_number=rn, status="completed",
            started_at=sa, completed_at=ca, duration_s=dur,
            participating_clients=pc, total_clients=5,
            accuracy=acc, loss=loss, f1=f1,
            model_version=ver, aggregation_method="FedAvg",
        )
        db.add(tr)
    await db.flush()


# ── Client Participations ──────────────────────────────────────

async def _seed_client_participations(db: AsyncSession) -> None:
    from sqlalchemy import select
    # Get round id lookup
    result = await db.execute(select(TrainingRound).order_by(TrainingRound.round_number))
    rounds = {r.round_number: r.id for r in result.scalars().all()}

    # (round_number, org_id, status, local_acc, local_loss, samples, dur_s, upd_mb)
    participations = []
    orgs = [
        ("org-alpha",   88.2, 0.34, 45000, 42, 2.4),
        ("org-beta",    83.7, 0.41, 32000, 36, 2.4),
        ("org-gamma",   85.9, 0.38, 28000, 33, 2.4),
        ("org-delta",   81.3, 0.44, 18000, 44, 2.4),
        ("org-epsilon", None, None, None,  None, None),
    ]
    for rn, _, _, _, _, _, _, _, pc in _ROUND_DATA:
        round_id = rounds[rn]
        for i, (org_id, acc, loss, samples, dur, upd) in enumerate(orgs):
            is_epsilon = org_id == "org-epsilon"
            skipped = is_epsilon and rn == 12
            status = "skipped" if skipped else "completed"
            participations.append(ClientParticipation(
                round_id=round_id, org_id=org_id,
                status=status,
                local_accuracy=None if skipped else acc,
                local_loss=None if skipped else loss,
                samples_used=None if skipped else samples,
                duration_s=None if skipped else dur,
                update_size_mb=None if skipped else upd,
            ))
    for cp in participations:
        db.add(cp)
    await db.flush()


# ── Model Versions ─────────────────────────────────────────────

async def _seed_model_versions(db: AsyncSession) -> None:
    from sqlalchemy import select
    result = await db.execute(select(TrainingRound).order_by(TrainingRound.round_number))
    rounds = {r.round_number: r.id for r in result.scalars().all()}

    for rn, acc, loss, f1, _, ver, _, ca, _ in _ROUND_DATA:
        mv = ModelVersion(
            version=ver, round_id=rounds[rn],
            accuracy=acc, loss=loss, f1=f1,
            false_positive_rate=round(8.6 - (rn - 1) * 0.45, 2),
            created_at=ca, is_global=True,
        )
        db.add(mv)
    await db.flush()


# ── Threat Detections ──────────────────────────────────────────

async def _seed_threat_detections(db: AsyncSession) -> None:
    detections = [
        ThreatDetection(
            id="td-001", timestamp="2026-08-31T11:24:12Z",
            org_id="org-alpha", organization_name="Organization Alpha",
            threat_type="DoS/DDoS", severity="critical", confidence=97.3,
            status="blocked", model_version="v12.0",
            source_ip="10.0.1.45", destination_ip="192.168.1.10",
            protocol="TCP", port=80,
            description="High-volume SYN flood targeting web server. Traffic matches distributed DoS signature.",
            raw_features_json=json.dumps({"flow_duration": 12450, "fwd_packets": 98432, "bwd_packets": 124, "flow_bytes_per_s": 8934210}),
            detection_method="federated",
        ),
        ThreatDetection(
            id="td-002", timestamp="2026-08-31T11:21:45Z",
            org_id="org-gamma", organization_name="Organization Gamma",
            threat_type="Brute Force", severity="high", confidence=94.1,
            status="detected", model_version="v12.0",
            source_ip="10.0.3.112", destination_ip="192.168.3.5",
            protocol="TCP", port=22,
            description="Repeated SSH authentication failures. 847 attempts in 5 minutes.",
            raw_features_json=json.dumps({"flow_duration": 302000, "fwd_packets": 1694, "bwd_packets": 1694, "flow_bytes_per_s": 5620}),
            detection_method="federated",
        ),
        ThreatDetection(
            id="td-003", timestamp="2026-08-31T11:18:33Z",
            org_id="org-beta", organization_name="Organization Beta",
            threat_type="Malware", severity="high", confidence=91.8,
            status="investigating", model_version="v12.0",
            source_ip="10.0.2.78", destination_ip="203.0.113.42",
            protocol="TCP", port=443,
            description="Outbound C2 beacon pattern. Periodic HTTPS connections to known malicious infrastructure.",
            raw_features_json=json.dumps({"flow_duration": 86400000, "fwd_packets": 288, "bwd_packets": 288, "flow_bytes_per_s": 42}),
            detection_method="federated",
        ),
        ThreatDetection(
            id="td-004", timestamp="2026-08-31T11:15:07Z",
            org_id="org-alpha", organization_name="Organization Alpha",
            threat_type="Port Scan", severity="medium", confidence=88.5,
            status="blocked", model_version="v12.0",
            source_ip="10.0.1.203", destination_ip="192.168.1.0/24",
            protocol="TCP", port=0,
            description="Horizontal port scan across subnet.",
            raw_features_json=json.dumps({"flow_duration": 30000, "fwd_packets": 260096, "bwd_packets": 3841, "flow_bytes_per_s": 346800}),
            detection_method="local",
        ),
        ThreatDetection(
            id="td-005", timestamp="2026-08-31T11:10:52Z",
            org_id="org-delta", organization_name="Organization Delta",
            threat_type="Data Exfiltration", severity="critical", confidence=96.2,
            status="detected", model_version="v11.0",
            source_ip="10.0.4.56", destination_ip="198.51.100.88",
            protocol="TCP", port=443,
            description="2.3 GB encrypted transfer to external host outside business hours.",
            raw_features_json=json.dumps({"flow_duration": 2700000, "fwd_packets": 1632000, "bwd_packets": 48000, "flow_bytes_per_s": 852000}),
            detection_method="federated",
        ),
    ]
    for td in detections:
        db.add(td)
    await db.flush()


# ── Performance Metrics ────────────────────────────────────────

async def _seed_metrics(db: AsyncSession) -> None:
    now = "2026-08-31T12:00:00Z"
    metrics: list[Metric] = []

    # ── Summary (single values) ──────────────────────────────
    for name, value, mtype in [
        ("federated_accuracy",  94.7, "federated"),
        ("local_avg_accuracy",  84.7, "local"),
        ("accuracy_gain",       10.0, "comparison"),
        ("federated_f1",        92.3, "federated"),
        ("local_avg_f1",        81.5, "local"),
        ("f1_gain",             10.8, "comparison"),
        ("federated_fpr",        3.2, "federated"),
        ("local_avg_fpr",        8.6, "local"),
        ("fpr_reduction",        5.4, "comparison"),
    ]:
        metrics.append(Metric(timestamp=now, metric_name=name, metric_value=value,
                              model_type=mtype, category="summary"))

    # ── Comparison (local vs federated per metric label) ─────
    comparisons = [
        ("Accuracy",            84.7, 94.7),
        ("Precision",           82.1, 92.8),
        ("Recall",              80.4, 91.9),
        ("F1 Score",            81.5, 92.3),
        ("False-Positive Rate",  8.6,  3.2),
        ("Attack Detection",    79.2, 93.1),
        ("Non-IID Robustness",  61.3, 87.4),
    ]
    for label, local_val, fed_val in comparisons:
        metrics.append(Metric(timestamp=now, metric_name=label, metric_value=local_val,
                              model_type="local", category="comparison"))
        metrics.append(Metric(timestamp=now, metric_name=label, metric_value=fed_val,
                              model_type="federated", category="comparison"))

    # ── Org performance (one row per org per metric) ─────────
    org_perf = [
        ("org-alpha",   "Organization Alpha",   88.2, 86.3, 87.1, 85.6, 94.7, 92.3, 6.5),
        ("org-beta",    "Organization Beta",    83.7, 81.9, 82.4, 81.4, 94.7, 92.3, 11.0),
        ("org-gamma",   "Organization Gamma",   85.9, 83.7, 84.2, 83.2, 94.7, 92.3, 8.8),
        ("org-delta",   "Organization Delta",   81.3, 79.4, 80.1, 78.7, 94.7, 92.3, 13.4),
        ("org-epsilon", "Organization Epsilon", 79.2, 77.1, 77.8, 76.4, 94.7, 92.3, 15.5),
    ]
    for org_id, org_name, la, lf, lp, lr, fa, ff, gain in org_perf:
        for mname, val, mtype in [
            ("local_accuracy", la, "local"), ("local_f1", lf, "local"),
            ("local_precision", lp, "local"), ("local_recall", lr, "local"),
            ("federated_accuracy", fa, "federated"), ("federated_f1", ff, "federated"),
            ("gain", gain, "comparison"),
        ]:
            metrics.append(Metric(timestamp=now, metric_name=mname, metric_value=val,
                                  model_type=mtype, org_id=org_id, category="org_performance"))

    # ── Non-IID results ──────────────────────────────────────
    noniid = [
        ("Uniform (IID)",       100.0, 88.4, 94.7, 96),
        ("Mild Skew (α=1.0)",     1.0, 85.9, 93.8, 89),
        ("Moderate (α=0.5)",      0.5, 84.7, 92.4, 83),
        ("Heavy Skew (α=0.1)",    0.1, 78.3, 89.1, 74),
        ("Extreme (α=0.01)",     0.01, 68.1, 84.6, 61),
    ]
    for scenario, alpha, la, fa, rob in noniid:
        metrics.append(Metric(timestamp=now, metric_name="alpha",          metric_value=alpha, model_type="noniid", category="noniid",
                              round_number=None))
        metrics.append(Metric(timestamp=now, metric_name="local_accuracy", metric_value=la,    model_type="local",  category="noniid",
                              round_number=None))
        metrics.append(Metric(timestamp=now, metric_name="fed_accuracy",   metric_value=fa,    model_type="federated", category="noniid",
                              round_number=None))
        metrics.append(Metric(timestamp=now, metric_name="robustness",     metric_value=rob,   model_type="noniid", category="noniid",
                              round_number=None))
        # store scenario label as a separate metric with value=0 and name=scenario
        metrics.append(Metric(timestamp=now, metric_name="scenario__" + scenario, metric_value=alpha,
                              model_type="noniid", category="noniid_scenario"))

    # ── Round performance ─────────────────────────────────────
    round_perf = [
        (1,64.3,68.2,61.1,62.1),(2,68.7,73.5,65.8,69.8),(3,72.4,78.1,69.7,74.5),
        (4,75.1,81.4,72.8,78.2),(5,77.8,84.6,75.3,81.9),(6,79.6,87.0,77.4,84.3),
        (7,81.2,89.2,79.0,86.8),(8,82.4,90.8,80.2,88.6),(9,83.3,92.1,81.1,89.9),
        (10,84.0,93.3,81.8,91.0),(11,84.4,94.1,82.1,91.8),(12,84.7,94.7,81.5,92.3),
    ]
    for rn, la, fa, lf, ff in round_perf:
        for mname, val, mtype in [
            ("local_avg_accuracy", la, "local"), ("federated_accuracy", fa, "federated"),
            ("local_avg_f1", lf, "local"), ("federated_f1", ff, "federated"),
        ]:
            metrics.append(Metric(timestamp=now, metric_name=mname, metric_value=val,
                                  model_type=mtype, round_number=rn, category="round_perf"))

    # ── Collaboration benefit ─────────────────────────────────
    collab = [
        ("Accuracy",        84.7, 94.7, 10.0, 11.8),
        ("F1 Score",        81.5, 92.3, 10.8, 13.3),
        ("Recall",          80.4, 91.9, 11.5, 14.3),
        ("Attack Detection",79.2, 93.1, 13.9, 17.6),
        ("FPR Reduction",    8.6,  3.2,  5.4, 62.8),
    ]
    for mname, la, fa, imp, imp_pct in collab:
        metrics.append(Metric(timestamp=now, metric_name=mname + "__local",      metric_value=la,      model_type="local",      category="collab_benefit"))
        metrics.append(Metric(timestamp=now, metric_name=mname + "__federated",  metric_value=fa,      model_type="federated",  category="collab_benefit"))
        metrics.append(Metric(timestamp=now, metric_name=mname + "__improvement",metric_value=imp,     model_type="comparison", category="collab_benefit"))
        metrics.append(Metric(timestamp=now, metric_name=mname + "__pct",        metric_value=imp_pct, model_type="comparison", category="collab_benefit"))

    # ── Confusion matrix cells ────────────────────────────────
    cm_labels = ["DoS", "Brute Force", "Port Scan", "Malware", "Normal"]
    local_diag  = [841, 758, 779, 741, 864]
    fed_diag    = [891, 823, 836, 807, 934]
    local_off   = [24,18,9,12,31,22,14,19,15,28,11,21,10,18,14,41,29,22,18,16]
    fed_off     = [8,4,2,3,7,8,3,3,5,6,2,5,3,5,4,5,6,4,3,2]
    off_idx = 0
    for i, actual in enumerate(cm_labels):
        for j, predicted in enumerate(cm_labels):
            key = f"{actual}__{predicted}"
            if i == j:
                local_v = local_diag[i]
                fed_v   = fed_diag[i]
            else:
                local_v = local_off[off_idx % len(local_off)]
                fed_v   = fed_off[off_idx % len(fed_off)]
                off_idx += 1
            metrics.append(Metric(timestamp=now, metric_name=key, metric_value=float(local_v),
                                  model_type="local",     category="confusion_matrix"))
            metrics.append(Metric(timestamp=now, metric_name=key, metric_value=float(fed_v),
                                  model_type="federated", category="confusion_matrix"))

    for m in metrics:
        db.add(m)
    await db.flush()


# ── Privacy Events ─────────────────────────────────────────────

async def _seed_privacy_events(db: AsyncSession) -> None:
    events = [
        PrivacyEvent(id="sec-001", timestamp="2026-08-31T11:30:00Z", org_id=None,
                     event_type="Unknown client connection attempt", category="Access Control",
                     severity="warning", status="resolved", detail="Unregistered client refused."),
        PrivacyEvent(id="sec-002", timestamp="2026-08-31T11:15:22Z", org_id="org-epsilon",
                     event_type="Client disconnected mid-round", category="Availability",
                     severity="info", status="resolved", detail="Epsilon offline during round 12."),
        PrivacyEvent(id="sec-003", timestamp="2026-08-31T10:44:18Z", org_id=None,
                     event_type="Large model update rejected", category="Update Validation",
                     severity="warning", status="resolved", detail="Norm 12.4× expected — discarded."),
        PrivacyEvent(id="sec-004", timestamp="2026-08-30T22:11:44Z", org_id=None,
                     event_type="Repeated connection probe", category="Access Control",
                     severity="critical", status="monitoring", detail="14 probes from 203.0.113.77."),
    ]
    for ev in events:
        db.add(ev)
    await db.flush()


# ── Validation Tests ───────────────────────────────────────────

async def _seed_validation_tests(db: AsyncSession) -> None:
    tests = [
        ValidationTest(id="TC-101", name="Federated Training Convergence",
                       category="AC-1 Representative Operation",
                       description="Verify global model converges to ≥90% accuracy over 12 rounds.",
                       expected_result="Accuracy ≥ 90% at round 12",
                       actual_result="Mock: 94.7% (DEMO — not on live system)",
                       status="warning", execution_state="mock_run",
                       timestamp="2026-08-31T11:30:00Z",
                       notes="Must re-run once Flower pipeline integrated."),
        ValidationTest(id="TC-102", name="Multi-Organization Participation",
                       category="AC-1 Representative Operation",
                       description="All orgs join and submit updates in one round.",
                       expected_result="≥4 of 5 orgs complete training",
                       actual_result=None, status="pending", execution_state="not_run",
                       timestamp=None, notes="Requires live Flower server."),
        ValidationTest(id="TC-103", name="Threat Detection Accuracy",
                       category="AC-1 Representative Operation",
                       description="Evaluate global model on held-out test set.",
                       expected_result="Accuracy ≥90%, F1 ≥88%",
                       actual_result=None, status="pending", execution_state="not_run",
                       timestamp=None, notes="Requires real dataset split."),
        ValidationTest(id="TC-201", name="Non-IID Degradation",
                       category="AC-2 Boundary & Failure",
                       description="Measure degradation as Dirichlet α → 0.",
                       expected_result="Federated ≥80% at α=0.1",
                       actual_result="Mock: 89.1% at α=0.1 (DEMO)",
                       status="warning", execution_state="mock_run",
                       timestamp="2026-08-31T10:00:00Z",
                       notes="Simulated with mock distribution."),
        ValidationTest(id="TC-202", name="Single Organization Dropout",
                       category="AC-2 Boundary & Failure",
                       description="One org offline mid-round — training continues.",
                       expected_result="Round completes with ≥3 clients",
                       actual_result=None, status="pending", execution_state="not_run",
                       timestamp=None, notes="Requires live Flower with failure injection."),
        ValidationTest(id="TC-204", name="Oversized Update Rejection",
                       category="AC-2 Boundary & Failure",
                       description="Submit high-norm update — verify rejection.",
                       expected_result="Update rejected; round continues",
                       actual_result="Mock: Rejected (norm 12.4×) — sec event only",
                       status="warning", execution_state="mock_run",
                       timestamp="2026-08-31T10:44:18Z",
                       notes="Formal test requires norm-threshold config."),
        ValidationTest(id="TC-301", name="Privacy Boundary — Data Locality",
                       category="AC-3 Independent Acceptance",
                       description="Network capture confirms no raw data transmitted.",
                       expected_result="Only weight tensors in network capture",
                       actual_result="Code inspection passed; network test NOT RUN",
                       status="warning", execution_state="mock_run",
                       timestamp="2026-09-01T09:00:00Z",
                       notes="Full network-level verification pending."),
        ValidationTest(id="TC-302", name="Unauthorized Update Rejection",
                       category="AC-3 Independent Acceptance",
                       description="Unregistered client attempt — verify refused.",
                       expected_result="Connection refused; no update accepted",
                       actual_result="Mock: sec-001 event (DEMO — not formal test)",
                       status="warning", execution_state="mock_run",
                       timestamp="2026-08-31T11:30:00Z",
                       notes="Formal pen test required with real auth."),
        ValidationTest(id="TC-303", name="Invalid Update Handling",
                       category="AC-3 Independent Acceptance",
                       description="Wrong-shape tensor — server handles without crash.",
                       expected_result="Rejected; round continues",
                       actual_result=None, status="pending", execution_state="not_run",
                       timestamp=None, notes="Requires live Flower server."),
        ValidationTest(id="TC-401", name="Model Size Constraint",
                       category="AC-4 Frozen Resource Envelope",
                       description="Global model ≤50 MB on disk.",
                       expected_result="Model ≤ 50 MB",
                       actual_result=None, status="pending", execution_state="not_run",
                       timestamp=None, notes="Measurable once architecture frozen."),
        ValidationTest(id="TC-402", name="Inference Latency",
                       category="AC-4 Frozen Resource Envelope",
                       description="Single-sample CPU inference ≤100 ms.",
                       expected_result="Latency ≤ 100 ms",
                       actual_result=None, status="pending", execution_state="not_run",
                       timestamp=None, notes="Benchmark with torch.inference_mode()."),
        ValidationTest(id="TC-403", name="Training Round Time Budget",
                       category="AC-4 Frozen Resource Envelope",
                       description="Avg round ≤120s across 5 clients.",
                       expected_result="Avg duration ≤ 120s",
                       actual_result="Mock: ~38s avg (DEMO)",
                       status="warning", execution_state="mock_run",
                       timestamp="2026-08-31T11:00:00Z",
                       notes="Mock timing only — verify on target hardware."),
    ]
    for t in tests:
        db.add(t)
    await db.flush()
