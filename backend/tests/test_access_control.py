import hashlib
import json
import time
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import get_settings

@pytest.fixture
def registry(tmp_path, monkeypatch):
    path = tmp_path / 'access.json'
    monkeypatch.setattr(get_settings(), 'access_registry_path', str(path))
    def write(revoked=False):
        rows = {token: {'role': role, 'expires_at': time.time()+offset, 'revoked': rev} for token, role, offset, rev in [
            ('viewer-test', 'viewer', 600, False), ('operator-test', 'operator', 600, revoked), ('expired-test', 'operator', -1, False)]}
        path.write_text(json.dumps({hashlib.sha256(k.encode()).hexdigest(): v for k,v in rows.items()}))
    write()
    return write

@pytest.mark.asyncio
@pytest.mark.parametrize('token,status', [(None,401), ('wrong',401), ('expired-test',401), ('viewer-test',200), ('operator-test',200)])
async def test_read_permissions(registry, token, status):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        r = await c.get('/api/predict/health', headers={} if token is None else {'Authorization': 'Bearer '+token})
        assert r.status_code == status
        assert r.headers['cache-control'] == 'no-store'

@pytest.mark.asyncio
async def test_viewer_cannot_predict(registry):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        r = await c.post('/api/predict', headers={'Authorization':'Bearer viewer-test'}, json={'features':[0.0]*68,'record_alert':True})
        assert r.status_code == 403
        r = await c.post('/api/predict', headers={'Authorization':'Bearer operator-test'}, json={})
        assert r.status_code == 422

@pytest.mark.asyncio
async def test_revocation_rechecked(registry):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test', headers={'Authorization':'Bearer operator-test'}) as c:
        assert (await c.get('/api/predict/health')).status_code == 200
        registry(True)
        assert (await c.get('/api/predict/health')).status_code == 401
        assert (await c.post('/api/predict', json={'features':[0.0]*68})).status_code == 401

@pytest.mark.asyncio
async def test_all_read_routes_require_token(registry):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        for path in ('dashboard','organizations','training','training/rounds','threats','performance','privacy','tests','system','experiments','experiments/latest','experiments/example','predict/health'):
            assert (await c.get('/api/'+path)).status_code == 401, path
        assert (await c.get('/health')).status_code == 200
        assert (await c.post('/api/predict', json={})).status_code == 401


@pytest.mark.asyncio
async def test_session_role_and_samples_permissions(registry):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        assert (await c.get('/api/access/session')).status_code == 401
        assert (await c.get('/api/predict/samples')).status_code == 401
        for role in ('viewer', 'operator'):
            headers = {'Authorization': 'Bearer '+role+'-test'}
            response = await c.get('/api/access/session', headers=headers)
            assert response.status_code == 200
            assert response.json() == {'role': role}
        assert (await c.get('/api/predict/samples', headers={'Authorization':'Bearer viewer-test'})).status_code == 403

@pytest.mark.asyncio
async def test_samples_are_held_out_raw_features(registry, monkeypatch):
    from types import SimpleNamespace
    from app.ml import inference
    from app.ml.data import create_benchmark_splits, CLASS_NAMES, FEATURE_NAMES
    import numpy as np
    monkeypatch.setattr(inference, 'get_inference_model', lambda: SimpleNamespace(
        is_loaded=True, has_normalization=True, metadata={'experiment_id':'exp_20261125_173246_9acfd8aa'}))
    splits = create_benchmark_splits(seed=42)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test', headers={'Authorization':'Bearer operator-test'}) as c:
        response = await c.get('/api/predict/samples')
        assert response.status_code == 200
        data = response.json()
        assert data['seed'] == 42 and data['feature_names'] == list(FEATURE_NAMES)
        assert [sample['label'] for sample in data['samples']] == list(CLASS_NAMES)
        for class_id, sample in enumerate(data['samples']):
            i = sample['test_index']
            assert int(splits['y_test'][i]) == class_id
            np.testing.assert_array_equal(sample['features'], splits['X_test'][i])
