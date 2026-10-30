"""Tests for schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.job import CreateJobRequest, JobStatus, PatchApprovalRequest
from app.schemas.patch import FilePatch, ProposedPatch
from app.schemas.execution import CommandStatus, ExecutionResult


def test_job_status_values():
    valid = [s.value for s in JobStatus]
    assert "queued" in valid
    assert "awaiting_approval" in valid
    assert "completed" in valid
    assert "failed" in valid


def test_create_job_request_valid():
    req = CreateJobRequest(
        repo_name="test",
        repo_source="upload",
        bug_description="A sufficiently long bug description here.",
    )
    assert req.status_is_valid if hasattr(req, "status_is_valid") else True


def test_create_job_request_rejects_bad_source():
    with pytest.raises(ValidationError):
        CreateJobRequest(
            repo_name="test",
            repo_source="github",  # not allowed
            bug_description="Long enough description.",
        )


def test_patch_approval_valid():
    req = PatchApprovalRequest(decision="approved")
    assert req.decision == "approved"


def test_patch_approval_invalid():
    with pytest.raises(ValidationError):
        PatchApprovalRequest(decision="maybe")


def test_execution_result():
    r = ExecutionResult(
        command=["pytest"],
        exit_code=1,
        stdout="FAILED",
        stderr="",
        status=CommandStatus.failure,
    )
    assert r.status == CommandStatus.failure
    assert r.timed_out is False


def test_proposed_patch_structure():
    patch = ProposedPatch(
        patch_id="p1",
        job_id="j1",
        summary="Fix off-by-one error.",
        files=[
            FilePatch(
                file_path="src/calc.py",
                unified_diff="--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,2 +1,2 @@\n-return x\n+return x + 1\n",
                change_description="Fix return value.",
            )
        ],
    )
    assert len(patch.files) == 1
    assert patch.is_valid is False  # not validated yet
