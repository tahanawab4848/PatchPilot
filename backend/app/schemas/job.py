"""
Job lifecycle schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    queued = "queued"
    analyzing = "analyzing"
    reproducing = "reproducing"
    diagnosing = "diagnosing"
    patch_proposed = "patch_proposed"
    awaiting_approval = "awaiting_approval"
    applying_patch = "applying_patch"
    verifying = "verifying"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class VerificationOutcome(str, Enum):
    verified = "verified"
    partially_verified = "partially_verified"
    failed = "failed"
    unable_to_verify = "unable_to_verify"


class PatchApproval(str, Enum):
    approved = "approved"
    rejected = "rejected"
    revised = "revised"
    cancelled = "cancelled"


class JobEventSchema(BaseModel):
    id: str
    job_id: str
    created_at: datetime
    stage: str
    status: str
    details: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

    model_config = {"from_attributes": True}


class JobSummary(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    repo_name: str
    repo_source: str
    bug_description: str
    status: JobStatus
    repair_iterations: int

    model_config = {"from_attributes": True}


class JobDetail(JobSummary):
    project_metadata: Optional[Dict[str, Any]] = None
    proposed_patch: Optional[str] = None
    nemotron_critique: Optional[Dict[str, Any]] = None
    nebius_telemetry: Optional[Dict[str, Any]] = None
    reasoning_log: Optional[str] = None
    patch_approval: Optional[PatchApproval] = None
    patch_feedback: Optional[str] = None
    repair_report: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    events: List[JobEventSchema] = []

    model_config = {"from_attributes": True}


class CreateJobRequest(BaseModel):
    repo_name: str = Field(..., min_length=1, max_length=255)
    repo_source: str = Field(..., pattern="^(upload|demo)$")
    archive_path: Optional[str] = Field(None, max_length=1024)
    bug_description: str = Field(..., min_length=10, max_length=4000)


class PatchApprovalRequest(BaseModel):
    decision: PatchApproval
    notes: Optional[str] = Field(None, max_length=2000)
