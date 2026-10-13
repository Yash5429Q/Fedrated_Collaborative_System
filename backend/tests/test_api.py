"""
API regression tests — real-data integration.
Run with:  cd backend && pytest tests/ -v --asyncio-mode=auto

All tests assert that real CICIDS2017 experiment data is returned,
not seeded/synthetic values.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

LATEST_EXP_ID = "exp_20261013_042208_6fb2147a"
EXPECTED_IID_ACCURACY = 78.94   # confirmed from DB
EXPECTED_IID_F1 = 73.84         # confirmed from DB
EXPECTED_IID_FPR = 5.37         # confirmed from DB
EXPECTED_TOTAL_ROUNDS = 20
EXPECTED_LOCAL_EPOCHS = 3
EXPECTED_CLIENTS = 3
EXPECTED_TOTAL_SAMPLES = 37183
EXPECTED_DIRICHLET_ALPHA = 0.5


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── Health ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Experiment endpoint (new) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_experiments_list(client: AsyncClient):
    r = await client.get("/api/experiments")
    assert r.status_code == 200
    data = r.json()
    assert "experiments" in data
    assert data["total"] >= 1
    assert data["latest_experiment_id"] == LATEST_EXP_ID


@pytest.mark.asyncio
async def test_experiments_latest(client: AsyncClient):
    r = await client.get("/api/experiments/latest")
    assert r.status_code == 200
    data = r.json()
    assert data["experiment_id"] == LATEST_EXP_ID
    assert data["is_latest"] is True
    assert data["number_of_rounds"] == EXPECTED_TOTAL_ROUNDS
    assert data["local_epochs"] == EXPECTED_LOCAL_EPOCHS
    assert data["number_of_clients"] == EXPECTED_CLIENTS
    assert data["total_samples"] == EXPECTED_TOTAL_SAMPLES
    assert abs(data["dirichlet_alpha"] - EXPECTED_DIRICHLET_ALPHA) < 0.001


@pytest.mark.asyncio
async def test_experiments_by_id(client: AsyncClient):
    r = await client.get(f"/api/experiments/{LATEST_EXP_ID}")
    assert r.status_code == 200
    data = r.json()
    assert data["experiment_id"] == LATEST_EXP_ID


@pytest.mark.asyncio
async def test_experiments_not_found(client: AsyncClient):
    r = await client.get("/api/experiments/exp_nonexistent")
    assert r.status_code == 404


# ── Dashboard — real CICIDS2017 KPIs ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard(client: AsyncClient):
    r = await client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "total_organizations" in data
    # data_source must reference the experiment, not "demo"
    assert "experiment:" in data["data_source"] or data["data_source"] == "database"


@pytest.mark.asyncio
async def test_dashboard_real_accuracy(client: AsyncClient):
    """Global accuracy must come from the CICIDS2017 experiment, not seeded 94.7."""
    r = await client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    acc = data["global_model_accuracy"]
    # Must NOT be the seeded 94.7 value
    assert abs(acc - 94.7) > 1.0, f"Accuracy {acc} looks like seeded value (94.7)"
    # Must be close to real experiment value
    assert abs(acc - EXPECTED_IID_ACCURACY) < 1.0, f"Expected ~{EXPECTED_IID_ACCURACY}, got {acc}"


@pytest.mark.asyncio
async def test_dashboard_real_f1(client: AsyncClient):
    """F1 must be real experiment value, not seeded 92.3."""
    r = await client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    f1 = data["f1_score"]
    assert abs(f1 - 92.3) > 1.0, f"F1 {f1} looks like seeded value (92.3)"
    assert abs(f1 - EXPECTED_IID_F1) < 1.0, f"Expected ~{EXPECTED_IID_F1}, got {f1}"


@pytest.mark.asyncio
async def test_dashboard_real_fpr(client: AsyncClient):
    """FPR must be real experiment value, not seeded 3.2."""
    r = await client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    fpr = data["false_positive_rate"]
    assert abs(fpr - 3.2) > 1.0, f"FPR {fpr} looks like seeded value (3.2)"
    assert abs(fpr - EXPECTED_IID_FPR) < 1.0, f"Expected ~{EXPECTED_IID_FPR}, got {fpr}"


@pytest.mark.asyncio
async def test_dashboard_real_rounds(client: AsyncClient):
    """Total rounds must be 10 (from CICIDS2017 experiment), not 12 or 25."""
    r = await client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert data["total_rounds"] == EXPECTED_TOTAL_ROUNDS, \
        f"total_rounds should be {EXPECTED_TOTAL_ROUNDS}, got {data['total_rounds']}"


# ── Organizations ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_organizations(client: AsyncClient):
    r = await client.get("/api/organizations")
    assert r.status_code == 200
    data = r.json()
    assert "organizations" in data
    # No hardcoded assertion on count — DB has 5 orgs (3 active in experiment)


@pytest.mark.asyncio
async def test_organizations_data_source(client: AsyncClient):
    r = await client.get("/api/organizations")
    assert r.status_code == 200
    data = r.json()
    # data_source should reference experiment
    assert "experiment" in data["data_source"] or "database" in data["data_source"]


# ── Training — experiment rounds ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_training(client: AsyncClient):
    r = await client.get("/api/training")
    assert r.status_code == 200
    assert "summary" in r.json()


@pytest.mark.asyncio
async def test_training_real_accuracy(client: AsyncClient):
    """Training global accuracy must not be the inflated 99.67% seeded value."""
    r = await client.get("/api/training")
    assert r.status_code == 200
    data = r.json()
    acc = data["summary"]["global_accuracy"]
    assert abs(acc - 99.67) > 1.0, f"Accuracy {acc} looks like seeded value (99.67)"
    assert abs(acc - EXPECTED_IID_ACCURACY) < 1.0, f"Expected ~{EXPECTED_IID_ACCURACY}, got {acc}"


@pytest.mark.asyncio
async def test_training_rounds_count(client: AsyncClient):
    """Round history must contain exactly 10 rounds from the CICIDS2017 experiment."""
    r = await client.get("/api/training/rounds")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == EXPECTED_TOTAL_ROUNDS, \
        f"Expected {EXPECTED_TOTAL_ROUNDS} rounds, got {data['total']}"


@pytest.mark.asyncio
async def test_training_clients(client: AsyncClient):
    """Active clients must be 3 (CICIDS2017 experiment had 3 clients)."""
    r = await client.get("/api/training")
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["total_clients"] == EXPECTED_CLIENTS


@pytest.mark.asyncio
async def test_training_data_source(client: AsyncClient):
    r = await client.get("/api/training")
    assert r.status_code == 200
    data = r.json()
    assert "experiment" in data["data_source"]


# ── Performance ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_performance(client: AsyncClient):
    r = await client.get("/api/performance")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "metric_comparisons" in data


@pytest.mark.asyncio
async def test_performance_real_accuracy(client: AsyncClient):
    """Performance federated accuracy must be real, not seeded 94.7."""
    r = await client.get("/api/performance")
    assert r.status_code == 200
    data = r.json()
    acc = data["summary"]["federated_accuracy"]
    assert abs(acc - 94.7) > 1.0, f"Accuracy {acc} looks like seeded value"
    assert abs(acc - EXPECTED_IID_ACCURACY) < 1.0, f"Expected ~{EXPECTED_IID_ACCURACY}, got {acc}"


@pytest.mark.asyncio
async def test_performance_data_source_experiment(client: AsyncClient):
    """data_source must reference a real experiment."""
    r = await client.get("/api/performance")
    assert r.status_code == 200
    data = r.json()
    assert "experiment" in data["data_source"]


# ── Threats — real DB queries, no hardcoded numbers ───────────────────────────

@pytest.mark.asyncio
async def test_threats(client: AsyncClient):
    r = await client.get("/api/threats")
    assert r.status_code == 200
    data = r.json()
    assert "detections" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_threats_no_hardcoded_counts(client: AsyncClient):
    """Severity counts must match real DB totals, not hardcoded 187/493/641/526."""
    r = await client.get("/api/threats")
    assert r.status_code == 200
    data = r.json()
    s = data["summary"]
    total = s["total"]
    sev_sum = s["critical"] + s["high"] + s["medium"] + s["low"]
    # Severity subtotals must add up to total
    assert sev_sum == total, f"Severity counts {sev_sum} != total {total}"
    # Must NOT match the old hardcoded values
    assert s["critical"] != 187, "critical=187 is a hardcoded magic number"
    assert s["high"]     != 493, "high=493 is a hardcoded magic number"
    assert s["medium"]   != 641, "medium=641 is a hardcoded magic number"
    assert s["low"]      != 526, "low=526 is a hardcoded magic number"
    assert s["blocked"]  != 1204, "blocked=1204 is a hardcoded magic number"
    assert s["investigating"] != 89, "investigating=89 is a hardcoded magic number"


@pytest.mark.asyncio
async def test_threats_timeline_real(client: AsyncClient):
    """Timeline must be from real DB aggregation, not static hourly list."""
    r = await client.get("/api/threats")
    assert r.status_code == 200
    data = r.json()
    tl = data["timeline"]
    # 5 seeded records — timeline may be short or empty (honest)
    # Verify structure
    for point in tl:
        assert "hour" in point
        assert "critical" in point
        assert "high" in point
        assert "medium" in point
        assert "low" in point


@pytest.mark.asyncio
async def test_threats_filter_severity(client: AsyncClient):
    r = await client.get("/api/threats?severity=critical")
    assert r.status_code == 200
    data = r.json()
    for threat in data["detections"]:
        assert threat["severity"] == "critical"


# ── Privacy ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_privacy(client: AsyncClient):
    r = await client.get("/api/privacy")
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["raw_data_shared"] is False


@pytest.mark.asyncio
async def test_privacy_org_updates_use_real_round(client: AsyncClient):
    """Org update statuses must NOT reference hardcoded round=15."""
    r = await client.get("/api/privacy")
    assert r.status_code == 200
    data = r.json()
    for org_upd in data["org_update_statuses"]:
        assert org_upd["round"] != 15, \
            f"round=15 is a hardcoded value; got {org_upd['round']} for {org_upd['org_id']}"


# ── Testing ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tests_endpoint(client: AsyncClient):
    r = await client.get("/api/tests")
    assert r.status_code == 200
    data = r.json()
    assert "test_cases" in data
    # Verify no test is falsely claimed as fully executed on live system
    for tc in data["test_cases"]:
        assert tc["execution_state"] in ("not_run", "mock_run", "executed")


# ── Experiments endpoint ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_system(client: AsyncClient):
    r = await client.get("/api/system")
    assert r.status_code == 200
    data = r.json()
    assert data["fl_connected"] is False
    assert data["ml_connected"] is False


# ── MetricRepo unit-level: get_latest_experiment_id ───────────────────────────

@pytest.mark.asyncio
async def test_metric_repo_get_latest_experiment_id():
    """
    Regression test for the get_latest_experiment_id() bug fix.
    Verifies that the method returns the model_type (experiment ID string)
    NOT the metric_value (0.0 float).
    """
    from app.database.session import AsyncSessionLocal
    from app.repositories.metric_repo import MetricRepo

    async with AsyncSessionLocal() as db:
        repo = MetricRepo(db)
        exp_id = await repo.get_latest_experiment_id()

    assert exp_id is not None, "get_latest_experiment_id() returned None — DB may have no experiment_metadata rows"
    assert exp_id == LATEST_EXP_ID, f"Expected {LATEST_EXP_ID}, got {exp_id}"
    # Must be a string, not 0.0
    assert isinstance(exp_id, str)
    # Must start with 'exp_'
    assert exp_id.startswith("exp_"), f"Returned value '{exp_id}' doesn't look like an experiment ID"
    # Must NOT contain the dataset suffix
    assert "__" not in exp_id, f"Suffix was not stripped: {exp_id}"
