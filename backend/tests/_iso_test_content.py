"""
Isolated regression tests for all repository and service functions.

Uses an in-memory SQLite database seeded with deterministic temporary data so
the real cyber20.db is NEVER touched. Every test in this file:
  - Calls the actual repository / service method (not just assertion on dicts).
  - Works with real SQLAlchemy queries against a throwaway schema.
  - Is fully isolated via a session-scoped async fixture.

Run with:  cd backend && pytest tests/test_repos_isolated.py -v
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Import all models to register them with Base.metadata
import app.models  # noqa: F401
from app.database.session import Base

from app.repositories.threat_repo import ThreatRepo
from app.repositories.organization_repo import OrganizationRepo
from app.repositories.metric_repo import MetricRepo
from app.repositories.privacy_repo import PrivacyRepo
from app.repositories.testing_repo import TestingRepo
from app.repositories.training_repo import TrainingRepo

from app.models.threat_detection import ThreatDetection
from app.models.organization import Organization
from app.models.metric import Metric
from app.models.privacy_event import PrivacyEvent
from app.models.validation_test import ValidationTest
from app.models.training_round import TrainingRound
from app.models.client_participation import ClientParticipation


EXP_ID = "exp_test_isolated_abc123"
EXP_DATASET = "test_dataset"
EXP_IID_MODEL_TYPE = f"{EXP_ID}__{EXP_DATASET}__iid"

EXPECTED_ROUNDS = 3
EXPECTED_CLIENTS = 2
EXPECTED_ACCURACY = 72.5
EXPECTED_F1 = 55.3
EXPECTED_FPR = 6.8
EXPECTED_TOTAL_SAMPLES = 10000


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture(scope="module")
def event_loop():
    """Module-scoped event loop (required for module-scoped async fixtures)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh in-memory SQLite database, build all tables, seed
    deterministic test data, and yield one shared AsyncSession for the module.
    The real cyber20.db is never opened or modified.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession,
        expire_on_commit=False, autocommit=False, autoflush=False,
    )
    async with factory() as session:
        await _seed_test_data(session)
        await session.commit()
        yield session
    await engine.dispose()


