"""
Pytest configuration and isolated database fixture for CI and regression tests.

Ensures test reproducibility on clean checkouts without requiring a pre-existing
local cyber20.db file.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.database.session as session_module
import app.models  # noqa: F401 - Register models with Base.metadata
from app.database.init_db import Base
from app.database.seed import seed_if_empty

logger = logging.getLogger(__name__)

# Attempt to reuse existing experiment-saving function from run_experiment.py
try:
    from run_experiment import _save_experiment_results
    _IMPORT_ERROR = None
except ImportError as err:
    _save_experiment_results = None
    _IMPORT_ERROR = err


@pytest.fixture(scope="module", autouse=True)
def isolated_test_database(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Module-scoped fixture providing an isolated temporary SQLite database
    for database-dependent tests (e.g. test_api.py).
    Keeps test_repos_isolated.py, test_predict.py, and test_privacy.py independent.
    """
    # Keep other test modules independent of this database fixture
    if not request.module.__name__.endswith("test_api"):
        yield
        return

    # Check if _save_experiment_results could be safely imported
    if _save_experiment_results is None:
        pytest.fail(
            f"Cannot safely import _save_experiment_results from run_experiment: {_IMPORT_ERROR}"
        )

    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    db_path = Path(temp_db.name)
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    # 1. Setup temporary database using a setup engine and sessionmaker
    async def _setup_db() -> None:
        setup_engine = create_async_engine(
            test_db_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
        setup_sessionmaker = async_sessionmaker(
            bind=setup_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        # Create all tables
        async with setup_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Seed standard demo data (organizations, threats, etc.)
        async with setup_sessionmaker() as session:
            await seed_if_empty(session)

        # Seed historical experiment data from backend/experiment_results.json
        results_file = BACKEND_DIR / "experiment_results.json"
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        exp_id = data["experiment_id"]
        iid_result = data["iid"]
        noniid_result = data["non_iid"]
        args_dict = {
            "alpha": float(noniid_result.get("alpha", 0.5)),
            "rounds": int(iid_result.get("num_rounds", 20)),
            "num_clients": int(iid_result.get("num_clients", 3)),
            "samples": float(
                sum(p["total_samples"] for p in iid_result.get("partition_stats", []))
            ),
            "seed": 42,
            "epochs": int(iid_result.get("local_epochs", 3)),
        }

        # Point AsyncSessionLocal temporarily to setup_sessionmaker for _save_experiment_results
        orig_factory = session_module.AsyncSessionLocal
        session_module.AsyncSessionLocal = setup_sessionmaker
        try:
            await _save_experiment_results(iid_result, noniid_result, exp_id, args_dict)
        finally:
            session_module.AsyncSessionLocal = orig_factory

        await setup_engine.dispose()

    asyncio.run(_setup_db())

    # 2. Configure runtime engine and sessionmaker for test execution
    test_engine = create_async_engine(
        test_db_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    test_sessionmaker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    orig_engine = session_module.engine
    orig_factory = session_module.AsyncSessionLocal

    session_module.engine = test_engine
    session_module.AsyncSessionLocal = test_sessionmaker

    if "app.database.init_db" in sys.modules:
        import app.database.init_db as init_db_module

        init_db_module.engine = test_engine
        init_db_module.AsyncSessionLocal = test_sessionmaker

    try:
        yield
    finally:
        # 3. Teardown: restore module-level references and clean up
        session_module.engine = orig_engine
        session_module.AsyncSessionLocal = orig_factory

        if "app.database.init_db" in sys.modules:
            import app.database.init_db as init_db_module

            init_db_module.engine = orig_engine
            init_db_module.AsyncSessionLocal = orig_factory

        asyncio.run(test_engine.dispose())
        try:
            if db_path.exists():
                db_path.unlink()
        except Exception:
            pass
