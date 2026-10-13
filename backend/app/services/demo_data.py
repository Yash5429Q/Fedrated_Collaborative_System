"""
Demo data service.

Returns structured development data that mirrors the frontend mock data.
This service is the ONLY source of demo responses — all API routers call
into this module.

When real data sources are ready (Flower, PyTorch, database records),
each method here is replaced with a real query/service call.
The router layer never changes — only this service layer.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from app.schemas.dashboard import (
    DashboardResponse, ModelComparisonMetric, OrgActivityItem,
    RecentThreat, SystemComponent, ThreatCategory, TrainingRoundMetric,
)
from app.schemas.organizations import (
    DataSlice, Organization, OrganizationSummary, OrganizationsResponse,
    OrgTrainingRound,
)
from app.schemas.performance import (
    CollaborationBenefit, ConfusionCell, ConfusionMatrix,
    MetricComparison, NonIIDResult, OrgPerformanceRow,
    PerformanceResponse, PerformanceSummary, PerfRoundMetric,
)
from app.schemas.privacy import (
    OrgUpdateStatus, PrivacyProperty, PrivacyResponse,
    PrivacySummary, SecurityEvent,
)
from app.schemas.system import ComponentHealth, SystemResponse
from app.schemas.testing import (
    AcceptanceCriterion, TestCase, TestingResponse, TestSuiteSummary,
)
from app.schemas.threats import (
    ThreatDetection, ThreatSummary, ThreatTimelinePoint,
    ThreatTypeCount, ThreatsResponse,
)
from app.schemas.training import (
    ClientStatus, ParticipationPoint, TrainingResponse,
    TrainingRound, TrainingRoundsResponse, TrainingSummary,
)

_START_TIME = time.time()


# ─────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────

def get_dashboard() -> DashboardResponse:
    return DashboardResponse(
        total_organizations=5,
        active_organizations=4,
        current_round=12,
        total_rounds=12,
        threats_detected=1847,
        global_model_accuracy=94.7,
        f1_score=92.3,
        false_positive_rate=3.2,
        privacy_status="Data Local — Privacy Mechanisms Planned",
        training_rounds=[
            TrainingRoundMetric(round=r, accuracy=a, loss=l, f1=f)
            for r, a, l, f in [
                (1, 68.2, 0.89, 62.1), (2, 73.5, 0.76, 69.8),
                (3, 78.1, 0.64, 74.5), (4, 81.4, 0.54, 78.2),
                (5, 84.6, 0.46, 81.9), (6, 87.0, 0.40, 84.3),
                (7, 89.2, 0.34, 86.8), (8, 90.8, 0.29, 88.6),
                (9, 92.1, 0.25, 89.9), (10, 93.3, 0.22, 91.0),
                (11, 94.1, 0.20, 91.8), (12, 94.7, 0.19, 92.3),
            ]
        ],
        model_comparison=[
            ModelComparisonMetric(metric=m, local=l, federated=f)
            for m, l, f in [
                ("Accuracy", 84.7, 94.7), ("Precision", 82.1, 92.8),
                ("Recall", 80.4, 91.9), ("F1 Score", 81.5, 92.3),
            ]
        ],
        threat_categories=[
            ThreatCategory(name="DoS/DDoS",     count=423, color="#f87171"),
            ThreatCategory(name="Brute Force",  count=312, color="#fb923c"),
            ThreatCategory(name="Port Scan",    count=289, color="#fbbf24"),
            ThreatCategory(name="Malware",      count=256, color="#a78bfa"),
            ThreatCategory(name="SQL Injection",count=178, color="#60a5fa"),
            ThreatCategory(name="Other",        count=389, color="#6b7280"),
        ],
        org_activity=[
            OrgActivityItem(org_id="org-alpha",   name="Organization Alpha",   status="active",   current_round=12, last_update="2026-08-31T11:24:12Z"),
            OrgActivityItem(org_id="org-beta",    name="Organization Beta",    status="active",   current_round=12, last_update="2026-08-31T11:19:44Z"),
            OrgActivityItem(org_id="org-gamma",   name="Organization Gamma",   status="active",   current_round=12, last_update="2026-08-31T11:24:01Z"),
            OrgActivityItem(org_id="org-delta",   name="Organization Delta",   status="active",   current_round=12, last_update="2026-08-31T11:05:38Z"),
            OrgActivityItem(org_id="org-epsilon", name="Organization Epsilon", status="offline",  current_round=11, last_update="2026-08-31T09:48:22Z"),
        ],
        recent_threats=[
            RecentThreat(id="td-001", timestamp="2026-08-31T11:24:12Z", organization="Organization Alpha", threat_type="DoS/DDoS",      severity="critical", confidence=97.3, status="blocked",       model_version="v12.0"),
            RecentThreat(id="td-002", timestamp="2026-08-31T11:21:45Z", organization="Organization Gamma", threat_type="Brute Force",   severity="high",     confidence=94.1, status="detected",      model_version="v12.0"),
            RecentThreat(id="td-003", timestamp="2026-08-31T11:18:33Z", organization="Organization Beta",  threat_type="Malware",       severity="high",     confidence=91.8, status="investigating",  model_version="v12.0"),
            RecentThreat(id="td-004", timestamp="2026-08-31T11:15:07Z", organization="Organization Alpha", threat_type="Port Scan",     severity="medium",   confidence=88.5, status="blocked",       model_version="v12.0"),
            RecentThreat(id="td-005", timestamp="2026-08-31T11:10:52Z", organization="Organization Delta", threat_type="Data Exfil",    severity="critical", confidence=96.2, status="detected",      model_version="v11.0"),
        ],
        system_components=[
            SystemComponent(name="FastAPI Server",       status="healthy",  detail="Running — development mode"),
            SystemComponent(name="SQLite Database",      status="healthy",  detail="Connected"),
            SystemComponent(name="Flower FL Server",     status="unknown",  detail="Not yet integrated — Phase 10+"),
            SystemComponent(name="PyTorch ML Pipeline",  status="unknown",  detail="Not yet integrated — Phase 10+"),
            SystemComponent(name="Org Client 1 (Alpha)", status="healthy",  detail="Simulated — demo data"),
            SystemComponent(name="Org Client 2 (Beta)",  status="healthy",  detail="Simulated — demo data"),
        ],
    )


# ─────────────────────────────────────────────────────────────
# Organizations
# ─────────────────────────────────────────────────────────────

def get_organizations() -> OrganizationsResponse:
    orgs = [
        Organization(
            org_id="org-alpha", name="Organization Alpha", status="active",
            dataset_size=45000, local_model_status="trained", local_model_accuracy=88.2,
            current_round=12, last_update="2026-08-31T11:24:12Z",
            participation_rate=1.0,
            data_distribution=[
                DataSlice(label="DoS/DDoS",    value=38.0, color="#f87171"),
                DataSlice(label="Brute Force", value=22.0, color="#fb923c"),
                DataSlice(label="Port Scan",   value=18.0, color="#fbbf24"),
                DataSlice(label="Malware",     value=12.0, color="#a78bfa"),
                DataSlice(label="Normal",      value=10.0, color="#6b7280"),
            ],
            recent_rounds=[
                OrgTrainingRound(round=12, status="completed", accuracy=88.2, duration_s=42),
                OrgTrainingRound(round=11, status="completed", accuracy=87.9, duration_s=38),
                OrgTrainingRound(round=10, status="completed", accuracy=87.5, duration_s=40),
            ],
        ),
        Organization(
            org_id="org-beta", name="Organization Beta", status="active",
            dataset_size=32000, local_model_status="trained", local_model_accuracy=83.7,
            current_round=12, last_update="2026-08-31T11:19:44Z",
            participation_rate=1.0,
            data_distribution=[
                DataSlice(label="Normal",      value=45.0, color="#6b7280"),
                DataSlice(label="Port Scan",   value=25.0, color="#fbbf24"),
                DataSlice(label="DoS/DDoS",    value=15.0, color="#f87171"),
                DataSlice(label="Brute Force", value=10.0, color="#fb923c"),
                DataSlice(label="Malware",     value=5.0,  color="#a78bfa"),
            ],
            recent_rounds=[
                OrgTrainingRound(round=12, status="completed", accuracy=83.7, duration_s=36),
                OrgTrainingRound(round=11, status="completed", accuracy=83.1, duration_s=34),
                OrgTrainingRound(round=10, status="completed", accuracy=82.8, duration_s=35),
            ],
        ),
        Organization(
            org_id="org-gamma", name="Organization Gamma", status="active",
            dataset_size=28000, local_model_status="trained", local_model_accuracy=85.9,
            current_round=12, last_update="2026-08-31T11:24:01Z",
            participation_rate=1.0,
            data_distribution=[
                DataSlice(label="Brute Force",  value=40.0, color="#fb923c"),
                DataSlice(label="Malware",      value=28.0, color="#a78bfa"),
                DataSlice(label="DoS/DDoS",     value=15.0, color="#f87171"),
                DataSlice(label="Normal",       value=12.0, color="#6b7280"),
                DataSlice(label="Port Scan",    value=5.0,  color="#fbbf24"),
            ],
            recent_rounds=[
                OrgTrainingRound(round=12, status="completed", accuracy=85.9, duration_s=33),
                OrgTrainingRound(round=11, status="completed", accuracy=85.4, duration_s=31),
                OrgTrainingRound(round=10, status="completed", accuracy=85.0, duration_s=32),
            ],
        ),
        Organization(
            org_id="org-delta", name="Organization Delta", status="active",
            dataset_size=18000, local_model_status="trained", local_model_accuracy=81.3,
            current_round=12, last_update="2026-08-31T11:05:38Z",
            participation_rate=0.92,
            data_distribution=[
                DataSlice(label="Normal",      value=50.0, color="#6b7280"),
                DataSlice(label="Malware",     value=30.0, color="#a78bfa"),
                DataSlice(label="DoS/DDoS",    value=12.0, color="#f87171"),
                DataSlice(label="Brute Force", value=5.0,  color="#fb923c"),
                DataSlice(label="Port Scan",   value=3.0,  color="#fbbf24"),
            ],
            recent_rounds=[
                OrgTrainingRound(round=12, status="completed", accuracy=81.3, duration_s=44),
                OrgTrainingRound(round=11, status="completed", accuracy=80.9, duration_s=41),
                OrgTrainingRound(round=10, status="completed", accuracy=80.4, duration_s=43),
            ],
        ),
        Organization(
            org_id="org-epsilon", name="Organization Epsilon", status="offline",
            dataset_size=12000, local_model_status="pending", local_model_accuracy=None,
            current_round=11, last_update="2026-08-31T09:48:22Z",
            participation_rate=0.83,
            data_distribution=[
                DataSlice(label="Port Scan",   value=55.0, color="#fbbf24"),
                DataSlice(label="Normal",      value=30.0, color="#6b7280"),
                DataSlice(label="DoS/DDoS",    value=10.0, color="#f87171"),
                DataSlice(label="Brute Force", value=5.0,  color="#fb923c"),
            ],
            recent_rounds=[
                OrgTrainingRound(round=11, status="completed", accuracy=79.2, duration_s=51),
                OrgTrainingRound(round=10, status="completed", accuracy=78.8, duration_s=48),
                OrgTrainingRound(round=12, status="skipped",   accuracy=None,  duration_s=None),
            ],
        ),
    ]
    active  = sum(1 for o in orgs if o.status == "active")
    training= sum(1 for o in orgs if o.status == "training")
    idle    = sum(1 for o in orgs if o.status == "idle")
    offline = sum(1 for o in orgs if o.status == "offline")
    return OrganizationsResponse(
        summary=OrganizationSummary(total=len(orgs), active=active, training=training, idle=idle, offline=offline),
        organizations=orgs,
    )


# ─────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────

def get_training() -> TrainingResponse:
    return TrainingResponse(
        summary=TrainingSummary(
            current_round=12, total_rounds=12,
            global_model_version="v12.0",
            training_status="completed",
            global_accuracy=94.7, global_f1=92.3, global_loss=0.19,
            avg_round_duration_s=38, aggregation_strategy="FedAvg",
            active_clients=4, total_clients=5,
        ),
        client_statuses=[
            ClientStatus(org_id="org-alpha",   org_name="Organization Alpha",   connection_status="active",  training_status="completed", local_accuracy=88.2, local_loss=0.34, samples=45000, update_size_mb=2.4, duration_s=42),
            ClientStatus(org_id="org-beta",    org_name="Organization Beta",    connection_status="active",  training_status="completed", local_accuracy=83.7, local_loss=0.41, samples=32000, update_size_mb=2.4, duration_s=36),
            ClientStatus(org_id="org-gamma",   org_name="Organization Gamma",   connection_status="active",  training_status="completed", local_accuracy=85.9, local_loss=0.38, samples=28000, update_size_mb=2.4, duration_s=33),
            ClientStatus(org_id="org-delta",   org_name="Organization Delta",   connection_status="active",  training_status="completed", local_accuracy=81.3, local_loss=0.44, samples=18000, update_size_mb=2.4, duration_s=44),
            ClientStatus(org_id="org-epsilon", org_name="Organization Epsilon", connection_status="offline", training_status="skipped",   local_accuracy=None, local_loss=None, samples=None,  update_size_mb=None, duration_s=None),
        ],
        participation=[
            ParticipationPoint(round=r, participating=p, total=5)
            for r, p in [(1,5),(2,5),(3,5),(4,5),(5,5),(6,5),(7,5),(8,5),(9,5),(10,5),(11,4),(12,4)]
        ],
    )


def get_training_rounds() -> TrainingRoundsResponse:
    raw = [
        (1, 68.2, 0.89, 62.1, 41, "v1.0",  "2026-08-31T07:00:00Z", "2026-08-31T07:00:41Z"),
        (2, 73.5, 0.76, 69.8, 38, "v2.0",  "2026-08-31T07:01:00Z", "2026-08-31T07:01:38Z"),
        (3, 78.1, 0.64, 74.5, 36, "v3.0",  "2026-08-31T07:02:00Z", "2026-08-31T07:02:36Z"),
        (4, 81.4, 0.54, 78.2, 39, "v4.0",  "2026-08-31T07:03:00Z", "2026-08-31T07:03:39Z"),
        (5, 84.6, 0.46, 81.9, 37, "v5.0",  "2026-08-31T07:04:00Z", "2026-08-31T07:04:37Z"),
        (6, 87.0, 0.40, 84.3, 35, "v6.0",  "2026-08-31T07:05:00Z", "2026-08-31T07:05:35Z"),
        (7, 89.2, 0.34, 86.8, 40, "v7.0",  "2026-08-31T07:06:00Z", "2026-08-31T07:06:40Z"),
        (8, 90.8, 0.29, 88.6, 38, "v8.0",  "2026-08-31T07:07:00Z", "2026-08-31T07:07:38Z"),
        (9, 92.1, 0.25, 89.9, 36, "v9.0",  "2026-08-31T07:08:00Z", "2026-08-31T07:08:36Z"),
        (10,93.3, 0.22, 91.0, 39, "v10.0", "2026-08-31T07:09:00Z", "2026-08-31T07:09:39Z"),
        (11,94.1, 0.20, 91.8, 37, "v11.0", "2026-08-31T07:10:00Z", "2026-08-31T07:10:37Z"),
        (12,94.7, 0.19, 92.3, 42, "v12.0", "2026-08-31T07:11:00Z", "2026-08-31T07:11:42Z"),
    ]
    rounds = [
        TrainingRound(
            round=r, status="completed",
            participating_clients=5 if r <= 10 else 4, total_clients=5,
            accuracy=acc, loss=loss, f1=f1, duration_s=dur,
            model_version=ver, started_at=sa, completed_at=ca,
        )
        for r, acc, loss, f1, dur, ver, sa, ca in raw
    ]
    return TrainingRoundsResponse(rounds=list(reversed(rounds)), total=len(rounds))


# ─────────────────────────────────────────────────────────────
# Threats
# ─────────────────────────────────────────────────────────────

_THREATS_RAW: list[dict] = [
    {"id":"td-001","timestamp":"2026-08-31T11:24:12Z","organization":"Organization Alpha","organization_id":"org-alpha","threat_type":"DoS/DDoS","severity":"critical","confidence":97.3,"status":"blocked","model_version":"v12.0","source_ip":"10.0.1.45","destination_ip":"192.168.1.10","protocol":"TCP","port":80,"description":"High-volume SYN flood targeting web server. Traffic matches distributed DoS signature.","raw_features":{"flow_duration":12450,"fwd_packets":98432,"bwd_packets":124,"flow_bytes_per_s":8934210},"detection_method":"federated"},
    {"id":"td-002","timestamp":"2026-08-31T11:21:45Z","organization":"Organization Gamma","organization_id":"org-gamma","threat_type":"Brute Force","severity":"high","confidence":94.1,"status":"detected","model_version":"v12.0","source_ip":"10.0.3.112","destination_ip":"192.168.3.5","protocol":"TCP","port":22,"description":"Repeated SSH authentication failures. 847 attempts in 5 minutes.","raw_features":{"flow_duration":302000,"fwd_packets":1694,"bwd_packets":1694,"flow_bytes_per_s":5620},"detection_method":"federated"},
    {"id":"td-003","timestamp":"2026-08-31T11:18:33Z","organization":"Organization Beta","organization_id":"org-beta","threat_type":"Malware","severity":"high","confidence":91.8,"status":"investigating","model_version":"v12.0","source_ip":"10.0.2.78","destination_ip":"203.0.113.42","protocol":"TCP","port":443,"description":"Outbound C2 beacon pattern. Periodic HTTPS connections to known malicious infrastructure.","raw_features":{"flow_duration":86400000,"fwd_packets":288,"bwd_packets":288,"flow_bytes_per_s":42},"detection_method":"federated"},
    {"id":"td-004","timestamp":"2026-08-31T11:15:07Z","organization":"Organization Alpha","organization_id":"org-alpha","threat_type":"Port Scan","severity":"medium","confidence":88.5,"status":"blocked","model_version":"v12.0","source_ip":"10.0.1.203","destination_ip":"192.168.1.0/24","protocol":"TCP","port":0,"description":"Horizontal port scan across subnet.","raw_features":{"flow_duration":30000,"fwd_packets":260096,"bwd_packets":3841,"flow_bytes_per_s":346800},"detection_method":"local"},
    {"id":"td-005","timestamp":"2026-08-31T11:10:52Z","organization":"Organization Delta","organization_id":"org-delta","threat_type":"Data Exfiltration","severity":"critical","confidence":96.2,"status":"detected","model_version":"v11.0","source_ip":"10.0.4.56","destination_ip":"198.51.100.88","protocol":"TCP","port":443,"description":"2.3 GB encrypted transfer to external host outside business hours.","raw_features":{"flow_duration":2700000,"fwd_packets":1632000,"bwd_packets":48000,"flow_bytes_per_s":852000},"detection_method":"federated"},
]


def get_threats(
    organization: str | None = None,
    threat_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> ThreatsResponse:
    threats = [ThreatDetection(**t) for t in _THREATS_RAW]

    # Apply filters
    if organization:
        threats = [t for t in threats if t.organization == organization]
    if threat_type:
        threats = [t for t in threats if t.threat_type == threat_type]
    if severity:
        threats = [t for t in threats if t.severity == severity]
    if status:
        threats = [t for t in threats if t.status == status]
    if search:
        s = search.lower()
        threats = [t for t in threats if s in t.threat_type.lower() or s in t.organization.lower() or s in t.source_ip]

    summary = ThreatSummary(
        total=1847, critical=187, high=493, medium=641, low=526,
        blocked=1204, investigating=89, avg_confidence=91.4,
    )
    distribution = [
        ThreatTypeCount(type="DoS/DDoS",           count=423, color="#f87171"),
        ThreatTypeCount(type="Brute Force",         count=312, color="#fb923c"),
        ThreatTypeCount(type="Port Scan",           count=289, color="#fbbf24"),
        ThreatTypeCount(type="Malware",             count=256, color="#a78bfa"),
        ThreatTypeCount(type="SQL Injection",       count=178, color="#60a5fa"),
        ThreatTypeCount(type="XSS",                count=149, color="#22d3ee"),
        ThreatTypeCount(type="Data Exfiltration",  count=132, color="#34d399"),
        ThreatTypeCount(type="Privilege Escalation",count=108, color="#f472b6"),
    ]
    timeline = [
        ThreatTimelinePoint(hour=h, critical=c, high=hi, medium=m, low=lo)
        for h, c, hi, m, lo in [
            ("00:00",2,5,8,6),("01:00",1,3,6,5),("06:00",2,4,7,5),
            ("09:00",7,12,15,10),("12:00",4,8,11,7),("15:00",9,15,19,13),
            ("18:00",4,8,11,8),("21:00",2,4,6,5),("23:00",1,3,4,3),
        ]
    ]
    start = (page - 1) * page_size
    paged = threats[start: start + page_size]
    return ThreatsResponse(
        summary=summary, detections=paged, distribution=distribution,
        timeline=timeline, total=len(threats), page=page, page_size=page_size,
    )


# ─────────────────────────────────────────────────────────────
# Performance
# ─────────────────────────────────────────────────────────────

def get_performance() -> PerformanceResponse:
    cm_labels = ["DoS", "Brute Force", "Port Scan", "Malware", "Normal"]
    local_diag  = [841, 758, 779, 741, 864]
    fed_diag    = [891, 823, 836, 807, 934]

    def build_cm(labels: list[str], diag: list[int], off_val_fn) -> list[ConfusionCell]:
        cells = []
        for i, actual in enumerate(labels):
            for j, predicted in enumerate(labels):
                if i == j:
                    cells.append(ConfusionCell(actual=actual, predicted=predicted, value=diag[i]))
                else:
                    cells.append(ConfusionCell(actual=actual, predicted=predicted, value=off_val_fn(i, j)))
        return cells

    return PerformanceResponse(
        summary=PerformanceSummary(
            federated_accuracy=94.7, local_avg_accuracy=84.7, accuracy_gain=10.0,
            federated_f1=92.3,       local_avg_f1=81.5,       f1_gain=10.8,
            federated_fpr=3.2,        local_avg_fpr=8.6,       fpr_reduction=5.4,
        ),
        metric_comparisons=[
            MetricComparison(label="Accuracy",            local=84.7, federated=94.7, unit="%",     higher_is_better=True),
            MetricComparison(label="Precision",           local=82.1, federated=92.8, unit="%",     higher_is_better=True),
            MetricComparison(label="Recall",              local=80.4, federated=91.9, unit="%",     higher_is_better=True),
            MetricComparison(label="F1 Score",            local=81.5, federated=92.3, unit="%",     higher_is_better=True),
            MetricComparison(label="False-Positive Rate", local=8.6,  federated=3.2,  unit="%",     higher_is_better=False),
            MetricComparison(label="Attack Detection",    local=79.2, federated=93.1, unit="%",     higher_is_better=True),
            MetricComparison(label="Non-IID Robustness",  local=61.3, federated=87.4, unit="score", higher_is_better=True),
        ],
        org_performance=[
            OrgPerformanceRow(org_id="org-alpha",   org_name="Organization Alpha",   local_accuracy=88.2, local_f1=86.3, local_precision=87.1, local_recall=85.6, federated_accuracy=94.7, federated_f1=92.3, gain=6.5),
            OrgPerformanceRow(org_id="org-beta",    org_name="Organization Beta",    local_accuracy=83.7, local_f1=81.9, local_precision=82.4, local_recall=81.4, federated_accuracy=94.7, federated_f1=92.3, gain=11.0),
            OrgPerformanceRow(org_id="org-gamma",   org_name="Organization Gamma",   local_accuracy=85.9, local_f1=83.7, local_precision=84.2, local_recall=83.2, federated_accuracy=94.7, federated_f1=92.3, gain=8.8),
            OrgPerformanceRow(org_id="org-delta",   org_name="Organization Delta",   local_accuracy=81.3, local_f1=79.4, local_precision=80.1, local_recall=78.7, federated_accuracy=94.7, federated_f1=92.3, gain=13.4),
            OrgPerformanceRow(org_id="org-epsilon", org_name="Organization Epsilon", local_accuracy=79.2, local_f1=77.1, local_precision=77.8, local_recall=76.4, federated_accuracy=94.7, federated_f1=92.3, gain=15.5),
        ],
        non_iid_results=[
            NonIIDResult(scenario="Uniform (IID)",        alpha=100.0, local_avg_accuracy=88.4, federated_accuracy=94.7, robustness_score=96),
            NonIIDResult(scenario="Mild Skew (α=1.0)",   alpha=1.0,   local_avg_accuracy=85.9, federated_accuracy=93.8, robustness_score=89),
            NonIIDResult(scenario="Moderate (α=0.5)",    alpha=0.5,   local_avg_accuracy=84.7, federated_accuracy=92.4, robustness_score=83),
            NonIIDResult(scenario="Heavy Skew (α=0.1)", alpha=0.1,   local_avg_accuracy=78.3, federated_accuracy=89.1, robustness_score=74),
            NonIIDResult(scenario="Extreme (α=0.01)",   alpha=0.01,  local_avg_accuracy=68.1, federated_accuracy=84.6, robustness_score=61),
        ],
        round_metrics=[
            PerfRoundMetric(round=r, local_avg_accuracy=la, federated_accuracy=fa, local_avg_f1=lf, federated_f1=ff)
            for r, la, fa, lf, ff in [
                (1,64.3,68.2,61.1,62.1),(2,68.7,73.5,65.8,69.8),(3,72.4,78.1,69.7,74.5),
                (4,75.1,81.4,72.8,78.2),(5,77.8,84.6,75.3,81.9),(6,79.6,87.0,77.4,84.3),
                (7,81.2,89.2,79.0,86.8),(8,82.4,90.8,80.2,88.6),(9,83.3,92.1,81.1,89.9),
                (10,84.0,93.3,81.8,91.0),(11,84.4,94.1,82.1,91.8),(12,84.7,94.7,81.5,92.3),
            ]
        ],
        collaboration_benefit=[
            CollaborationBenefit(metric="Accuracy",         local_avg=84.7, federated=94.7, improvement=10.0, improvement_pct=11.8),
            CollaborationBenefit(metric="F1 Score",         local_avg=81.5, federated=92.3, improvement=10.8, improvement_pct=13.3),
            CollaborationBenefit(metric="Recall",           local_avg=80.4, federated=91.9, improvement=11.5, improvement_pct=14.3),
            CollaborationBenefit(metric="Attack Detection", local_avg=79.2, federated=93.1, improvement=13.9, improvement_pct=17.6),
            CollaborationBenefit(metric="FPR Reduction",    local_avg=8.6,  federated=3.2,  improvement=5.4,  improvement_pct=62.8),
        ],
        local_confusion_matrix=ConfusionMatrix(
            labels=cm_labels, model_type="local",
            cells=build_cm(cm_labels, local_diag, lambda i, j: [24,18,9,12,31,22,14,19,15,28,11,21,10,18,14,41,29,22,18,16][i*4+j if i*4+j < 20 else 0]),
        ),
        federated_confusion_matrix=ConfusionMatrix(
            labels=cm_labels, model_type="federated",
            cells=build_cm(cm_labels, fed_diag, lambda i, j: [8,4,2,3,7,8,3,3,5,6,2,5,3,5,4,5,6,4,3,2][i*4+j if i*4+j < 20 else 0]),
        ),
    )


# ─────────────────────────────────────────────────────────────
# Privacy
# ─────────────────────────────────────────────────────────────

def get_privacy() -> PrivacyResponse:
    return PrivacyResponse(
        summary=PrivacySummary(
            raw_data_shared=False, model_updates_only=True,
            privacy_mechanisms_implemented=1, privacy_mechanisms_planned=3,
            security_events_last_24h=4, unauthorized_attempts_blocked=2,
        ),
        properties=[
            PrivacyProperty(id="data-locality",     label="Raw Data Locality",    category="data_locality", description="Organization raw data never leaves local environment.", status="enforced", detail="Enforced by FL architecture — only weight updates transmitted.", planned=False),
            PrivacyProperty(id="model-updates-only",label="Model Updates Only",   category="model_update",  description="Only weight updates are sent to server.", status="enforced", detail="Flower client sends parameter deltas only.", planned=False),
            PrivacyProperty(id="differential-privacy",label="Differential Privacy",category="model_update", description="Noise added to updates for formal privacy guarantees.", status="planned", detail="NOT YET IMPLEMENTED. Planned: Gaussian mechanism via Opacus.", planned=True),
            PrivacyProperty(id="secure-aggregation", label="Secure Aggregation",  category="aggregation",   description="Server cannot see individual client updates.", status="planned", detail="NOT YET IMPLEMENTED. Planned: Flower SecAgg+ strategy.", planned=True),
        ],
        org_update_statuses=[
            OrgUpdateStatus(org_id="org-alpha",   org_name="Organization Alpha",   round=12, update_status="submitted", update_size="2.4 MB", submitted_at="2026-08-31T11:22:10Z", validation_passed=True,  notes="Update accepted."),
            OrgUpdateStatus(org_id="org-beta",    org_name="Organization Beta",    round=12, update_status="submitted", update_size="2.4 MB", submitted_at="2026-08-31T11:19:44Z", validation_passed=True,  notes="Update accepted."),
            OrgUpdateStatus(org_id="org-gamma",   org_name="Organization Gamma",   round=12, update_status="submitted", update_size="2.4 MB", submitted_at="2026-08-31T11:24:01Z", validation_passed=True,  notes="Update accepted."),
            OrgUpdateStatus(org_id="org-delta",   org_name="Organization Delta",   round=12, update_status="submitted", update_size="2.4 MB", submitted_at="2026-08-31T11:05:38Z", validation_passed=True,  notes="Update accepted."),
            OrgUpdateStatus(org_id="org-epsilon", org_name="Organization Epsilon", round=12, update_status="not_sent",  update_size=None,     submitted_at=None,                    validation_passed=None,  notes="Client offline — did not participate."),
        ],
        security_events=[
            SecurityEvent(id="sec-001", timestamp="2026-08-31T11:30:00Z", organization=None,                   event="Unknown client connection attempt",    category="Access Control",    severity="warning",  status="resolved",   detail="Unregistered client refused."),
            SecurityEvent(id="sec-002", timestamp="2026-08-31T11:15:22Z", organization="Organization Epsilon", event="Client disconnected mid-round",        category="Availability",      severity="info",     status="resolved",   detail="Epsilon offline during round 12."),
            SecurityEvent(id="sec-003", timestamp="2026-08-31T10:44:18Z", organization=None,                   event="Large model update rejected",          category="Update Validation", severity="warning",  status="resolved",   detail="Norm 12.4× expected — discarded."),
            SecurityEvent(id="sec-004", timestamp="2026-08-30T22:11:44Z", organization=None,                   event="Repeated connection probe",            category="Access Control",    severity="critical", status="monitoring", detail="14 probes from 203.0.113.77."),
        ],
    )


# ─────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────

def get_testing() -> TestingResponse:
    cases = [
        TestCase(id="TC-101", name="Federated Training Convergence",    category="AC-1 Representative Operation", description="Verify global model converges to ≥90% accuracy over 12 rounds.", expected_result="Accuracy ≥ 90% at round 12", actual_result="Mock: 94.7% (DEMO — not on live system)", status="warning", execution_state="mock_run", timestamp="2026-08-31T11:30:00Z", notes="Must re-run once Flower pipeline integrated."),
        TestCase(id="TC-102", name="Multi-Organization Participation",  category="AC-1 Representative Operation", description="All orgs join and submit updates in one round.", expected_result="≥4 of 5 orgs complete training", actual_result=None, status="pending", execution_state="not_run", timestamp=None, notes="Requires live Flower server."),
        TestCase(id="TC-103", name="Threat Detection Accuracy",         category="AC-1 Representative Operation", description="Evaluate global model on held-out test set.", expected_result="Accuracy ≥90%, F1 ≥88%", actual_result=None, status="pending", execution_state="not_run", timestamp=None, notes="Requires real dataset split."),
        TestCase(id="TC-201", name="Non-IID Degradation",              category="AC-2 Boundary & Failure",       description="Measure degradation as Dirichlet α → 0.", expected_result="Federated ≥80% at α=0.1", actual_result="Mock: 89.1% at α=0.1 (DEMO)", status="warning", execution_state="mock_run", timestamp="2026-08-31T10:00:00Z", notes="Simulated with mock distribution."),
        TestCase(id="TC-202", name="Single Organization Dropout",       category="AC-2 Boundary & Failure",       description="One org offline mid-round — training continues.", expected_result="Round completes with ≥3 clients", actual_result=None, status="pending", execution_state="not_run", timestamp=None, notes="Requires live Flower with failure injection."),
        TestCase(id="TC-204", name="Oversized Update Rejection",        category="AC-2 Boundary & Failure",       description="Submit high-norm update — verify rejection.", expected_result="Update rejected; round continues", actual_result="Mock: Rejected (norm 12.4×) — sec event only", status="warning", execution_state="mock_run", timestamp="2026-08-31T10:44:18Z", notes="Formal test requires norm-threshold config."),
        TestCase(id="TC-301", name="Privacy Boundary — Data Locality",  category="AC-3 Independent Acceptance",   description="Network capture confirms no raw data transmitted.", expected_result="Only weight tensors in network capture", actual_result="Code inspection passed; network test NOT RUN", status="warning", execution_state="mock_run", timestamp="2026-09-01T09:00:00Z", notes="Full network-level verification pending."),
        TestCase(id="TC-302", name="Unauthorized Update Rejection",     category="AC-3 Independent Acceptance",   description="Unregistered client attempt — verify refused.", expected_result="Connection refused; no update accepted", actual_result="Mock: sec-001 event (DEMO — not formal test)", status="warning", execution_state="mock_run", timestamp="2026-08-31T11:30:00Z", notes="Formal pen test required with real auth."),
        TestCase(id="TC-303", name="Invalid Update Handling",           category="AC-3 Independent Acceptance",   description="Wrong-shape tensor — server handles without crash.", expected_result="Rejected; round continues", actual_result=None, status="pending", execution_state="not_run", timestamp=None, notes="Requires live Flower server."),
        TestCase(id="TC-401", name="Model Size Constraint",            category="AC-4 Frozen Resource Envelope", description="Global model ≤50 MB on disk.", expected_result="Model ≤ 50 MB", actual_result=None, status="pending", execution_state="not_run", timestamp=None, notes="Measurable once architecture frozen."),
        TestCase(id="TC-402", name="Inference Latency",                category="AC-4 Frozen Resource Envelope", description="Single-sample CPU inference ≤100 ms.", expected_result="Latency ≤ 100 ms", actual_result=None, status="pending", execution_state="not_run", timestamp=None, notes="Benchmark with torch.inference_mode()."),
        TestCase(id="TC-403", name="Training Round Time Budget",       category="AC-4 Frozen Resource Envelope", description="Avg round ≤120s across 5 clients.", expected_result="Avg duration ≤ 120s", actual_result="Mock: ~38s avg (DEMO)", status="warning", execution_state="mock_run", timestamp="2026-08-31T11:00:00Z", notes="Mock timing only — verify on target hardware."),
    ]
    mock_run  = sum(1 for c in cases if c.execution_state == "mock_run")
    not_run   = sum(1 for c in cases if c.execution_state == "not_run")
    executed  = sum(1 for c in cases if c.execution_state == "executed")
    passed    = sum(1 for c in cases if c.status == "pass")
    failed    = sum(1 for c in cases if c.status == "fail")
    warnings  = sum(1 for c in cases if c.status == "warning")
    pending   = sum(1 for c in cases if c.status == "pending")
    ran       = mock_run + executed
    return TestingResponse(
        summary=TestSuiteSummary(
            total=len(cases), executed=executed, mock_run=mock_run, not_run=not_run,
            passed=passed, failed=failed, warnings=warnings, pending=pending,
            pass_rate=round(passed / ran * 100, 1) if ran else 0.0,
        ),
        test_cases=cases,
        acceptance_criteria=[
            AcceptanceCriterion(code="AC-1", title="Representative Operation",    description="Primary function under normal conditions.",    tests=["TC-101","TC-102","TC-103"], passing_threshold=90),
            AcceptanceCriterion(code="AC-2", title="Boundary and Failure",         description="Edge cases, failures, invalid inputs.",        tests=["TC-201","TC-202","TC-204"], passing_threshold=80),
            AcceptanceCriterion(code="AC-3", title="Independent Acceptance",       description="Independently verifiable evidence.",           tests=["TC-301","TC-302","TC-303"], passing_threshold=100),
            AcceptanceCriterion(code="AC-4", title="Frozen Resource Envelope",     description="System within defined resource limits.",       tests=["TC-401","TC-402","TC-403"], passing_threshold=100),
        ],
    )


# ─────────────────────────────────────────────────────────────
# System
# ─────────────────────────────────────────────────────────────

def get_system(db_ok: bool = True) -> SystemResponse:
    uptime = int(time.time() - _START_TIME)
    from app.core.config import get_settings
    cfg = get_settings()
    now = datetime.now(timezone.utc).isoformat()
    return SystemResponse(
        status="healthy",
        version=cfg.app_version,
        environment=cfg.environment,
        uptime_s=uptime,
        fl_connected=False,
        ml_connected=False,
        db_connected=db_ok,
        components=[
            ComponentHealth(name="FastAPI Server",      status="healthy",  detail=f"Running {cfg.environment} mode", last_checked=now),
            ComponentHealth(name="SQLite Database",     status="healthy" if db_ok else "offline", detail="Connected via aiosqlite" if db_ok else "Connection failed", last_checked=now),
            ComponentHealth(name="Flower FL Server",    status="unknown",  detail="Not yet integrated — planned Phase 10+", last_checked=now),
            ComponentHealth(name="PyTorch ML Pipeline", status="unknown",  detail="Not yet integrated — planned Phase 10+", last_checked=now),
        ],
    )