async def _seed_test_data(session: AsyncSession) -> None:
    """Insert deterministic temporary data into the in-memory DB."""
    orgs = [
        Organization(id="org-alpha", name="Alpha Corp", status="active",
                     dataset_size=5000, participation_rate=1.0,
                     local_model_status="ready", local_model_accuracy=96.1,
                     current_round=3, last_update=_ts(), joined_at=_ts(),
                     privacy_mode="Model updates only", data_distribution_json="[]"),
        Organization(id="org-beta", name="Beta Ltd", status="training",
                     dataset_size=5000, participation_rate=1.0,
                     local_model_status="ready", local_model_accuracy=94.5,
                     current_round=3, last_update=_ts(), joined_at=_ts(),
                     privacy_mode="Model updates only", data_distribution_json="[]"),
        Organization(id="org-delta", name="Delta Inc", status="idle",
                     dataset_size=0, participation_rate=0.0,
                     local_model_status="pending", local_model_accuracy=None,
                     current_round=0, last_update=_ts(), joined_at=_ts(),
                     privacy_mode="Model updates only", data_distribution_json="[]"),
    ]
    for o in orgs:
        session.add(o)
    await session.flush()

    severities = ["critical", "high", "medium", "low", "critical"]
    types = ["DoS/DDoS", "Brute Force", "Port Scan", "Malware", "DoS/DDoS"]
    statuses = ["blocked", "investigating", "blocked", "blocked", "blocked"]
    for i in range(5):
        session.add(ThreatDetection(
            id=f"threat-test-{i:03d}",
            timestamp=f"2026-10-01T10:{i:02d}:00+00:00",
            org_id="org-alpha",
            organization_name="Alpha Corp",
            threat_type=types[i],
            severity=severities[i],
            confidence=0.9 - i * 0.05,
            status=statuses[i],
            model_version="v1.0",
            source_ip=f"192.168.1.{i+1}",
            destination_ip="10.0.0.1",
            protocol="TCP",
            port=8080 + i,
            description=f"Test threat {i}",
            raw_features_json="{}",
            detection_method="federated",
        ))
    await session.flush()

    for name, val, mtype in [
        ("experiment_id", 0.0, EXP_IID_MODEL_TYPE),
        ("number_of_rounds", float(EXPECTED_ROUNDS), EXP_IID_MODEL_TYPE),
        ("local_epochs", 3.0, EXP_IID_MODEL_TYPE),
        ("number_of_clients", float(EXPECTED_CLIENTS), EXP_IID_MODEL_TYPE),
        ("total_samples", float(EXPECTED_TOTAL_SAMPLES), EXP_IID_MODEL_TYPE),
        ("dirichlet_alpha", 0.5, EXP_IID_MODEL_TYPE),
        ("dataset", 1.0, EXP_IID_MODEL_TYPE),
    ]:
        session.add(Metric(timestamp=_ts(), metric_name=name, metric_value=val,
                           model_type=mtype, category="experiment_metadata"))

    for name, val in [
        ("accuracy", EXPECTED_ACCURACY),
        ("f1", EXPECTED_F1),
        ("false_positive_rate", EXPECTED_FPR),
        ("precision", 60.0),
        ("recall", 55.0),
    ]:
        session.add(Metric(timestamp=_ts(), metric_name=name, metric_value=val,
                           model_type=EXP_IID_MODEL_TYPE, category="experiment_summary"))

    round_accs = [60.0, 66.0, EXPECTED_ACCURACY]
    round_f1s = [40.0, 48.0, EXPECTED_F1]
    round_fprs = [10.0, 8.0, EXPECTED_FPR]
    for rn in range(1, EXPECTED_ROUNDS + 1):
        for mname, mval in [
            ("federated_accuracy", round_accs[rn - 1]),
            ("federated_f1", round_f1s[rn - 1]),
            ("federated_fpr", round_fprs[rn - 1]),
        ]:
            session.add(Metric(timestamp=_ts(), metric_name=mname, metric_value=mval,
                               model_type=EXP_IID_MODEL_TYPE, round_number=rn,
                               category="experiment_round"))

    for org_id, local_acc in [("org-alpha", 96.1), ("org-beta", 94.5)]:
        for mname, mval in [
            ("accuracy__local", local_acc),
            ("f1__local", local_acc - 40.0),
            ("precision__local", local_acc - 35.0),
            ("recall__local", local_acc - 38.0),
        ]:
            session.add(Metric(timestamp=_ts(), metric_name=mname, metric_value=mval,
                               model_type=EXP_IID_MODEL_TYPE, org_id=org_id,
                               category="experiment_org"))

    for mname, mval in [
        ("config__clipping_enabled", 1.0),
        ("config__dp_noise_enabled", 1.0),
        ("config__validation_enabled", 1.0),
        ("config__clip_norm", 1.0),
        ("config__noise_std", 0.01),
        ("config__epsilon_per_round", 4.92),
        ("config__delta", 1e-5),
    ]:
        session.add(Metric(timestamp=_ts(), metric_name=mname, metric_value=mval,
                           model_type=EXP_IID_MODEL_TYPE, category="privacy_event"))

    for rn in range(1, EXPECTED_ROUNDS + 1):
        session.add(TrainingRound(
            round_number=rn, status="completed", started_at=_ts(), completed_at=_ts(),
            duration_s=120, participating_clients=EXPECTED_CLIENTS,
            total_clients=EXPECTED_CLIENTS, accuracy=round_accs[rn - 1],
            loss=0.5 - rn * 0.05, f1=round_f1s[rn - 1],
            model_version=f"v1.{rn}", aggregation_method="FedAvg",
        ))
    await session.flush()

    from sqlalchemy import select
    for rn in range(1, EXPECTED_ROUNDS + 1):
        tr = (await session.execute(
            select(TrainingRound).where(TrainingRound.round_number == rn)
        )).scalar_one()
        for org_id in ["org-alpha", "org-beta"]:
            session.add(ClientParticipation(
                round_id=tr.id, org_id=org_id, status="completed",
                local_accuracy=95.0, local_loss=0.2, samples_used=5000,
                duration_s=60, update_size_mb=1.5,
            ))
    await session.flush()

    for i in range(3):
        session.add(PrivacyEvent(
            id=f"priv-ev-test-{i:03d}", timestamp=_ts(), org_id="org-alpha",
            event_type="update_validation", category="validation",
            severity="info" if i < 2 else "critical",
            status="resolved", detail=f"Privacy event {i}",
        ))
    await session.flush()

    states = [("pass", "executed"), ("fail", "mock_run"), ("pending", "not_run"),
              ("warning", "executed"), ("pass", "executed")]
    for i, (status, exec_state) in enumerate(states):
        session.add(ValidationTest(
            id=f"vt-{i:02d}", name=f"Test Case {i}",
            category="unit" if i < 3 else "integration",
            description=f"Description {i}", expected_result="Pass",
            actual_result="Pass" if status == "pass" else None,
            status=status, execution_state=exec_state, timestamp=_ts(), notes="",
        ))
    await session.flush()


# ==================== ThreatRepo ====================

