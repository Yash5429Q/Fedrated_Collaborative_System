"""Pydantic schemas for the /api/tests endpoint."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


TestResult         = Literal["pass", "fail", "warning", "pending"]
TestExecutionState = Literal["not_run", "mock_run", "executed"]
TestCategory       = Literal[
    "AC-1 Representative Operation",
    "AC-2 Boundary & Failure",
    "AC-3 Independent Acceptance",
    "AC-4 Frozen Resource Envelope",
]


class TestCase(BaseModel):
    id: str
    name: str
    category: TestCategory
    description: str
    expected_result: str
    actual_result: Optional[str]
    status: TestResult
    execution_state: TestExecutionState
    timestamp: Optional[str]
    notes: str


class AcceptanceCriterion(BaseModel):
    code: str
    title: str
    description: str
    tests: List[str]
    passing_threshold: int = Field(ge=0, le=100)


class TestSuiteSummary(BaseModel):
    total: int
    executed: int
    mock_run: int
    not_run: int
    passed: int
    failed: int
    warnings: int
    pending: int
    pass_rate: float


class TestingResponse(BaseModel):
    summary: TestSuiteSummary
    test_cases: List[TestCase]
    acceptance_criteria: List[AcceptanceCriterion]
    data_source: str = "database"
