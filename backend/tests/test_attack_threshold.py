"""Regression checks for the optional validation-selected attack gate."""
import numpy as np
import pytest
import torch
from torch.utils.data import DataLoader, TensorDataset
from app.ml.model import (predict_classes, binary_detection_metrics,
                          validate_attack_threshold, select_attack_threshold,
                          test_model_detailed as evaluate_model)


def test_default_preserves_argmax():
    logits = torch.tensor([[0., 1., 0., 0., 0.], [2., 1., 1., 1., 1.]])
    assert torch.equal(predict_classes(logits), logits.argmax(1))


def test_gate_suppresses_only_attack_predictions():
    logits = torch.log(torch.tensor([[.42,.45,.07,.04,.02], [.60,.10,.10,.10,.10], [.01,.96,.01,.01,.01]]))
    assert predict_classes(logits, .8).tolist() == [0, 0, 1]
    assert predict_classes(logits).tolist() == [1, 0, 1]


@pytest.mark.parametrize('bad', [-.1, 1.1, float('nan'), float('inf'), True, '0.8'])
def test_invalid_threshold_rejected(bad):
    with pytest.raises(ValueError):
        validate_attack_threshold(bad)


def test_binary_metrics():
    cm = np.diag([8, 10, 10, 10, 10])
    cm[0, 1] = 2
    cm[1, 0] = 1
    cm[1, 2] = 3
    result = binary_detection_metrics(cm)
    assert result['binary_false_positive_rate'] == 20
    assert result['binary_attack_detection_rate'] == pytest.approx(100 * 43 / 44)
    assert result['binary_fn'] == 1
    assert result['binary_fp'] == 2


def test_validation_selection_and_evaluation_agree():
    probabilities = torch.tensor([[.42,.45,.07,.04,.02], [.80,.05,.05,.05,.05],
                                  [.01,.96,.01,.01,.01], [.01,.01,.96,.01,.01],
                                  [.01,.01,.01,.96,.01], [.01,.01,.01,.01,.96]])
    loader = DataLoader(TensorDataset(probabilities.log(), torch.tensor([0,0,1,2,3,4])), batch_size=2)
    model = torch.nn.Identity()
    rule = select_attack_threshold(model, loader)
    assert rule['selection_split'] == 'validation'
    assert rule['attack_threshold'] is not None
    assert rule['selected']['binary_false_positive_rate'] == 0
    assert rule['selected']['binary_attack_detection_rate'] == 100
    evaluated = evaluate_model(model, loader, attack_threshold=rule['attack_threshold']).to_dict()
    assert evaluated['binary_false_positive_rate'] == 0
    assert evaluated['binary_attack_detection_rate'] == 100


def test_no_improvement_keeps_argmax():
    loader = DataLoader(TensorDataset(torch.eye(5)*10, torch.arange(5)), batch_size=5)
    assert select_attack_threshold(torch.nn.Identity(), loader)['attack_threshold'] is None