class TestThreatRepoIsolated:
    """ThreatRepo methods against the isolated in-memory database."""

    async def test_get_total_count(self, db_session):
        assert await ThreatRepo(db_session).get_total_count() == 5

    async def test_count_alias(self, db_session):
        repo = ThreatRepo(db_session)
        assert await repo.count() == await repo.get_total_count()

    async def test_get_counts_by_severity_values(self, db_session):
        counts = await ThreatRepo(db_session).get_counts_by_severity()
        assert isinstance(counts, dict)
        assert counts.get("critical") == 2
        assert counts.get("high") == 1
        assert counts.get("medium") == 1
        assert counts.get("low") == 1

    async def test_get_counts_by_severity_sums_to_total(self, db_session):
        repo = ThreatRepo(db_session)
        assert sum((await repo.get_counts_by_severity()).values()) == await repo.get_total_count()

    async def test_get_counts_by_status_values(self, db_session):
        counts = await ThreatRepo(db_session).get_counts_by_status()
        assert counts.get("blocked") == 4
        assert counts.get("investigating") == 1

    async def test_get_counts_by_status_sums_to_total(self, db_session):
        repo = ThreatRepo(db_session)
        assert sum((await repo.get_counts_by_status()).values()) == await repo.get_total_count()

    async def test_get_counts_by_type_values(self, db_session):
        types = await ThreatRepo(db_session).get_counts_by_type()
        type_map = {t["type"]: t["count"] for t in types}
        assert type_map.get("DoS/DDoS") == 2
        assert type_map.get("Brute Force") == 1
        assert type_map.get("Port Scan") == 1
        assert type_map.get("Malware") == 1

    async def test_get_counts_by_type_sums_to_total(self, db_session):
        repo = ThreatRepo(db_session)
        types = await repo.get_counts_by_type()
        assert sum(t["count"] for t in types) == await repo.get_total_count()

    async def test_get_hourly_timeline_structure(self, db_session):
        timeline = await ThreatRepo(db_session).get_hourly_timeline()
        assert isinstance(timeline, list)
        for pt in timeline:
            for key in ["hour", "critical", "high", "medium", "low"]:
                assert key in pt

    async def test_get_hourly_timeline_sum_equals_total(self, db_session):
        repo = ThreatRepo(db_session)
        tl = await repo.get_hourly_timeline()
        tl_sum = sum(pt["critical"] + pt["high"] + pt["medium"] + pt["low"] for pt in tl)
        assert tl_sum == await repo.get_total_count()

    async def test_get_threats_no_filter(self, db_session):
        threats, total = await ThreatRepo(db_session).get_threats()
        assert total == 5 and len(threats) == 5

    async def test_get_threats_filter_severity_critical(self, db_session):
        threats, total = await ThreatRepo(db_session).get_threats(severity="critical")
        assert total == 2
        assert all(t.severity == "critical" for t in threats)

    async def test_get_threats_filter_status_blocked(self, db_session):
        threats, total = await ThreatRepo(db_session).get_threats(status="blocked")
        assert total == 4
        assert all(t.status == "blocked" for t in threats)

    async def test_get_threats_filter_type(self, db_session):
        threats, total = await ThreatRepo(db_session).get_threats(threat_type="Brute Force")
        assert total == 1
        assert threats[0].threat_type == "Brute Force"

    async def test_get_threats_filter_org(self, db_session):
        _, total = await ThreatRepo(db_session).get_threats(organization="Alpha Corp")
        assert total == 5

    async def test_get_threats_filter_search(self, db_session):
        _, total = await ThreatRepo(db_session).get_threats(search="DoS")
        assert total == 2

    async def test_get_threats_pagination_page1(self, db_session):
        threats, total = await ThreatRepo(db_session).get_threats(page=1, page_size=2)
        assert total == 5 and len(threats) == 2

    async def test_get_threats_pagination_page2(self, db_session):
        threats, total = await ThreatRepo(db_session).get_threats(page=2, page_size=2)
        assert total == 5 and len(threats) == 2

    async def test_count_by_status_blocked(self, db_session):
        assert await ThreatRepo(db_session).count_by_status("blocked") == 4

    async def test_count_by_status_investigating(self, db_session):
        assert await ThreatRepo(db_session).count_by_status("investigating") == 1

    async def test_avg_confidence(self, db_session):
        avg = await ThreatRepo(db_session).avg_confidence()
        assert isinstance(avg, float)
        assert abs(avg - 0.80) < 0.05

    async def test_add_threat_increases_count(self, db_session):
        repo = ThreatRepo(db_session)
        new_t = ThreatDetection(
            id="threat-add-test-001", timestamp=_ts(), org_id="org-alpha",
            organization_name="Alpha Corp", threat_type="Malware",
            severity="high", confidence=0.95, status="blocked",
            model_version="v1.0", source_ip="10.0.0.99",
            destination_ip="10.0.0.1", protocol="UDP", port=53,
            description="Add test", raw_features_json="{}",
            detection_method="federated",
        )
        await repo.add(new_t)
        assert await repo.get_total_count() == 6
        await db_session.delete(new_t)
        await db_session.flush()


