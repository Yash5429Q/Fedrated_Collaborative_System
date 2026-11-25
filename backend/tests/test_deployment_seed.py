"""Cloud startup metric selection; isolated mocks, no production DB writes."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core import config
from app.database import seed


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    root = Path(seed.__file__).resolve().parents[2]
    meta = json.loads((root / 'models/latest/metadata.json').read_text(encoding='utf-8'))
    exp_id = meta['experiment_id']
    result = json.loads((root / f'{exp_id}_results.json').read_text(encoding='utf-8'))
    meta_path = tmp_path / 'models/latest/metadata.json'
    meta_path.parent.mkdir(parents=True)
    meta_path.write_text(json.dumps(meta), encoding='utf-8')
    result_path = tmp_path / f'{exp_id}_results.json'
    result_path.write_text(json.dumps(result), encoding='utf-8')
    (tmp_path / 'experiment_results.json').write_text('{"experiment_id":"wrong_legacy"}', encoding='utf-8')
    monkeypatch.setattr(seed, '__file__', str(tmp_path / 'app/database/seed.py'))
    monkeypatch.setattr(config, 'get_settings', lambda: SimpleNamespace(environment='production'))
    repo = SimpleNamespace(get_latest_experiment_id=AsyncMock(return_value=None), get_experiment_metadata=AsyncMock(return_value={}))
    monkeypatch.setattr(seed, 'MetricRepo', lambda db: repo)
    db = SimpleNamespace(add_all=Mock(), commit=AsyncMock())
    return meta, result, meta_path, result_path, repo, db


@pytest.mark.asyncio
async def test_fresh_cloud_seed_matches_checkpoint(deployment):
    meta, result, _, _, _, db = deployment
    await seed.seed_experiments_if_empty(db)
    rows = db.add_all.call_args.args[0]
    assert len(rows) == 791
    mode = result['exported_mode']
    assert mode == meta['mode'] == 'non_iid'
    metadata = {r.metric_name: r.metric_value for r in rows if r.category == 'experiment_metadata'}
    assert metadata['deployed_non_iid'] == 1
    accuracy = [r.metric_value for r in rows if r.category == 'experiment_summary' and r.model_type == meta['experiment_id'] + '__non_iid' and r.metric_name == 'accuracy']
    assert accuracy == [94.48]
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_matching_existing_database_not_reseeded(deployment):
    meta, _, _, _, repo, db = deployment
    repo.get_latest_experiment_id.return_value = meta['experiment_id']
    repo.get_experiment_metadata.return_value = {'deployed_non_iid': 1.0}
    await seed.seed_experiments_if_empty(db)
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cloud_refuses_old_database(deployment):
    _, _, _, _, repo, db = deployment
    repo.get_latest_experiment_id.return_value = 'exp_old'
    with pytest.raises(RuntimeError, match='does not match'):
        await seed.seed_experiments_if_empty(db)
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cloud_refuses_missing_matching_results(deployment):
    _, _, _, result_path, _, db = deployment
    result_path.unlink()
    with pytest.raises(RuntimeError, match='Results for deployed checkpoint are missing'):
        await seed.seed_experiments_if_empty(db)
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cloud_refuses_mismatched_checkpoint_settings(deployment):
    meta, _, meta_path, _, _, db = deployment
    meta['decision_rule']['attack_threshold'] = 0.5
    meta_path.write_text(json.dumps(meta), encoding='utf-8')
    with pytest.raises(RuntimeError, match='settings do not match'):
        await seed.seed_experiments_if_empty(db)
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()
