"""Pydantic schemas for the /api/system endpoint."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    name: str
    status: Literal["healthy", "degraded", "offline", "unknown"]
    detail: str
    last_checked: str


class SystemResponse(BaseModel):
    status: Literal["healthy", "degraded", "offline"]
    version: str
    environment: str
    uptime_s: int
    components: List[ComponentHealth]
    fl_connected: bool     # False until Flower is integrated
    ml_connected: bool     # False until PyTorch pipeline is integrated
    db_connected: bool
    data_source: str = "database"