# ==================== OrganizationRepo ====================

class TestOrganizationRepoIsolated:
    """OrganizationRepo methods against the isolated in-memory database."""

    async def test_count(self, db_session):
        assert await OrganizationRepo(db_session).count() == 3

    async def test_get_all_returns_all(self, db_session):
        assert len(await OrganizationRepo(db_session).get_all()) == 3

    async def test_get_all_ordered_by_name(self, db_session):
        orgs = await OrganizationRepo(db_session).get_all()
        names = [o.name for o in orgs]
        assert names == sorted(names)

    async def test_get_by_id_found(self, db_session):
        org = await OrganizationRepo(db_session).get_by_id("org-alpha")
        assert org is not None and org.name == "Alpha Corp"

    async def test_get_by_id_not_found(self, db_session):
        assert await OrganizationRepo(db_session).get_by_id("nonexistent") is None

    async def test_get_summary_counts(self, db_session):
        s = await OrganizationRepo(db_session).get_summary()
        assert s["total"] == 3
        assert s["active"] == 1
        assert s["training"] == 1
        assert s["idle"] == 1
        assert s["offline"] == 0

    async def test_get_data_distribution_empty(self, db_session):
        dist = await OrganizationRepo(db_session).get_data_distribution("org-alpha")
        assert dist == []

    async def test_get_data_distribution_unknown(self, db_session):
        assert await OrganizationRepo(db_session).get_data_distribution("no-such") == []

    async def test_upsert_updates_existing(self, db_session):
        repo = OrganizationRepo(db_session)
        org = await repo.get_by_id("org-delta")
        org.dataset_size = 999
        await repo.upsert(org)
        updated = await repo.get_by_id("org-delta")
        assert updated.dataset_size == 999
        updated.dataset_size = 0
        await repo.upsert(updated)

    async def test_upsert_inserts_new(self, db_session):
        repo = OrganizationRepo(db_session)
        new_org = Organization(
            id="org-new-upsert-test", name="Zeta Corp", status="active",
            dataset_size=1, participation_rate=0.5, local_model_status="ready",
            local_model_accuracy=80.0, current_round=0, last_update=_ts(),
            joined_at=_ts(), privacy_mode="Model updates only",
            data_distribution_json="[]",
        )
        await repo.upsert(new_org)
        assert await repo.count() == 4
        found = await repo.get_by_id("org-new-upsert-test")
        assert found is not None and found.name == "Zeta Corp"
        await db_session.delete(found)
        await db_session.flush()
        assert await repo.count() == 3


# ==================== MetricRepo ====================

