"""Regression tests for explicit prediction alert recording in an isolated database."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import importlib

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import app.models
from app.database import session as session_module
from app.models.threat_detection import ThreatDetection
from app.models.privacy_event import PrivacyEvent
from app.repositories.threat_repo import ThreatRepo
from app.repositories.privacy_repo import PrivacyRepo
from app.services.db_data import get_threats

predict_api = importlib.import_module("app.api.v1.predict")
EXPERIMENT = "exp_test_prediction_alerts"


def fake_result(class_id=1):
    return {
        "prediction": {"class_id": class_id, "label": predict_api.CLASS_NAMES[class_id], "confidence": 0.9},
        "probabilities": {name: 0.9 if i == class_id else 0.025 for i, name in enumerate(predict_api.CLASS_NAMES)},
        "model": {"name": "ThreatNet", "input_features": 68, "classes": 5, "experiment_id": EXPERIMENT, "normalization": True},
    }


@pytest_asyncio.fixture
async def alert_env(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'alerts.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(session_module.Base.metadata.create_all)
    async with factory() as db:
        db.add(ThreatDetection(id="td-001", timestamp="2026-08-31T11:24:12Z", threat_type="DoS", severity="critical", status="blocked", confidence=99, organization_name="Demo"))
        db.add(PrivacyEvent(id="sec-001", timestamp="2026-08-31T11:30:00Z", event_type="Demo", category="Access Control", severity="warning", status="resolved"))
        await db.commit()
    monkeypatch.setattr(session_module, "AsyncSessionLocal", factory)
    monkeypatch.setattr(predict_api, "get_inference_model", lambda: SimpleNamespace(is_loaded=True, has_normalization=True, metadata={"experiment_id": EXPERIMENT, "best_round": 6}))
    monkeypatch.setattr(predict_api, "predict", lambda features: fake_result())
    app = FastAPI()
    app.include_router(predict_api.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_alert_recording_and_demo_separation(alert_env):
    client, factory = alert_env
    async with factory() as db:
        data = await get_threats(db)
        assert data.total == data.summary.total == 0
        assert data.historical_demo_count == 1
    response = await client.post("/api/predict", json={"features": [0.0]*68, "record_alert": True})
    assert response.status_code == 200, response.text
    alert_id = response.json()["alert_id"]
    assert alert_id.startswith("pred-") and len(alert_id) == 32
    async with factory() as db:
        data = await get_threats(db)
        assert data.total == data.summary.total == 1
        assert data.summary.blocked == 0 and data.summary.medium == 1
        assert data.historical_demo_count == 1
        assert data.timeline[0].medium == 1 and len(data.timeline[0].hour) == 17
        row = data.detections[0]
        assert row.id == alert_id and row.status == "detected" and row.confidence == 90
        assert row.raw_features == {} and row.source_ip == row.destination_ip == row.protocol == ""
        assert row.organization_id == "" and row.port == 0 and EXPERIMENT in row.description
        assert await ThreatRepo(db).get_total_count() == 2
        assert (await get_threats(db, threat_type="Malware")).total == 0
        assert (await get_threats(db, threat_type="DoS")).total == 1


@pytest.mark.asyncio
async def test_default_prediction_does_not_record(alert_env):
    client, factory = alert_env
    response = await client.post("/api/predict", json={"features": [0.0]*68})
    assert response.status_code == 200 and response.json()["alert_id"] is None
    async with factory() as db:
        assert await ThreatRepo(db, scope="predictions").get_total_count() == 0


@pytest.mark.asyncio
async def test_normal_and_invalid_requests_do_not_record(alert_env, monkeypatch):
    client, factory = alert_env
    monkeypatch.setattr(predict_api, "predict", lambda features: fake_result(0))
    r = await client.post("/api/predict", json={"features": [0.0]*68, "record_alert": True})
    assert r.status_code == 200 and r.json()["alert_id"] is None
    for body in ({"features": [0.0]*67, "record_alert": True}, {"features": [False]+[0.0]*67, "record_alert": True}, {"features": [0.0]*68, "record_alert": "true"}):
        r = await client.post("/api/predict", json=body)
        assert r.status_code in (400, 422)
    async with factory() as db:
        assert await ThreatRepo(db, scope="predictions").get_total_count() == 0


@pytest.mark.asyncio
async def test_inconsistent_model_identity_does_not_record(alert_env, monkeypatch):
    client, factory = alert_env
    result = fake_result()
    result["model"]["experiment_id"] = "different"
    monkeypatch.setattr(predict_api, "predict", lambda features: result)
    r = await client.post("/api/predict", json={"features": [0.0]*68, "record_alert": True})
    assert r.status_code == 503
    async with factory() as db:
        assert await ThreatRepo(db, scope="predictions").get_total_count() == 0


@pytest.mark.asyncio
async def test_security_demo_exclusion_and_recent_window(alert_env):
    _, factory = alert_env
    now = datetime.now(timezone.utc)
    async with factory() as db:
        for eid, stamp in [("new-event", now-timedelta(hours=1)), ("old-event", now-timedelta(hours=25)), ("future-event", now+timedelta(hours=1))]:
            db.add(PrivacyEvent(id=eid, timestamp=stamp.isoformat(), event_type="Test", category="Test", severity="info", status="open"))
        await db.commit()
        repo = PrivacyRepo(db)
        events = await repo.get_security_events(include_demo=False)
        assert {e.id for e in events} == {"new-event", "old-event", "future-event"}
        assert repo.count_last_24h(events, now=now) == 1
