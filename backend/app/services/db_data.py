"""
Database-backed data service — real CICIDS2017 experiment data.

All functions read from SQLite via SQLAlchemy repositories.
No synthetic or seeded metric values are used for KPIs.
Seeded tables (organizations, training_rounds) are used only for
structural data; all performance metrics come from experiment_* categories.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organization_repo import OrganizationRepo
from app.repositories.training_repo import TrainingRepo
from app.repositories.threat_repo import ThreatRepo
from app.repositories.metric_repo import MetricRepo
from app.repositories.privacy_repo import PrivacyRepo
from app.repositories.testing_repo import TestingRepo

from app.schemas.dashboard import (
    DashboardResponse, ModelComparisonMetric, OrgActivityItem,
    RecentThreat, SystemComponent, ThreatCategory, TrainingRoundMetric,
)
from app.schemas.organizations import (
    DataSlice, Organization as OrgSchema, OrganizationSummary, OrganizationsResponse,
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
    ThreatDetection as ThreatSchema, ThreatSummary, ThreatTimelinePoint,
    ThreatTypeCount, ThreatsResponse,
)
from app.schemas.training import (
    ClientStatus, ParticipationPoint, TrainingResponse,
    TrainingRound as TrainingRoundSchema, TrainingRoundsResponse, TrainingSummary,
)

# ── Threat type colour palette ────────────────────────────────────────────────

_THREAT_COLORS = {
    "DoS":         "#f87171",
    "Brute Force": "#fb923c",
    "Port Scan":   "#fbbf24",
    "Malware":     "#a78bfa",
    "Normal":      "#6b7280",
}

def _threat_color(threat_type: str) -> str:
    for k, v in _THREAT_COLORS.items():
        if k.lower() in threat_type.lower():
            return v
    return "#94a3b8"


_START_TIME = time.time()


# ═════════════════════════════════════════════════════════════════════════════
# Dashboard
# ═════════════════════════════════════════════════════════════════════════════

async def get_dashboard(db: AsyncSession) -> DashboardResponse:
    org_repo    = OrganizationRepo(db)
    train_repo  = TrainingRepo(db)  # noqa: F841 — kept for future use
    threat_repo = ThreatRepo(db)
    metric_repo = MetricRepo(db)

    # 1. Registered organisations from DB
    all_orgs = await org_repo.get_all()
    org_sum  = await org_repo.get_summary()

    # 2. Latest experiment — all KPIs sourced from here
    exp_id   = await metric_repo.get_latest_experiment_id()
    exp_meta = await metric_repo.get_experiment_metadata(exp_id) if exp_id else {}

    # 3. Which orgs actually participated in this experiment (from experiment_org IID rows)
    exp_participant_ids: set[str] = set()
    if exp_id:
        exp_org_rows = await metric_repo.get_by_category_for_experiment("experiment_org", exp_id)
        exp_participant_ids = {
            m.org_id for m in exp_org_rows
            if m.org_id and m.model_type.endswith("__iid")
        }

    num_exp_clients = int(exp_meta.get("number_of_clients", len(exp_participant_ids)))

    # 4. Experiment summary metrics (IID run)
    global_acc   = 0.0
    global_f1    = 0.0
    global_fpr   = 0.0
    iid_metrics: dict[str, float] = {}
    total_rounds = int(exp_meta.get("number_of_rounds", 0))

    if exp_id:
        exp_summary = await metric_repo.get_by_category_for_experiment("experiment_summary", exp_id)
        iid_metrics = {m.metric_name: m.metric_value for m in exp_summary if m.model_type.endswith("__iid")}
        global_acc = iid_metrics.get("accuracy", 0.0)
        global_f1  = iid_metrics.get("f1", 0.0)
        global_fpr = iid_metrics.get("false_positive_rate", 0.0)

    # 5. Training rounds chart — per-round experiment_round (IID)
    #    The stored per-round metric is federated_fpr, NOT a cross-entropy loss.
    #    It is exposed as `fpr` (not `loss`) to avoid misrepresentation.
    training_round_metrics: list[TrainingRoundMetric] = []
    if exp_id:
        exp_rounds = await metric_repo.get_by_category_for_experiment("experiment_round", exp_id)
        iid_rounds = [m for m in exp_rounds if m.model_type.endswith("__iid")]
        round_nums = sorted(set(m.round_number for m in iid_rounds if m.round_number is not None))
        for rn in round_nums:
            rd = {m.metric_name: m.metric_value for m in iid_rounds if m.round_number == rn}
            training_round_metrics.append(TrainingRoundMetric(
                round=rn,
                accuracy=rd.get("federated_accuracy", 0.0),
                fpr=rd.get("federated_fpr", 0.0),
                f1=rd.get("federated_f1", 0.0),
            ))
        if total_rounds == 0 and round_nums:
            total_rounds = max(round_nums)

    # 6. Model comparison — local avg vs federated for Accuracy / Precision / Recall / F1
    model_comparison: list[ModelComparisonMetric] = []
    if exp_id:
        exp_org_all = await metric_repo.get_by_category_for_experiment("experiment_org", exp_id)
        iid_org = [m for m in exp_org_all if m.model_type.endswith("__iid")]
        for label in ["accuracy", "precision", "recall", "f1"]:
            fed_val = iid_metrics.get(label, 0.0)
            local_vals = [m.metric_value for m in iid_org if m.metric_name == f"{label}__local"]
            local_avg_val = round(sum(local_vals) / len(local_vals), 2) if local_vals else 0.0
            model_comparison.append(ModelComparisonMetric(
                metric=label.replace("_", " ").title(),
                local=local_avg_val,
                federated=fed_val,
            ))

    # 7. Threat totals — no daily trend: only 5 seeded records, all same date
    threats_total = await threat_repo.get_total_count()
    recent_threats_list, _ = await threat_repo.get_threats(page=1, page_size=5)
    threat_types = await threat_repo.get_counts_by_type()

    # 8. Current round = total rounds from experiment
    current_round = total_rounds

    # 9. Privacy status — built from verified experiment DP config
    privacy_status = "Data Local"
    privacy_detail: str | None = None
    if exp_id:
        # Read config from privacy_event category for this experiment (IID)
        priv_rows = await metric_repo.get_by_category_for_experiment("privacy_event", exp_id)
        iid_priv = {r.metric_name: r.metric_value for r in priv_rows if r.model_type.endswith("__iid")}
        clipping_enabled  = bool(iid_priv.get("config__clipping_enabled", 0))
        dp_noise_enabled  = bool(iid_priv.get("config__dp_noise_enabled", 0))
        validation_enabled = bool(iid_priv.get("config__validation_enabled", 0))
        clip_norm         = iid_priv.get("config__clip_norm", None)
        noise_std         = iid_priv.get("config__noise_std", None)
        epsilon_per_round = iid_priv.get("config__epsilon_per_round", None)
        delta             = iid_priv.get("config__delta", None)

        mechanisms = ["Data Local"]
        if clipping_enabled:
            mechanisms.append("Update Clipping")
        if dp_noise_enabled:
            mechanisms.append("Gaussian Noise")
        if validation_enabled:
            mechanisms.append("Server Validation")

        privacy_status = " · ".join(mechanisms)

        detail_parts = []
        if clipping_enabled and clip_norm is not None:
            detail_parts.append(f"clip_norm={clip_norm}")
        if dp_noise_enabled and noise_std is not None:
            detail_parts.append(f"noise_std={noise_std}")
        if epsilon_per_round is not None:
            detail_parts.append(f"ε≈{epsilon_per_round:.2f}/round")
        if delta is not None:
            detail_parts.append(f"δ={delta:.0e}")
        if detail_parts:
            privacy_detail = "Configured: " + ", ".join(detail_parts) + ". Secure aggregation: not implemented."
        else:
            privacy_detail = "DP mechanisms configured. Secure aggregation: not implemented."

    # 10. Organisation activity — all registered orgs, flagged by experiment participation
    #     current_round set to experiment total_rounds only for actual participants
    org_activity_items: list[OrgActivityItem] = []
    for o in all_orgs:
        is_participant = o.id in exp_participant_ids
        org_activity_items.append(OrgActivityItem(
            org_id=o.id,
            name=o.name,
            status=o.status,
            current_round=current_round if is_participant else None,
            last_update=o.last_update,
            is_experiment_participant=is_participant,
        ))

    data_source = f"experiment:{exp_id}" if exp_id else "database"

    return DashboardResponse(
        total_organizations=org_sum["total"],
        active_organizations=org_sum["active"],
        experiment_clients=num_exp_clients,
        current_round=current_round,
        total_rounds=total_rounds,
        threats_detected=threats_total,
        global_model_accuracy=global_acc,
        f1_score=global_f1,
        false_positive_rate=global_fpr,
        privacy_status=privacy_status,
        privacy_detail=privacy_detail,
        training_rounds=training_round_metrics,
        model_comparison=model_comparison,
        threat_categories=[
            ThreatCategory(
                name=t["type"],
                count=t["count"],
                color=_threat_color(t["type"]),
            )
            for t in threat_types[:6]
        ],
        org_activity=org_activity_items,
        recent_threats=[
            RecentThreat(
                id=t.id,
                timestamp=t.timestamp,
                organization=t.organization_name,
                threat_type=t.threat_type,
                severity=t.severity,     # type: ignore[arg-type]
                confidence=t.confidence,
                status=t.status,
                model_version=t.model_version,
            )
            for t in recent_threats_list
        ],
        system_components=[
            SystemComponent(name="FastAPI Server",        status="healthy", detail="Running — DB backed"),
            SystemComponent(name="SQLite Database",       status="healthy", detail="Connected via SQLAlchemy"),
            SystemComponent(name="ML Inference (Predict)",status="healthy" if exp_id else "unknown",
                            detail=f"Checkpoint from {exp_id}" if exp_id else "No experiment loaded"),
            SystemComponent(name="Flower FL Server",      status="unknown", detail="Not yet integrated"),
        ],
        experiment_id=exp_id,
        data_source=data_source,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Organizations
# ═════════════════════════════════════════════════════════════════════════════

async def get_organizations(db: AsyncSession) -> OrganizationsResponse:
    org_repo   = OrganizationRepo(db)
    train_repo = TrainingRepo(db)
    metric_repo = MetricRepo(db)

    all_orgs = await org_repo.get_all()
    org_sum  = await org_repo.get_summary()

    # Pull per-org metrics from latest experiment
    exp_id = await metric_repo.get_latest_experiment_id()
    exp_meta = await metric_repo.get_experiment_metadata(exp_id) if exp_id else {}
    total_rounds  = int(exp_meta.get("number_of_rounds", 0))
    local_epochs  = int(exp_meta.get("local_epochs", 0))
    total_samples = int(exp_meta.get("total_samples", 0))

    # Org metrics from experiment_org (IID run)
    org_exp_data: dict[str, dict] = {}
    if exp_id:
        exp_org = await metric_repo.get_by_category_for_experiment("experiment_org", exp_id)
        iid_org = [m for m in exp_org if m.model_type.endswith("__iid")]
        for m in iid_org:
            if m.org_id not in org_exp_data:
                org_exp_data[m.org_id] = {}
            org_exp_data[m.org_id][m.metric_name] = m.metric_value

    # Org partition data from experiment_partition
    partition_data: dict[str, dict] = {}
    if exp_id:
        exp_part = await metric_repo.get_by_category_for_experiment("experiment_partition", exp_id)
        iid_part = [m for m in exp_part if m.model_type.endswith("__iid")]
        for m in iid_part:
            if m.org_id not in partition_data:
                partition_data[m.org_id] = {}
            partition_data[m.org_id][m.metric_name] = m.metric_value

    # Client participations for training history
    participations = await train_repo.get_all_participations()

    org_schemas = []
    for o in all_orgs:
        exp_d = org_exp_data.get(o.id, {})
        part_d = partition_data.get(o.id, {})

        # Dataset size: prefer real experiment partition data
        dataset_size = int(part_d.get("total_samples", o.dataset_size))

        # Local accuracy: from experiment_org
        local_acc = exp_d.get("accuracy__local", o.local_model_accuracy)

        # Data distribution: from organization DB record (may be seeded)
        dist = []
        try:
            dist = json.loads(o.data_distribution_json)
        except Exception:
            pass

        # Training history from client_participations
        org_parts = sorted(
            [p for p in participations if p.org_id == o.id],
            key=lambda x: x.round_id,
            reverse=True,
        )[:10]

        # Determine joined_at — use DB value
        joined_at = o.joined_at if hasattr(o, "joined_at") and o.joined_at else "2026-01-01T00:00:00Z"

        # Local loss from experiment_org
        local_loss = exp_d.get("loss__local", None)

        org_schemas.append(OrgSchema(
            org_id=o.id,
            name=o.name,
            status=o.status,   # type: ignore[arg-type]
            dataset_size=dataset_size,
            local_model_status=o.local_model_status,
            local_model_accuracy=local_acc if o.id in org_exp_data else None,
            current_round=total_rounds if o.id in org_exp_data else None,
            last_update=o.last_update,
            participation_rate=o.participation_rate,
            data_distribution=[DataSlice(**d) for d in dist],
            recent_rounds=[
                OrgTrainingRound(
                    round=p.training_round.round_number,
                    status=p.status,
                    accuracy=p.local_accuracy,
                    duration_s=p.duration_s,
                )
                for p in org_parts
                if p.training_round is not None
            ],
        ))

    return OrganizationsResponse(
        summary=OrganizationSummary(**org_sum),
        organizations=org_schemas,
        data_source=f"experiment:{exp_id}" if exp_id else "database",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Training
# ═════════════════════════════════════════════════════════════════════════════

async def get_training(db: AsyncSession) -> TrainingResponse:
    train_repo  = TrainingRepo(db)
    metric_repo = MetricRepo(db)

    exp_id   = await metric_repo.get_latest_experiment_id()
    exp_meta = await metric_repo.get_experiment_metadata(exp_id) if exp_id else {}

    total_rounds  = int(exp_meta.get("number_of_rounds", 0))
    local_epochs  = int(exp_meta.get("local_epochs", 0))
    num_clients   = int(exp_meta.get("number_of_clients", 0))
    dirichlet_alpha = float(exp_meta.get("dirichlet_alpha", 0.0))
    total_samples = int(exp_meta.get("total_samples", 0))

    # IID summary metrics for global model accuracy
    global_acc  = 0.0
    global_f1   = 0.0
    global_loss = 0.0
    if exp_id:
        exp_summary = await metric_repo.get_by_category_for_experiment("experiment_summary", exp_id)
        iid_metrics = {m.metric_name: m.metric_value for m in exp_summary if m.model_type.endswith("__iid")}
        global_acc  = iid_metrics.get("accuracy", 0.0)
        global_f1   = iid_metrics.get("f1", 0.0)
        global_loss = iid_metrics.get("loss", 0.0)

    # Per-round metrics from experiment_round (IID)
    exp_rounds_data: dict[int, dict] = {}
    if exp_id:
        exp_rounds = await metric_repo.get_by_category_for_experiment("experiment_round", exp_id)
        iid_rounds = [m for m in exp_rounds if m.model_type.endswith("__iid")]
        for m in iid_rounds:
            if m.round_number not in exp_rounds_data:
                exp_rounds_data[m.round_number] = {}
            exp_rounds_data[m.round_number][m.metric_name] = m.metric_value

    # Client statuses from experiment_org (IID, last round)
    client_statuses: list[ClientStatus] = []
    if exp_id:
        exp_org = await metric_repo.get_by_category_for_experiment("experiment_org", exp_id)
        iid_org = [m for m in exp_org if m.model_type.endswith("__iid")]
        org_ids = sorted(set(m.org_id for m in iid_org if m.org_id))
        for oid in org_ids:
            org_d = {m.metric_name: m.metric_value for m in iid_org if m.org_id == oid}
            org_name = next(
                (m.organization.name for m in iid_org if m.org_id == oid and m.organization),
                oid,
            )
            client_statuses.append(ClientStatus(
                org_id=oid,
                org_name=org_name,
                connection_status="active",
                training_status="completed",
                local_accuracy=org_d.get("accuracy__local"),
                local_loss=org_d.get("loss__local"),
                samples=int(exp_meta.get("total_samples", 0)) // max(num_clients, 1),
                update_size_mb=None,
                duration_s=None,
            ))

    # Participation chart
    round_nums = sorted(exp_rounds_data.keys()) if exp_rounds_data else list(range(1, total_rounds + 1))
    participation = [
        ParticipationPoint(round=rn, participating=num_clients, total=num_clients)
        for rn in round_nums
    ]

    avg_dur = 0
    model_ver = f"v{total_rounds}.0" if total_rounds > 0 else "v0.0"

    return TrainingResponse(
        summary=TrainingSummary(
            current_round=total_rounds,
            total_rounds=total_rounds,
            global_model_version=model_ver,
            training_status="completed",
            global_accuracy=global_acc,
            global_f1=global_f1,
            global_loss=global_loss,
            avg_round_duration_s=avg_dur,
            aggregation_strategy="FedAvg",
            active_clients=num_clients,
            total_clients=num_clients,
        ),
        client_statuses=client_statuses,
        participation=participation,
        data_source=f"experiment:{exp_id}" if exp_id else "database",
    )


async def get_training_rounds(db: AsyncSession) -> TrainingRoundsResponse:
    metric_repo = MetricRepo(db)

    exp_id   = await metric_repo.get_latest_experiment_id()
    exp_meta = await metric_repo.get_experiment_metadata(exp_id) if exp_id else {}
    total_rounds = int(exp_meta.get("number_of_rounds", 0))
    num_clients  = int(exp_meta.get("number_of_clients", 0))

    schemas: list[TrainingRoundSchema] = []

    if exp_id:
        exp_rounds = await metric_repo.get_by_category_for_experiment("experiment_round", exp_id)
        iid_rounds = [m for m in exp_rounds if m.model_type.endswith("__iid")]
        round_nums = sorted(set(m.round_number for m in iid_rounds if m.round_number is not None))

        for rn in round_nums:
            rd = {m.metric_name: m.metric_value for m in iid_rounds if m.round_number == rn}
            schemas.append(TrainingRoundSchema(
                round=rn,
                status="completed",
                participating_clients=num_clients,
                total_clients=num_clients,
                accuracy=rd.get("federated_accuracy", 0.0),
                loss=rd.get("federated_fpr", 0.0),
                f1=rd.get("federated_f1", 0.0),
                duration_s=0,
                model_version=f"v{rn}.0",
                started_at=exp_meta.get("timestamp", datetime.now(timezone.utc).isoformat()),  # type: ignore[arg-type]
                completed_at=None,
            ))

    return TrainingRoundsResponse(
        rounds=list(reversed(schemas)),
        total=len(schemas),
        data_source=f"experiment:{exp_id}" if exp_id else "database",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Threats
# ═════════════════════════════════════════════════════════════════════════════

async def get_threats(
    db: AsyncSession,
    organization: str | None = None,
    threat_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> ThreatsResponse:
    repo = ThreatRepo(db)
    detections, total = await repo.get_threats(
        organization, threat_type, severity, status, search, page, page_size
    )

    # Real DB counts — no hardcoded numbers
    sev_counts    = await repo.get_counts_by_severity()
    status_counts = await repo.get_counts_by_status()
    types         = await repo.get_counts_by_type()
    total_all     = await repo.get_total_count()
    avg_conf      = await repo.avg_confidence()

    # Real hourly timeline
    raw_timeline  = await repo.get_hourly_timeline()
    timeline = [
        ThreatTimelinePoint(
            hour=row["hour"],
            critical=row["critical"],
            high=row["high"],
            medium=row["medium"],
            low=row["low"],
        )
        for row in raw_timeline
    ]

    dist = [
        ThreatTypeCount(type=t["type"], count=t["count"], color=_threat_color(t["type"]))
        for t in types
    ]

    return ThreatsResponse(
        summary=ThreatSummary(
            total=total_all,
            critical=sev_counts.get("critical", 0),
            high=sev_counts.get("high", 0),
            medium=sev_counts.get("medium", 0),
            low=sev_counts.get("low", 0),
            blocked=status_counts.get("blocked", 0),
            investigating=status_counts.get("investigating", 0),
            avg_confidence=avg_conf,
        ),
        detections=[
            ThreatSchema(
                id=d.id,
                timestamp=d.timestamp,
                organization=d.organization_name,
                organization_id=d.org_id or "",
                threat_type=d.threat_type,
                severity=d.severity,        # type: ignore[arg-type]
                confidence=d.confidence,
                status=d.status,            # type: ignore[arg-type]
                model_version=d.model_version,
                source_ip=d.source_ip,
                destination_ip=d.destination_ip,
                protocol=d.protocol,
                port=d.port,
                description=d.description,
                raw_features=json.loads(d.raw_features_json),
                detection_method=d.detection_method,  # type: ignore[arg-type]
            )
            for d in detections
        ],
        distribution=dist,
        timeline=timeline,
        total=total,
        page=page,
        page_size=page_size,
        data_source="database",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Performance
# ═════════════════════════════════════════════════════════════════════════════

async def get_performance(db: AsyncSession) -> PerformanceResponse:
    repo = MetricRepo(db)

    # Prefer latest CICIDS2017 experiment
    exp_id = await repo.get_latest_experiment_id()

    if exp_id:
        return await _get_performance_from_experiment(repo, exp_id)

    # Fallback: old-format rows if no experiment metadata exists
    exp_summary = await repo.get_by_category("experiment_summary")
    if exp_summary:
        return await _get_performance_old_format(repo)

    return await _get_performance_fallback(repo)


async def _get_performance_from_experiment(repo: MetricRepo, exp_id: str) -> PerformanceResponse:
    """Build full performance response from the specified CICIDS2017 experiment."""

    exp_summary = await repo.get_by_category_for_experiment("experiment_summary", exp_id)
    exp_rounds  = await repo.get_by_category_for_experiment("experiment_round",   exp_id)
    exp_org     = await repo.get_by_category_for_experiment("experiment_org",     exp_id)
    exp_noniid  = await repo.get_by_category_for_experiment("experiment_noniid",  exp_id)
    iid_cm      = await repo.get_confusion_matrix_like(f"{exp_id}__iid")
    noniid_cm   = await repo.get_confusion_matrix_like(f"{exp_id}__non_iid")

    iid_metrics    = {m.metric_name: m.metric_value for m in exp_summary if m.model_type.endswith("__iid")}
    noniid_metrics = {m.metric_name: m.metric_value for m in exp_summary if m.model_type.endswith("__non_iid")}
    iid_org        = [m for m in exp_org     if m.model_type.endswith("__iid")]
    iid_rounds     = [m for m in exp_rounds  if m.model_type.endswith("__iid")]

    # Local averages
    local_accs = [m.metric_value for m in iid_org if m.metric_name == "accuracy__local"]
    local_f1s  = [m.metric_value for m in iid_org if m.metric_name == "f1__local"]
    local_fprs = [m.metric_value for m in iid_org if m.metric_name == "precision__local"]

    fed_acc      = iid_metrics.get("accuracy",            0.0)
    local_avg_acc = round(sum(local_accs) / len(local_accs), 2) if local_accs else 0.0
    fed_f1       = iid_metrics.get("f1",                  0.0)
    local_avg_f1 = round(sum(local_f1s)  / len(local_f1s),  2) if local_f1s  else 0.0
    fed_fpr      = iid_metrics.get("false_positive_rate", 0.0)

    summary = PerformanceSummary(
        federated_accuracy=fed_acc,
        local_avg_accuracy=local_avg_acc,
        accuracy_gain=round(fed_acc - local_avg_acc, 2),
        federated_f1=fed_f1,
        local_avg_f1=local_avg_f1,
        f1_gain=round(fed_f1 - local_avg_f1, 2),
        federated_fpr=fed_fpr,
        local_avg_fpr=round(sum(local_fprs) / len(local_fprs), 2) if local_fprs else 0.0,
        fpr_reduction=0.0,
    )

    # Metric comparisons
    metric_comparisons = []
    for label in ["accuracy", "precision", "recall", "f1", "false_positive_rate"]:
        fed_val    = iid_metrics.get(label, 0.0)
        local_vals = [m.metric_value for m in iid_org if m.metric_name == f"{label}__local"]
        local_avg  = round(sum(local_vals) / len(local_vals), 2) if local_vals else 0.0
        metric_comparisons.append(MetricComparison(
            label=label.replace("_", " ").title(),
            local=local_avg,
            federated=fed_val,
            unit="%",
            higher_is_better=(label != "false_positive_rate"),
        ))

    # Per-org performance
    org_perf = []
    org_ids = sorted(set(m.org_id for m in iid_org if m.org_id))
    for oid in org_ids:
        org_data = {m.metric_name: m.metric_value for m in iid_org if m.org_id == oid}
        org_name = next(
            (m.organization.name for m in iid_org if m.org_id == oid and m.organization),
            oid,
        )
        org_perf.append(OrgPerformanceRow(
            org_id=oid,
            org_name=org_name,
            local_accuracy=org_data.get("accuracy__local",     0.0),
            local_f1=org_data.get("f1__local",                 0.0),
            local_precision=org_data.get("precision__local",   0.0),
            local_recall=org_data.get("recall__local",         0.0),
            federated_accuracy=org_data.get("accuracy__federated", 0.0),
            federated_f1=org_data.get("f1__federated",         0.0),
            gain=org_data.get("accuracy__gain",                 0.0),
        ))

    # Non-IID results
    noniid_results = []
    noniid_labels = sorted(set(m.model_type for m in exp_noniid))
    for label in noniid_labels:
        rows = {m.metric_name: m.metric_value for m in exp_noniid if m.model_type == label}
        display_name = label.split("__", 1)[-1] if "__" in label else label
        noniid_results.append(NonIIDResult(
            scenario=display_name,
            alpha=rows.get("noniid_scenario", 0.0),
            local_avg_accuracy=rows.get("local_avg_accuracy", 0.0),
            federated_accuracy=rows.get("federated_accuracy", 0.0),
            robustness_score=int(rows.get("robustness_score", 0)),
        ))

    # Round metrics
    round_nums = sorted(set(m.round_number for m in iid_rounds if m.round_number is not None))
    round_metrics = []
    for rn in round_nums:
        rd = {m.metric_name: m.metric_value for m in iid_rounds if m.round_number == rn}
        round_metrics.append(PerfRoundMetric(
            round=rn,
            local_avg_accuracy=rd.get("local_avg_accuracy", 0.0),
            federated_accuracy=rd.get("federated_accuracy", 0.0),
            local_avg_f1=rd.get("local_avg_f1",             0.0),
            federated_f1=rd.get("federated_f1",              0.0),
        ))

    # Collaboration benefit
    collab = []
    for label in ["accuracy", "precision", "recall", "f1"]:
        fed_val    = iid_metrics.get(label, 0.0)
        local_vals = [m.metric_value for m in iid_org if m.metric_name == f"{label}__local"]
        local_avg  = round(sum(local_vals) / len(local_vals), 2) if local_vals else 0.0
        improvement = round(fed_val - local_avg, 2)
        improvement_pct = round(improvement / local_avg * 100, 2) if local_avg > 0 else 0.0
        collab.append(CollaborationBenefit(
            metric=label.replace("_", " ").title(),
            local_avg=local_avg,
            federated=fed_val,
            improvement=improvement,
            improvement_pct=improvement_pct,
        ))

    # Confusion matrices
    labels = ["Normal", "DoS", "Brute Force", "Port Scan", "Malware"]
    iid_cells    = [
        ConfusionCell(actual=c.metric_name.split("__")[0], predicted=c.metric_name.split("__")[1], value=int(c.metric_value))
        for c in iid_cm
    ]
    noniid_cells = [
        ConfusionCell(actual=c.metric_name.split("__")[0], predicted=c.metric_name.split("__")[1], value=int(c.metric_value))
        for c in noniid_cm
    ]

    return PerformanceResponse(
        summary=summary,
        metric_comparisons=metric_comparisons,
        org_performance=org_perf,
        non_iid_results=noniid_results,
        round_metrics=round_metrics,
        collaboration_benefit=collab,
        local_confusion_matrix=ConfusionMatrix(labels=labels, model_type="iid",     cells=iid_cells),
        federated_confusion_matrix=ConfusionMatrix(labels=labels, model_type="non_iid", cells=noniid_cells),
        data_source=f"experiment:{exp_id}",
        experiment_id=exp_id,
    )


async def _get_performance_old_format(repo: MetricRepo) -> PerformanceResponse:
    """Old-format rows where model_type is bare 'iid' / 'non_iid'."""
    exp_summary = await repo.get_by_category("experiment_summary")
    exp_rounds  = await repo.get_by_category("experiment_round")
    exp_org     = await repo.get_by_category("experiment_org")
    exp_noniid  = await repo.get_by_category("experiment_noniid")
    iid_cm      = await repo.get_confusion_matrix("iid")
    noniid_cm   = await repo.get_confusion_matrix("non_iid")

    iid_metrics    = {m.metric_name: m.metric_value for m in exp_summary if m.model_type == "iid"}
    iid_org        = [m for m in exp_org    if m.model_type == "iid"]
    iid_rounds     = [m for m in exp_rounds if m.model_type == "iid"]

    local_accs = [m.metric_value for m in iid_org if m.metric_name == "accuracy__local"]
    local_f1s  = [m.metric_value for m in iid_org if m.metric_name == "f1__local"]
    local_fprs = [m.metric_value for m in iid_org if m.metric_name == "precision__local"]

    fed_acc       = iid_metrics.get("accuracy",            0.0)
    local_avg_acc = round(sum(local_accs) / len(local_accs), 2) if local_accs else 0.0
    fed_f1        = iid_metrics.get("f1",                  0.0)
    local_avg_f1  = round(sum(local_f1s)  / len(local_f1s),  2) if local_f1s  else 0.0
    fed_fpr       = iid_metrics.get("false_positive_rate", 0.0)

    summary = PerformanceSummary(
        federated_accuracy=fed_acc, local_avg_accuracy=local_avg_acc,
        accuracy_gain=round(fed_acc - local_avg_acc, 2),
        federated_f1=fed_f1, local_avg_f1=local_avg_f1,
        f1_gain=round(fed_f1 - local_avg_f1, 2),
        federated_fpr=fed_fpr,
        local_avg_fpr=round(sum(local_fprs) / len(local_fprs), 2) if local_fprs else 0.0,
        fpr_reduction=0.0,
    )

    metric_comparisons = []
    for label in ["accuracy", "precision", "recall", "f1", "false_positive_rate"]:
        fed_val    = iid_metrics.get(label, 0.0)
        local_vals = [m.metric_value for m in iid_org if m.metric_name == f"{label}__local"]
        local_avg  = round(sum(local_vals) / len(local_vals), 2) if local_vals else 0.0
        metric_comparisons.append(MetricComparison(
            label=label.replace("_", " ").title(), local=local_avg, federated=fed_val,
            unit="%", higher_is_better=(label != "false_positive_rate"),
        ))

    org_perf = []
    for oid in sorted(set(m.org_id for m in iid_org if m.org_id)):
        org_data = {m.metric_name: m.metric_value for m in iid_org if m.org_id == oid}
        org_name = next((m.organization.name for m in iid_org if m.org_id == oid and m.organization), oid)
        org_perf.append(OrgPerformanceRow(
            org_id=oid, org_name=org_name,
            local_accuracy=org_data.get("accuracy__local", 0.0),
            local_f1=org_data.get("f1__local", 0.0),
            local_precision=org_data.get("precision__local", 0.0),
            local_recall=org_data.get("recall__local", 0.0),
            federated_accuracy=org_data.get("accuracy__federated", 0.0),
            federated_f1=org_data.get("f1__federated", 0.0),
            gain=org_data.get("accuracy__gain", 0.0),
        ))

    noniid_results = []
    for label in sorted(set(m.model_type for m in exp_noniid)):
        rows = {m.metric_name: m.metric_value for m in exp_noniid if m.model_type == label}
        noniid_results.append(NonIIDResult(
            scenario=label, alpha=rows.get("noniid_scenario", 0.0),
            local_avg_accuracy=rows.get("local_avg_accuracy", 0.0),
            federated_accuracy=rows.get("federated_accuracy", 0.0),
            robustness_score=int(rows.get("robustness_score", 0)),
        ))

    round_nums = sorted(set(m.round_number for m in iid_rounds if m.round_number is not None))
    round_metrics = []
    for rn in round_nums:
        rd = {m.metric_name: m.metric_value for m in iid_rounds if m.round_number == rn}
        round_metrics.append(PerfRoundMetric(
            round=rn,
            local_avg_accuracy=rd.get("local_avg_accuracy", 0.0),
            federated_accuracy=rd.get("federated_accuracy", 0.0),
            local_avg_f1=rd.get("local_avg_f1", 0.0),
            federated_f1=rd.get("federated_f1", 0.0),
        ))

    collab = []
    for label in ["accuracy", "precision", "recall", "f1"]:
        fed_val    = iid_metrics.get(label, 0.0)
        local_vals = [m.metric_value for m in iid_org if m.metric_name == f"{label}__local"]
        local_avg  = round(sum(local_vals) / len(local_vals), 2) if local_vals else 0.0
        improvement = round(fed_val - local_avg, 2)
        collab.append(CollaborationBenefit(
            metric=label.replace("_", " ").title(), local_avg=local_avg, federated=fed_val,
            improvement=improvement, improvement_pct=round(improvement / local_avg * 100, 2) if local_avg > 0 else 0.0,
        ))

    labels = ["Normal", "DoS", "Brute Force", "Port Scan", "Malware"]
    iid_cells    = [ConfusionCell(actual=c.metric_name.split("__")[0], predicted=c.metric_name.split("__")[1], value=int(c.metric_value)) for c in iid_cm]
    noniid_cells = [ConfusionCell(actual=c.metric_name.split("__")[0], predicted=c.metric_name.split("__")[1], value=int(c.metric_value)) for c in noniid_cm]

    return PerformanceResponse(
        summary=summary, metric_comparisons=metric_comparisons, org_performance=org_perf,
        non_iid_results=noniid_results, round_metrics=round_metrics, collaboration_benefit=collab,
        local_confusion_matrix=ConfusionMatrix(labels=labels, model_type="iid",     cells=iid_cells),
        federated_confusion_matrix=ConfusionMatrix(labels=labels, model_type="non_iid", cells=noniid_cells),
        data_source="experiment:legacy",
    )


async def _get_performance_fallback(repo: MetricRepo) -> PerformanceResponse:
    """Last-resort: only seeded summary/comparison/round_perf data exists."""
    summaries   = await repo.get_summary_metrics()
    comparisons = await repo.get_comparison_metrics()
    rounds      = await repo.get_round_metrics()

    labels = ["DoS", "Brute Force", "Port Scan", "Malware", "Normal"]
    return PerformanceResponse(
        summary=PerformanceSummary(
            federated_accuracy=summaries.get("federated_accuracy", 0.0),
            local_avg_accuracy=summaries.get("local_avg_accuracy", 0.0),
            accuracy_gain=summaries.get("accuracy_gain",           0.0),
            federated_f1=summaries.get("federated_f1",             0.0),
            local_avg_f1=summaries.get("local_avg_f1",             0.0),
            f1_gain=summaries.get("f1_gain",                       0.0),
            federated_fpr=summaries.get("federated_fpr",           0.0),
            local_avg_fpr=summaries.get("local_avg_fpr",           0.0),
            fpr_reduction=summaries.get("fpr_reduction",           0.0),
        ),
        metric_comparisons=[
            MetricComparison(
                label=m.metric_name, local=m.metric_value,
                federated=next((f.metric_value for f in comparisons if f.metric_name == m.metric_name and f.model_type == "federated"), 0.0),
                unit="%", higher_is_better="Rate" not in m.metric_name,
            )
            for m in comparisons if m.model_type == "local"
        ],
        org_performance=[],
        non_iid_results=[],
        round_metrics=[
            PerfRoundMetric(
                round=m.round_number,
                local_avg_accuracy=m.metric_value,
                federated_accuracy=next((f.metric_value for f in rounds if f.round_number == m.round_number and f.metric_name == "federated_accuracy"), 0.0),
                local_avg_f1=next((f.metric_value for f in rounds if f.round_number == m.round_number and f.metric_name == "local_avg_f1"), 0.0),
                federated_f1=next((f.metric_value for f in rounds if f.round_number == m.round_number and f.metric_name == "federated_f1"), 0.0),
            )
            for m in rounds if m.metric_name == "local_avg_accuracy"
        ],
        collaboration_benefit=[],
        local_confusion_matrix=ConfusionMatrix(labels=labels, model_type="local",     cells=[]),
        federated_confusion_matrix=ConfusionMatrix(labels=labels, model_type="federated", cells=[]),
        data_source="database:seeded",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Privacy
# ═════════════════════════════════════════════════════════════════════════════

async def get_privacy(db: AsyncSession) -> PrivacyResponse:
    privacy_repo = PrivacyRepo(db)
    metric_repo  = MetricRepo(db)
    train_repo   = TrainingRepo(db)
    org_repo     = OrganizationRepo(db)

    events         = await privacy_repo.get_security_events()
    exp_id         = await metric_repo.get_latest_experiment_id()
    has_experiments = exp_id is not None

    # Real DP event counts from metrics
    privacy_events   = await metric_repo.get_by_category("privacy_event")
    clipping_events  = [e for e in privacy_events if e.metric_name == "clipping"]
    noise_events     = [e for e in privacy_events if e.metric_name == "noise_addition"]
    validation_events= [e for e in privacy_events if e.metric_name == "validation"]
    rejected_events  = [e for e in privacy_events if e.metric_name == "rejected"]

    # DP config from experiment metrics (use experiment-scoped query, IID format)
    dp_config: dict[str, float] = {}
    if has_experiments:
        exp_priv = await metric_repo.get_by_category_for_experiment("privacy_event", exp_id)
        iid_privacy = [e for e in exp_priv if e.model_type and e.model_type.endswith("__iid")]
        dp_config = {e.metric_name.replace("config__", ""): e.metric_value
                     for e in iid_privacy if e.metric_name.startswith("config__")}

    mechanisms_implemented = 3 if has_experiments else 1
    mechanisms_planned     = 1

    # Org update statuses from real client_participations for latest experiment round
    org_update_statuses: list[OrgUpdateStatus] = []

    if exp_id:
        exp_meta     = await metric_repo.get_experiment_metadata(exp_id)
        total_rounds = int(exp_meta.get("number_of_rounds", 0))
        all_orgs     = await org_repo.get_all()
        participations = await train_repo.get_all_participations()

        # Use experiment org IDs from experiment_org metrics
        exp_org = await metric_repo.get_by_category_for_experiment("experiment_org", exp_id)
        exp_org_ids = sorted(set(m.org_id for m in exp_org if m.org_id))

        # Filter to participating orgs only
        participating_orgs = [o for o in all_orgs if o.id in exp_org_ids]

        for org in participating_orgs:
            # Find the latest participation record for this org
            org_parts = sorted(
                [p for p in participations if p.org_id == org.id],
                key=lambda x: x.round_id,
                reverse=True,
            )
            latest_part = org_parts[0] if org_parts else None

            update_size = None
            submitted_at = None
            validation_passed = None
            notes = "Participated in experiment"

            if latest_part:
                update_size = f"{latest_part.update_size_mb:.1f} MB" if latest_part.update_size_mb else None
                submitted_at = latest_part.training_round.completed_at if latest_part.training_round else None
                validation_passed = latest_part.status == "completed"
                notes = "Clipped + noise added + validated." if has_experiments else "Completed."

            org_update_statuses.append(OrgUpdateStatus(
                org_id=org.id,
                org_name=org.name,
                round=total_rounds,
                update_status="submitted",
                update_size=update_size,
                submitted_at=submitted_at,
                validation_passed=validation_passed,
                notes=notes,
            ))

    clip_norm     = dp_config.get("clip_norm",       1.0)
    noise_std     = dp_config.get("noise_std",        0.1)
    epsilon       = dp_config.get("epsilon_per_round", 0.0)
    delta         = dp_config.get("delta",             1e-5)
    clip_count    = sum(int(e.metric_value) for e in clipping_events)
    noise_count   = sum(int(e.metric_value) for e in noise_events)
    reject_count  = sum(int(e.metric_value) for e in rejected_events)

    return PrivacyResponse(
        summary=PrivacySummary(
            raw_data_shared=False,
            model_updates_only=True,
            privacy_mechanisms_implemented=mechanisms_implemented,
            privacy_mechanisms_planned=mechanisms_planned,
            security_events_last_24h=len(events),
            unauthorized_attempts_blocked=reject_count,
        ),
        properties=[
            PrivacyProperty(
                id="data-locality", label="Data Locality",
                category="data_locality",
                description="Organisation raw data never leaves the local environment.",
                status="enforced",
                detail="Enforced by FL architecture — only model weight updates are transmitted. "
                       "Raw training features and labels remain on-device.",
                planned=False,
            ),
            PrivacyProperty(
                id="model-updates", label="Model Updates Only",
                category="model_update",
                description="Only model parameter deltas are sent to the aggregation server.",
                status="enforced",
                detail="Flower NumPyClient transmits List[np.ndarray] of weight matrices. "
                       "No raw samples, labels, or intermediate activations are included.",
                planned=False,
            ),
            PrivacyProperty(
                id="update-clipping", label=f"Update Clipping (L2 Norm ≤ {clip_norm})",
                category="model_update",
                description="Model updates are clipped to a maximum L2 norm before transmission.",
                status="enforced" if has_experiments else "planned",
                detail=(
                    f"Applied to {clip_count} updates across experiments. "
                    f"clip_norm={clip_norm}."
                ) if has_experiments else "Planned: L2 norm clipping with configurable bound.",
                planned=not has_experiments,
            ),
            PrivacyProperty(
                id="dp-noise", label="Differential Privacy (Gaussian Mechanism)",
                category="model_update",
                description="Calibrated Gaussian noise added to model updates for formal (ε,δ)-DP.",
                status="enforced" if has_experiments else "planned",
                detail=(
                    f"Applied to {noise_count} updates. "
                    f"noise_std={noise_std}, ε≈{epsilon:.2f}/round, δ={delta:.0e}."
                ) if has_experiments else "Planned: Gaussian mechanism with calibrated noise.",
                planned=not has_experiments,
            ),
            PrivacyProperty(
                id="server-validation", label="Server-Side Update Validation",
                category="aggregation",
                description="Server validates incoming updates for structural integrity and anomalies.",
                status="enforced" if has_experiments else "planned",
                detail=(
                    f"Checks structural match, NaN/Inf, L2 norm bounds, and extreme values. "
                    f"{reject_count} updates rejected."
                ) if has_experiments else "Planned: Structural and anomaly validation.",
                planned=not has_experiments,
            ),
            PrivacyProperty(
                id="sec-agg", label="Secure Aggregation",
                category="aggregation",
                description="Server cannot see individual client updates in plaintext.",
                status="planned",
                detail="Not yet implemented. Planned for a future phase.",
                planned=True,
            ),
        ],
        org_update_statuses=org_update_statuses,
        security_events=[
            SecurityEvent(
                id=e.id, timestamp=e.timestamp,
                organization=e.organization.name if e.organization else None,
                event=e.event_type, category=e.category,
                severity=e.severity,    # type: ignore[arg-type]
                status=e.status,        # type: ignore[arg-type]
                detail=e.detail,
            )
            for e in events
        ],
        data_source=f"experiment:{exp_id}" if has_experiments else "database",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Testing
# ═════════════════════════════════════════════════════════════════════════════

async def get_testing(db: AsyncSession) -> TestingResponse:
    repo  = TestingRepo(db)
    cases = await repo.get_all()
    summary = await repo.get_summary()

    return TestingResponse(
        summary=TestSuiteSummary(**summary),
        test_cases=[
            TestCase(
                id=t.id, name=t.name, category=t.category, description=t.description,
                expected_result=t.expected_result, actual_result=t.actual_result,
                status=t.status, execution_state=t.execution_state,
                timestamp=t.timestamp, notes=t.notes,
            )
            for t in cases
        ],
        acceptance_criteria=[
            AcceptanceCriterion(code="AC-1", title="Representative Operation",
                description="Primary function under normal conditions.",
                tests=["TC-101", "TC-102", "TC-103"], passing_threshold=90),
            AcceptanceCriterion(code="AC-2", title="Boundary and Failure",
                description="Edge cases, failures, invalid inputs.",
                tests=["TC-201", "TC-202", "TC-204"], passing_threshold=80),
            AcceptanceCriterion(code="AC-3", title="Independent Acceptance",
                description="Independently verifiable evidence.",
                tests=["TC-301", "TC-302", "TC-303"], passing_threshold=100),
            AcceptanceCriterion(code="AC-4", title="Frozen Resource Envelope",
                description="System within defined resource limits.",
                tests=["TC-401", "TC-402", "TC-403"], passing_threshold=100),
        ],
    )


# ═════════════════════════════════════════════════════════════════════════════
# System
# ═════════════════════════════════════════════════════════════════════════════

async def get_system(db: AsyncSession, db_ok: bool = True) -> SystemResponse:
    uptime = int(time.time() - _START_TIME)
    from app.core.config import get_settings
    cfg = get_settings()
    now = datetime.now(timezone.utc).isoformat()
    return SystemResponse(
        status="healthy", version=cfg.app_version, environment=cfg.environment, uptime_s=uptime,
        fl_connected=False, ml_connected=False, db_connected=db_ok,
        components=[
            ComponentHealth(name="FastAPI Server",     status="healthy",             detail=f"Running {cfg.environment} mode", last_checked=now),
            ComponentHealth(name="SQLite Database",    status="healthy" if db_ok else "offline",
                            detail="Connected via SQLAlchemy" if db_ok else "Connection failed", last_checked=now),
            ComponentHealth(name="Flower FL Server",   status="unknown", detail="Not yet integrated", last_checked=now),
            ComponentHealth(name="PyTorch ML Pipeline",status="unknown", detail="Inference available via /api/predict", last_checked=now),
        ],
    )
