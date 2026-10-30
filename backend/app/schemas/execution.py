"""
Sandbox execution schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CommandStatus(str, Enum):
    success = "success"
    failure = "failure"
    timeout = "timeout"
    error = "error"
    blocked = "blocked"


class ExecutionResult(BaseModel):
    command: List[str]
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    status: CommandStatus
    timed_out: bool = False
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class TestOutcome(str, Enum):
    passed = "passed"
    failed = "failed"
    error = "error"
    skipped = "skipped"


class TestResult(BaseModel):
    name: str
    outcome: TestOutcome
    duration_seconds: Optional[float] = None
    message: Optional[str] = None  # failure message or error traceback


class TestRunResult(BaseModel):
    framework: str
    command: List[str]
    execution: ExecutionResult
    tests: List[TestResult] = []
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    run_at: Optional[datetime] = None