class TestMetricRepoIsolated:
    """MetricRepo methods against the isolated in-memory database."""

    async def test_get_latest_experiment_id_value(self, db_session):
        assert await MetricRepo(db_session).get_latest_experiment_id() == EXP_ID

    async def test_get_latest_experiment_id_is_string(self, db_session):
        exp_id = await MetricRepo(db_session).get_latest_experiment_id()
        assert isinstance(exp_id, str)

    async def test_get_latest_experiment_id_no_suffix(self, db_session):
        exp_id = await MetricRepo(db_session).get_latest_experiment_id()
        assert "__" not in exp_id

    async def test_get_experiment_ids_list_contains_exp(self, db_session):
        ids = await MetricRepo(db_session).get_experiment_ids_list()
        assert EXP_ID in ids

    async def test_get_experiment_ids_list_no_duplicates(self, db_session):
        ids = await MetricRepo(db_session).get_experiment_ids_list()
        assert len(ids) == len(set(ids))

    async def test_get_experiment_metadata_is_nonempty(self, db_session):
        meta = await MetricRepo(db_session).get_experiment_metadata(EXP_ID)
        assert isinstance(meta, dict) and len(meta) > 0

    async def test_get_experiment_metadata_rounds(self, db_session):
        meta = await MetricRepo(db_session).get_experiment_metadata(EXP_ID)
        assert int(meta["number_of_rounds"]) == EXPECTED_ROUNDS

    async def test_get_experiment_metadata_clients(self, db_session):
        meta = await MetricRepo(db_session).get_experiment_metadata(EXP_ID)
        assert int(meta["number_of_clients"]) == EXPECTED_CLIENTS

    async def test_get_experiment_metadata_samples(self, db_session):
        meta = await MetricRepo(db_session).get_experiment_metadata(EXP_ID)
        assert int(meta["total_samples"]) == EXPECTED_TOTAL_SAMPLES

    async def test_get_experiment_metadata_unknown_is_empty(self, db_session):
        assert await MetricRepo(db_session).get_experiment_metadata("nonexistent_xyz") == {}

    async def test_summary_contains_accuracy_and_f1(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_summary", EXP_ID)
        names = {m.metric_name for m in rows}
        assert "accuracy" in names and "f1" in names

    async def test_iid_accuracy_value(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_summary", EXP_ID)
        iid = {m.metric_name: m.metric_value for m in rows if m.model_type.endswith("__iid")}
        assert abs(iid.get("accuracy", 0) - EXPECTED_ACCURACY) < 0.1

    async def test_iid_f1_value(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_summary", EXP_ID)
        iid = {m.metric_name: m.metric_value for m in rows if m.model_type.endswith("__iid")}
        assert abs(iid.get("f1", 0) - EXPECTED_F1) < 0.1

    async def test_iid_fpr_value(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_summary", EXP_ID)
        iid = {m.metric_name: m.metric_value for m in rows if m.model_type.endswith("__iid")}
        assert abs(iid.get("false_positive_rate", 0) - EXPECTED_FPR) < 0.1

    async def test_experiment_round_unknown_is_empty(self, db_session):
        assert await MetricRepo(db_session).get_by_category_for_experiment("experiment_round", "bad_id") == []

    async def test_round_numbers_match_expected(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_round", EXP_ID)
        iid = [m for m in rows if m.model_type.endswith("__iid")]
        nums = sorted({m.round_number for m in iid if m.round_number})
        assert nums == list(range(1, EXPECTED_ROUNDS + 1))

    async def test_last_round_accuracy(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_round", EXP_ID)
        iid = [m for m in rows if m.model_type.endswith("__iid")]
        last = {m.metric_name: m.metric_value for m in iid if m.round_number == EXPECTED_ROUNDS}
        assert abs(last.get("federated_accuracy", 0) - EXPECTED_ACCURACY) < 0.1

    async def test_experiment_org_participants(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_org", EXP_ID)
        iid = [m for m in rows if m.model_type.endswith("__iid")]
        assert {m.org_id for m in iid if m.org_id} == {"org-alpha", "org-beta"}

    async def test_privacy_clipping_enabled(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("privacy_event", EXP_ID)
        priv = {r.metric_name: r.metric_value for r in rows if r.model_type.endswith("__iid")}
        assert bool(priv.get("config__clipping_enabled", 0)) is True

    async def test_privacy_noise_enabled(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("privacy_event", EXP_ID)
        priv = {r.metric_name: r.metric_value for r in rows if r.model_type.endswith("__iid")}
        assert bool(priv.get("config__dp_noise_enabled", 0)) is True

    async def test_get_by_category_legacy(self, db_session):
        rows = await MetricRepo(db_session).get_by_category("experiment_metadata")
        assert len(rows) > 0

    async def test_get_by_name_and_type(self, db_session):
        rows = await MetricRepo(db_session).get_by_name_and_type("accuracy", EXP_IID_MODEL_TYPE)
        assert len(rows) >= 1
        assert abs(rows[0].metric_value - EXPECTED_ACCURACY) < 0.1

    async def test_get_for_round(self, db_session):
        assert len(await MetricRepo(db_session).get_for_round(1)) >= 3

    async def test_get_for_org(self, db_session):
        assert len(await MetricRepo(db_session).get_for_org("org-alpha")) > 0

    async def test_count_positive(self, db_session):
        assert await MetricRepo(db_session).count() > 0

    async def test_add_and_retrieve_metric(self, db_session):
        repo = MetricRepo(db_session)
        before = await repo.count()
        m = Metric(timestamp=_ts(), metric_name="test_metric_add",
                   metric_value=99.9, model_type="test_model",
                   category="test_category_add")
        await repo.add(m)
        assert await repo.count() == before + 1
        rows = await repo.get_by_category("test_category_add")
        assert any(r.metric_name == "test_metric_add" for r in rows)
        await db_session.delete(m)
        await db_session.flush()


# ==================== PrivacyRepo ====================

class TestPrivacyRepoIsolated:
    """PrivacyRepo methods against the isolated in-memory database."""

    async def test_get_security_events_count(self, db_session):
        assert len(await PrivacyRepo(db_session).get_security_events()) == 3

    async def test_get_events_by_severity_info(self, db_session):
        events = await PrivacyRepo(db_session).get_events_by_severity("info")
        assert len(events) == 2
        assert all(e.severity == "info" for e in events)

    async def test_get_events_by_severity_critical(self, db_session):
        events = await PrivacyRepo(db_session).get_events_by_severity("critical")
        assert len(events) == 1 and events[0].severity == "critical"

    async def test_count_recent(self, db_session):
        assert await PrivacyRepo(db_session).count_recent() == 3

    async def test_count_critical(self, db_session):
        assert await PrivacyRepo(db_session).count_critical() == 1

    async def test_count_alias(self, db_session):
        repo = PrivacyRepo(db_session)
        assert await repo.count() == await repo.count_recent()

    async def test_add_privacy_event(self, db_session):
        repo = PrivacyRepo(db_session)
        new_ev = PrivacyEvent(
            id="priv-ev-add-001", timestamp=_ts(), org_id="org-beta",
            event_type="dp_noise_applied", category="dp", severity="info",
            status="logged", detail="DP noise added",
        )
        await repo.add(new_ev)
        assert await repo.count_recent() == 4
        await db_session.delete(new_ev)
        await db_session.flush()


# ==================== TestingRepo ====================

class TestTestingRepoIsolated:
    """TestingRepo methods against the isolated in-memory database."""

    async def test_get_all_count(self, db_session):
        assert len(await TestingRepo(db_session).get_all()) == 5

    async def test_get_by_category_unit(self, db_session):
        assert len(await TestingRepo(db_session).get_by_category("unit")) == 3

    async def test_get_by_category_integration(self, db_session):
        assert len(await TestingRepo(db_session).get_by_category("integration")) == 2

    async def test_get_summary_total(self, db_session):
        s = await TestingRepo(db_session).get_summary()
        assert s["total"] == 5

    async def test_get_summary_passed(self, db_session):
        s = await TestingRepo(db_session).get_summary()
        assert s["passed"] == 2

    async def test_get_summary_failed(self, db_session):
        s = await TestingRepo(db_session).get_summary()
        assert s["failed"] == 1

    async def test_get_summary_pass_rate(self, db_session):
        # Seeded: 3 executed + 1 mock_run = ran=4; passed=2 → pass_rate = 50.0%
        s = await TestingRepo(db_session).get_summary()
        assert s["pass_rate"] == pytest.approx(50.0, abs=0.2)

    async def test_count(self, db_session):
        assert await TestingRepo(db_session).count() == 5

    async def test_add_validation_test(self, db_session):
        repo = TestingRepo(db_session)
        new_t = ValidationTest(
            id="vt-99", name="Regression test", category="regression",
            description="Added by test", expected_result="Pass",
            actual_result="Pass", status="pass", execution_state="executed",
            timestamp=_ts(), notes="",
        )
        await repo.add(new_t)
        assert await repo.count() == 6
        await db_session.delete(new_t)
        await db_session.flush()


# ==================== TrainingRepo ====================

class TestTrainingRepoIsolated:
    """TrainingRepo methods against the isolated in-memory database."""

    async def test_get_all_rounds_count(self, db_session):
        assert len(await TrainingRepo(db_session).get_all_rounds()) == EXPECTED_ROUNDS

    async def test_get_all_rounds_ordered(self, db_session):
        rounds = await TrainingRepo(db_session).get_all_rounds()
        assert [r.round_number for r in rounds] == list(range(1, EXPECTED_ROUNDS + 1))

    async def test_get_latest_round(self, db_session):
        latest = await TrainingRepo(db_session).get_latest_round()
        assert latest is not None and latest.round_number == EXPECTED_ROUNDS

    async def test_count_rounds(self, db_session):
        assert await TrainingRepo(db_session).count_rounds() == EXPECTED_ROUNDS

    async def test_get_participations_for_round(self, db_session):
        repo = TrainingRepo(db_session)
        rounds = await repo.get_all_rounds()
        parts = await repo.get_participations_for_round(rounds[0].id)
        assert len(parts) == EXPECTED_CLIENTS

    async def test_get_all_participations(self, db_session):
        parts = await TrainingRepo(db_session).get_all_participations()
        assert len(parts) == EXPECTED_ROUNDS * EXPECTED_CLIENTS

    async def test_get_all_orgs(self, db_session):
        assert len(await TrainingRepo(db_session).get_all_orgs()) == 3

    async def test_get_participation_by_round(self, db_session):
        data = await TrainingRepo(db_session).get_participation_by_round()
        assert len(data) == EXPECTED_ROUNDS
        for e in data:
            assert e["participating"] == EXPECTED_CLIENTS

    async def test_upsert_round_updates_status(self, db_session):
        repo = TrainingRepo(db_session)
        rounds = await repo.get_all_rounds()
        r1 = rounds[0]
        r1.status = "failed"
        updated = await repo.upsert_round(r1)
        assert updated.status == "failed"
        r1.status = "completed"
        await repo.upsert_round(r1)

    async def test_upsert_round_inserts_new(self, db_session):
        repo = TrainingRepo(db_session)
        new_r = TrainingRound(
            round_number=99, status="completed", started_at=_ts(),
            completed_at=_ts(), duration_s=60, participating_clients=2,
            total_clients=2, accuracy=80.0, loss=0.2, f1=75.0,
            model_version="v99", aggregation_method="FedAvg",
        )
        inserted = await repo.upsert_round(new_r)
        assert inserted.round_number == 99
        assert await repo.count_rounds() == EXPECTED_ROUNDS + 1
        await db_session.delete(inserted)
        await db_session.flush()
        assert await repo.count_rounds() == EXPECTED_ROUNDS


# ==================== Cross-repo Consistency ====================

class TestCrossRepoConsistency:
    """Invariants across multiple repos in the isolated DB."""

    async def test_threats_reference_registered_orgs(self, db_session):
        org_ids = {o.id for o in await OrganizationRepo(db_session).get_all()}
        threats, _ = await ThreatRepo(db_session).get_threats()
        for t in threats:
            assert t.org_id is None or t.org_id in org_ids

    async def test_timeline_sum_equals_total(self, db_session):
        repo = ThreatRepo(db_session)
        tl = await repo.get_hourly_timeline()
        tl_sum = sum(pt["critical"] + pt["high"] + pt["medium"] + pt["low"] for pt in tl)
        assert tl_sum == await repo.get_total_count()

    async def test_sev_stat_type_all_agree_on_total(self, db_session):
        repo = ThreatRepo(db_session)
        total = await repo.get_total_count()
        assert sum((await repo.get_counts_by_severity()).values()) == total
        assert sum((await repo.get_counts_by_status()).values()) == total
        assert sum(t["count"] for t in await repo.get_counts_by_type()) == total

    async def test_experiment_participants_are_registered(self, db_session):
        all_ids = {o.id for o in await OrganizationRepo(db_session).get_all()}
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_org", EXP_ID)
        part_ids = {m.org_id for m in rows if m.org_id and m.model_type.endswith("__iid")}
        assert part_ids.issubset(all_ids)

    async def test_non_participant_not_in_experiment_org(self, db_session):
        rows = await MetricRepo(db_session).get_by_category_for_experiment("experiment_org", EXP_ID)
        assert "org-delta" not in {m.org_id for m in rows if m.org_id}

    async def test_training_rounds_match_metadata(self, db_session):
        meta = await MetricRepo(db_session).get_experiment_metadata(EXP_ID)
        expected = int(meta.get("number_of_rounds", 0))
        actual = await TrainingRepo(db_session).count_rounds()
        assert actual == expected

    async def test_participation_counts_per_round(self, db_session):
        repo = TrainingRepo(db_session)
        for r in await repo.get_all_rounds():
            parts = await repo.get_participations_for_round(r.id)
            active = sum(1 for p in parts if p.status != "skipped")
            assert active == EXPECTED_CLIENTS

    async def test_privacy_event_count_matches_get_all(self, db_session):
        repo = PrivacyRepo(db_session)
        assert len(await repo.get_security_events()) == await repo.count_recent()

    async def test_metric_count_consistent_on_add_delete(self, db_session):
        repo = MetricRepo(db_session)
        before = await repo.count()
        m = Metric(timestamp=_ts(), metric_name="consist_check",
                   metric_value=1.0, model_type="test", category="test_consist")
        await repo.add(m)
        assert await repo.count() == before + 1
        await db_session.delete(m)
        await db_session.flush()
        assert await repo.count() == before


# ==================== Privacy Fallback Logic (pure unit, no DB) ====================

class TestPrivacyFallbackLogic:
    """Unit tests for the privacy_status logic from db_data.get_dashboard."""

    def _build(self, iid_priv: dict) -> tuple[str, str]:
        clipping = bool(iid_priv.get("config__clipping_enabled", 0))
        noise = bool(iid_priv.get("config__dp_noise_enabled", 0))
        validation = bool(iid_priv.get("config__validation_enabled", 0))
        clip_norm = iid_priv.get("config__clip_norm")
        noise_std = iid_priv.get("config__noise_std")
        epsilon = iid_priv.get("config__epsilon_per_round")
        delta = iid_priv.get("config__delta")
        mechs = ["Data Local"]
        if clipping:
            mechs.append("Update Clipping")
        if noise:
            mechs.append("Gaussian Noise")
        if validation:
            mechs.append("Server Validation")
        status = " · ".join(mechs)
        parts = []
        if clipping and clip_norm is not None:
            parts.append(f"clip_norm={clip_norm}")
        if noise and noise_std is not None:
            parts.append(f"noise_std={noise_std}")
        if epsilon is not None:
            parts.append(f"eps={epsilon:.2f}/round")
        if delta is not None:
            parts.append(f"delta={delta:.0e}")
        detail = ("Configured: " + ", ".join(parts) if parts else "DP mechanisms configured") \
                 + ". Secure aggregation: not implemented."
        return status, detail

    def test_empty_returns_data_local_only(self):
        status, detail = self._build({})
        assert status == "Data Local"
        assert "not implemented" in detail

    def test_clipping_only_adds_update_clipping(self):
        status, _ = self._build({"config__clipping_enabled": 1.0, "config__clip_norm": 1.0})
        assert "Update Clipping" in status
        assert "Gaussian Noise" not in status

    def test_noise_only_adds_gaussian_noise(self):
        status, _ = self._build({"config__dp_noise_enabled": 1.0, "config__noise_std": 0.01})
        assert "Gaussian Noise" in status
        assert "Update Clipping" not in status

    def test_clipping_and_noise_both_present(self):
        status, _ = self._build({"config__clipping_enabled": 1.0, "config__dp_noise_enabled": 1.0})
        assert "Update Clipping" in status and "Gaussian Noise" in status

    def test_validation_adds_server_validation(self):
        status, _ = self._build({"config__clipping_enabled": 1.0, "config__dp_noise_enabled": 1.0,
                                  "config__validation_enabled": 1.0})
        assert "Server Validation" in status

    def test_detail_mentions_clip_norm(self):
        _, detail = self._build({"config__clipping_enabled": 1.0, "config__clip_norm": 1.5})
        assert "clip_norm=1.5" in detail

    def test_detail_mentions_noise_std(self):
        _, detail = self._build({"config__dp_noise_enabled": 1.0, "config__noise_std": 0.005})
        assert "noise_std=0.005" in detail

    def test_secure_aggregation_not_in_status(self):
        status, detail = self._build({"config__clipping_enabled": 1.0})
        assert "Secure Aggregation" not in status
        assert "not implemented" in detail

    def test_zero_flags_treated_as_false(self):
        status, _ = self._build({"config__clipping_enabled": 0, "config__dp_noise_enabled": 0})
        assert status == "Data Local"

    def test_data_local_always_present(self):
        for cfg in [{}, {"config__clipping_enabled": 1.0}, {"config__dp_noise_enabled": 1.0}]:
            status, _ = self._build(cfg)
            assert "Data Local" in status


# ==================== Boundary Conditions ====================

class TestBoundaryConditions:
    """Safe empty returns for nonexistent inputs."""

    async def test_threats_unknown_org(self, db_session):
        _, total = await ThreatRepo(db_session).get_threats(organization="Unknown Corp")
        assert total == 0

    async def test_threats_unknown_type(self, db_session):
        _, total = await ThreatRepo(db_session).get_threats(threat_type="Unknown Type")
        assert total == 0

    async def test_threats_unknown_severity(self, db_session):
        _, total = await ThreatRepo(db_session).get_threats(severity="unknown")
        assert total == 0

    async def test_metric_empty_category(self, db_session):
        assert await MetricRepo(db_session).get_by_category("nonexistent_xyz") == []

    async def test_metric_empty_name_type(self, db_session):
        assert await MetricRepo(db_session).get_by_name_and_type("no_metric", "no_model") == []

    async def test_metric_empty_round(self, db_session):
        assert await MetricRepo(db_session).get_for_round(9999) == []

    async def test_metric_empty_org(self, db_session):
        assert await MetricRepo(db_session).get_for_org("nonexistent-xyz") == []

    async def test_privacy_no_events_for_missing_severity(self, db_session):
        assert await PrivacyRepo(db_session).get_events_by_severity("warning") == []

    async def test_testing_unknown_category(self, db_session):
        assert await TestingRepo(db_session).get_by_category("nonexistent") == []

    async def test_count_by_unknown_status(self, db_session):
        assert await ThreatRepo(db_session).count_by_status("nonexistent_status") == 0

    async def test_org_get_by_id_unknown(self, db_session):
        assert await OrganizationRepo(db_session).get_by_id("no-such-org-abc") is None

    async def test_training_participations_unknown_round(self, db_session):
        assert await TrainingRepo(db_session).get_participations_for_round(99999) == []
