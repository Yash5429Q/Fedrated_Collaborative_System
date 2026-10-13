"""
Central router — aggregates all v1 sub-routers.
Import this single router into main.py.
"""
from fastapi import APIRouter

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

router = APIRouter()

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
