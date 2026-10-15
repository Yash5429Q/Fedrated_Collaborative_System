"""
Tests for automatic experiment results seeding.

Validates that:
1. A fresh database automatically receives the CICIDS2017 experiment results.
2. The seeding is idempotent and does not produce duplicate records on repeated calls.
3. Pre-existing experiment data is strictly preserved and never overwritten.
4. Demo seed data and experiment seed data coexist without conflict.
"""
from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 - Register models
from app.database.session import Base
from app.database.seed import seed_experiments_if_empty, seed_if_empty
from app.models.metric import Metric
from app.repositories.metric_repo import MetricRepo


@pytest.fixture
async def async_session():
    """Yields an isolated in-memory SQLite database session for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_experiments_success(async_session: AsyncSession):
    """Verify that seed_experiments_if_empty populates experiment results on a fresh database."""
    repo = MetricRepo(async_session)

    # Before seeding: no experiment should exist
    assert await repo.get_latest_experiment_id() is None

    # Perform seeding
    await seed_experiments_if_empty(async_session)

    # Verify experiment ID is populated
    latest_id = await repo.get_latest_experiment_id()
    assert latest_id == "exp_20261013_042208_6fb2147a"

    # Verify metadata fields via get_experiment_metadata
    metadata = await repo.get_experiment_metadata(latest_id)
    assert metadata["number_of_rounds"] == 20.0
    assert metadata["number_of_clients"] == 3.0
    assert metadata["total_samples"] == 37183.0
    assert metadata["dirichlet_alpha"] == 0.5
    assert metadata["local_epochs"] == 3.0
    assert metadata["dataset"] == "cicids2017"

    # Verify round metrics are populated (20 rounds * 5 metrics * 2 modes = 200 rows)
    round_metrics = await repo.get_by_category_for_experiment("experiment_round", latest_id)
    assert len(round_metrics) > 0
    rounds_seen = {m.round_number for m in round_metrics}
    assert set(range(1, 21)).issubset(rounds_seen)

    # Verify org metrics are populated
    org_metrics = await repo.get_by_category_for_experiment("experiment_org", latest_id)
    assert len(org_metrics) > 0
    org_ids = {m.org_id for m in org_metrics if m.org_id}
    assert {"org-alpha", "org-beta", "org-gamma"}.issubset(org_ids)

    # Verify confusion matrix
    cm_metrics = await repo.get_by_category_for_experiment("confusion_matrix", latest_id)
    assert len(cm_metrics) == 50  # 5x5 classes * 2 modes (iid + noniid)

    # Verify summary metrics
    summary_metrics = await repo.get_by_category_for_experiment("experiment_summary", latest_id)
    assert len(summary_metrics) > 0

    # Verify non-iid scenario metrics
    noniid_metrics = await repo.get_by_category_for_experiment("experiment_noniid", latest_id)
    assert len(noniid_metrics) > 0

    # Verify partition stats
    partition_metrics = await repo.get_by_category_for_experiment("experiment_partition", latest_id)
    assert len(partition_metrics) > 0


@pytest.mark.asyncio
async def test_seed_experiments_idempotent_no_duplicates(async_session: AsyncSession):
    """Verify that calling seed_experiments_if_empty multiple times does not create duplicates."""
    # First seed
    await seed_experiments_if_empty(async_session)

    # Count rows in metric table
    count_result_1 = await async_session.execute(select(func.count(Metric.id)))
    initial_count = count_result_1.scalar_one()
    assert initial_count > 0

    # Second seed call
    await seed_experiments_if_empty(async_session)

    # Count rows again
    count_result_2 = await async_session.execute(select(func.count(Metric.id)))
    count_after_repeat = count_result_2.scalar_one()

    # Third seed call
    await seed_experiments_if_empty(async_session)

    count_result_3 = await async_session.execute(select(func.count(Metric.id)))
    count_after_third = count_result_3.scalar_one()

    assert count_after_repeat == initial_count
    assert count_after_third == initial_count


@pytest.mark.asyncio
async def test_seed_preserves_existing_custom_experiment(async_session: AsyncSession):
    """Verify that existing experiment data is never overwritten or deleted."""
    custom_exp_id = "exp_custom_pre_existing_99999"
    async_session.add(
        Metric(
            timestamp="2026-01-01T00:00:00Z",
            metric_name="experiment_id",
            metric_value=0.0,
            model_type=custom_exp_id,
            category="experiment_metadata",
        )
    )
    async_session.add(
        Metric(
            timestamp="2026-01-01T00:00:00Z",
            metric_name="number_of_rounds",
            metric_value=99.0,
            model_type=custom_exp_id,
            category="experiment_metadata",
        )
    )
    await async_session.commit()

    repo = MetricRepo(async_session)
    assert await repo.get_latest_experiment_id() == custom_exp_id

    # Call seed_experiments_if_empty
    await seed_experiments_if_empty(async_session)

    # Verify latest experiment remains the custom one
    latest_id = await repo.get_latest_experiment_id()
    assert latest_id == custom_exp_id

    # Verify metadata still has custom values
    metadata = await repo.get_experiment_metadata(custom_exp_id)
    assert metadata["number_of_rounds"] == 99.0

    # Verify that the JSON file experiment was not inserted
    default_records = await async_session.execute(
        select(Metric).where(Metric.model_type.like("exp_20261013_042208_6fb2147a%"))
    )
    assert len(default_records.scalars().all()) == 0


@pytest.mark.asyncio
async def test_seed_with_demo_data_coexists(async_session: AsyncSession):
    """Verify that seed_if_empty and seed_experiments_if_empty work together seamlessly."""
    repo = MetricRepo(async_session)

    # Run seed_if_empty (which seeds demo data and legacy summary metrics)
    await seed_if_empty(async_session)

    # At this point, demo data exists, but NO experiment_metadata exists
    assert await repo.get_latest_experiment_id() is None

    # Run seed_experiments_if_empty
    await seed_experiments_if_empty(async_session)

    # Now experiment metadata exists alongside demo data
    assert await repo.get_latest_experiment_id() == "exp_20261013_042208_6fb2147a"
