import json
import numpy as np
import pytest
import torch
from app.ml import inference as inf
from app.ml.data import FEATURE_NAMES, CLASS_NAMES
from app.ml.model import ThreatNet

@pytest.fixture
def valid_checkpoint(tmp_path, monkeypatch):
    latest = tmp_path / 'latest'
    latest.mkdir()
    torch.save(ThreatNet().state_dict(), latest / 'global_model.pt')
    (latest / 'metadata.json').write_text(json.dumps({'experiment_id':'test', 'input_features':68, 'num_classes':5, 'class_mapping':{str(i): n for i,n in enumerate(CLASS_NAMES)}}))
    np.savez(latest / 'normalization.npz', mean=np.zeros(68), std=np.ones(68), feature_names=np.array(FEATURE_NAMES))
    monkeypatch.setattr(inf, '_LATEST_DIR', latest)
    monkeypatch.setattr(inf, '_MODELS_DIR', tmp_path)
    return latest

def test_explicit_missing_never_falls_back(valid_checkpoint):
    m = inf._InferenceModel()
    assert m.load()
    assert not m.load(str(valid_checkpoint.parent / 'missing'))
    assert not m.is_loaded and m.model is None and m.metadata is None
    assert not m.has_normalization and m.checkpoint_path is None

def test_default_never_scans_history(valid_checkpoint):
    valid_checkpoint.rename(valid_checkpoint.parent / 'historical')
    m = inf._InferenceModel()
    assert not m.load()
    assert not m.is_loaded

def test_wrong_class_mapping_rejected(valid_checkpoint):
    path = valid_checkpoint / 'metadata.json'
    meta = json.loads(path.read_text())
    meta['class_mapping']['0'] = 'Malware'
    path.write_text(json.dumps(meta))
    m = inf._InferenceModel()
    assert not m.load()
    assert 'class mapping' in m.load_error
