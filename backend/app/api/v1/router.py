"""
Central router — aggregates all v1 sub-routers.
Import this single router into main.py.
"""
from fastapi import APIRouter, Depends
from app.core.access import require_access

from app.api.v1 import (
    dashboard,
    organizations,
    training,
    threats,
    performance,
    privacy,
    tests,
    system,
    predict,
    experiments,
)

router = APIRouter(dependencies=[Depends(require_access)])

router.include_router(dashboard.router)
router.include_router(organizations.router)
router.include_router(training.router)
router.include_router(threats.router)
router.include_router(performance.router)
router.include_router(privacy.router)
router.include_router(tests.router)
router.include_router(system.router)
router.include_router(predict.router)
router.include_router(experiments.router)


@router.get("/api/access/session")
def access_session(role: str = Depends(require_access)):
    return {"role": role}


@router.get("/api/predict/samples")
def benchmark_samples(role: str = Depends(require_access)):
    from fastapi import HTTPException
    from app.ml.inference import get_inference_model
    from app.ml.data import CLASS_NAMES, FEATURE_NAMES, create_benchmark_splits
    if role != "operator":
        raise HTTPException(403, "Operator permission required")
    inf = get_inference_model()
    if not inf.is_loaded or not inf.has_normalization or (inf.metadata or {}).get("experiment_id") != "exp_20261125_173246_9acfd8aa":
        raise HTTPException(503, "Frozen demonstration checkpoint unavailable")
    try:
        splits = create_benchmark_splits(seed=42)
        if len(splits["y_test"]) != 5575:
            raise ValueError("Unexpected benchmark split size")
        samples = []
        for c, label in enumerate(CLASS_NAMES):
            i = next(i for i, y in enumerate(splits["y_test"]) if int(y) == c)
            samples.append({"label": label, "test_index": i, "features": splits["X_test"][i].tolist()})
        return {"experiment_id": inf.metadata["experiment_id"], "seed": 42, "feature_names": list(FEATURE_NAMES), "samples": samples}
    except (ValueError, OSError, KeyError, StopIteration):
        raise HTTPException(503, "Benchmark samples unavailable") from None
