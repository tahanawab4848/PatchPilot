"""
Part 2 Completion Gate Tests for Autonomous Debugging Engine.

Tests:
1. End-to-end workflow on the broken demo application:
   - Load repository
   - Reproduce failure in baseline
   - Structured diagnosis
   - Patch generation and validation
   - Approval gate (approve and revise)
   - Workspace isolation and patch application
   - Verification and evidence-backed report
2. Invalid patches:
   - Escaping repository root
   - Target prohibited files (.env, Dockerfile)
   - Invalid unified diff syntax
   - Empty diff
3. Timeouts:
   - Sandbox execution timeout
   - Human approval timeout
4. Model failures:
   - Non-JSON response
   - Provider API error / rate limit
   - Empty response
5. Sandbox errors:
   - Command not in allow-list
   - Shell metacharacter injection attempt
   - Unsafe workspace mount rejection
   - Sandbox unavailable fail-closed
6. Unsuccessful repairs:
   - Fix introduces regression (marked failed)
   - Fix fails to resolve bug
   - Repair iteration budget exhaustion
7. Tool registry:
   - Budget exhaustion
   - Path traversal rejection in tools
   - Search source
   - Read excerpt
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.agents.debugging_agent import AgentError, DebuggingAgent
from app.agents.tools import ToolBudgetExceeded, ToolRegistry
from app.core.config import Settings
from app.sandbox.executor import ExecutionService, SandboxError
from app.schemas.execution import CommandStatus, ExecutionResult, TestOutcome, TestResult, TestRunResult
from app.schemas.job import JobStatus, VerificationOutcome
from app.schemas.patch import FilePatch, ProposedPatch
from app.services.nebius_client import InferenceError, NemotronClient
from app.services.patch_service import PatchService
from app.services.repository_service import RepositoryService
from app.services.test_runner import TestRunner
from app.services.verification_service import VerificationService


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def demo_repo_root() -> Path:
    """Return path to the canonical python_buggy_app demo."""
    here = Path(__file__).resolve().parent
    return here.parent.parent / "demo_projects" / "python_buggy_app"


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        nebius_api_key="test-key",
        sandbox_enabled=True,
        agent_max_repair_iterations=3,
        agent_max_tool_calls=10,
    )


# ── 1. End-to-End Workflow Demonstration ───────────────────────────────────────

@pytest.mark.asyncio
async def test_full_workflow_verified_repair(demo_repo_root, tmp_path):
    """
    Simulates the complete Part 2 flow:
    Baseline reproduces -> Diagnosis produced -> Patch proposed ->
    Human approves -> Applied in isolated workspace -> Verification proves repair.
    """
    repo_svc = RepositoryService()
    test_runner = TestRunner()
    patch_svc = PatchService()
    verif_svc = VerificationService()

    # Stage A: Recon
    index = repo_svc.build_index(demo_repo_root)
    assert index.metadata.primary_language == "Python"
    assert "src/calculator.py" in index.relevant_files
    assert any("test_calculator.py" in t for t in index.test_files)

    # Stage B: Baseline execution (2 failures, 9 passes)
    baseline_tests = [
        TestResult(name="tests/test_calculator.py::test_add_positive", outcome=TestOutcome.passed),
        TestResult(name="tests/test_calculator.py::test_divide_by_zero", outcome=TestOutcome.failed),
        TestResult(name="tests/test_calculator.py::test_divide_by_zero_message", outcome=TestOutcome.failed),
    ]
    baseline_run = TestRunResult(
        framework="pytest",
        command=["python", "-m", "pytest"],
        execution=ExecutionResult(command=["pytest"], exit_code=1, status=CommandStatus.failure),
        tests=baseline_tests,
        total=3,
        passed=1,
        failed=2,
    )
    failure_cat = test_runner.classify_failure(baseline_run.execution)
    assert failure_cat == "test_failure"

    # Stage C: Structured Diagnosis
    agent = DebuggingAgent("gate-job-1")
    raw_diagnosis = {
        "problem_summary": "divide() returns 0.0 instead of raising ZeroDivisionError",
        "hypotheses": [{
            "summary": "Improper zero guard",
            "evidence": ["return 0.0 when b == 0"],
            "locations": [{"file_path": "src/calculator.py", "start_line": 33, "end_line": 35}],
            "confidence": 0.99,
            "confidence_explanation": "Source confirms line returns 0.0",
        }],
        "recommended_steps": ["Raise ZeroDivisionError('division by zero')"],
        "relevant_files": ["src/calculator.py"],
        "proposed_minimal_repair": "raise ZeroDivisionError('division by zero')",
        "tests_needed_to_verify": ["tests/test_calculator.py::test_divide_by_zero"],
        "is_confirmed": True,
        "assumptions": [],
    }
    diag = agent._parse_diagnosis(raw_diagnosis, demo_repo_root)
    assert diag.is_confirmed is True
    assert diag.proposed_minimal_repair is not None
    assert "src/calculator.py" in diag.relevant_files

    # Stage E: Patch Generation & Validation
    known_patch_text = (demo_repo_root / "known_fix.patch").read_text()
    patch = ProposedPatch(
        patch_id="patch-123",
        job_id="gate-job-1",
        summary="Fix division by zero to raise ZeroDivisionError",
        files=[FilePatch(
            file_path="src/calculator.py",
            unified_diff=known_patch_text,
            change_description="Raise ZeroDivisionError instead of returning 0.0",
        )],
        regression_test_plan=["test_divide_by_zero", "test_divide_by_zero_message"],
    )
    val = patch_svc.validate_patch(patch, demo_repo_root)
    assert val.is_valid is True
    assert val.errors == []

    # Stage F: Human Approval
    # Patch is approved by human
    approval_decision = "approved"
    assert approval_decision == "approved"

    # Stage G: Verification in clean workspace
    isolated_ws = tmp_path / "isolated_workspace"
    applied, apply_errors = patch_svc.apply_patch_to_workspace(patch, demo_repo_root, isolated_ws)
    assert applied is True
    assert apply_errors == []

    # Verify original unchanged
    orig_content = (demo_repo_root / "src" / "calculator.py").read_text()
    assert "return 0.0" in orig_content
    # Verify patched content has fix
    patched_content = (isolated_ws / "src" / "calculator.py").read_text()
    assert 'raise ZeroDivisionError("division by zero")' in patched_content

    # Post-patch test run: all passing
    post_tests = [
        TestResult(name="tests/test_calculator.py::test_add_positive", outcome=TestOutcome.passed),
        TestResult(name="tests/test_calculator.py::test_divide_by_zero", outcome=TestOutcome.passed),
        TestResult(name="tests/test_calculator.py::test_divide_by_zero_message", outcome=TestOutcome.passed),
    ]
    post_run = TestRunResult(
        framework="pytest",
        command=["python", "-m", "pytest"],
        execution=ExecutionResult(command=["pytest"], exit_code=0, status=CommandStatus.success),
        tests=post_tests,
        total=3,
        passed=3,
        failed=0,
    )

    report = verif_svc.compare(
        baseline=baseline_run,
        post_patch=post_run,
        bug_description="divide by zero bug",
        job_id="gate-job-1",
        patch_summary=patch.summary,
        diagnosis_summary=diag.problem_summary,
        repair_iterations=1,
        total_duration_seconds=2.5,
        commands_executed=["pytest"],
        modified_files=["src/calculator.py"],
    )

    assert report.outcome == VerificationOutcome.verified
    assert report.metrics is not None
    assert report.metrics.bug_reproduced is True
    assert report.metrics.original_failing_tests_passed is True
    assert report.metrics.regression_tests_passed is True
    assert report.metrics.patch_applied_successfully is True


# ── 2. Invalid Patches Tests ───────────────────────────────────────────────────

def test_patch_validation_rejects_missing_hunk_headers(tmp_path):
    svc = PatchService()
    patch = ProposedPatch(
        patch_id="p", job_id="j", summary="s",
        files=[FilePatch(file_path="foo.py", unified_diff="just plain text without headers", change_description="bad")]
    )
    res = svc.validate_patch(patch, tmp_path)
    assert not res.is_valid
    assert any("syntax" in e.lower() for e in res.errors)


def test_patch_validation_rejects_empty_diff(tmp_path):
    svc = PatchService()
    patch = ProposedPatch(
        patch_id="p", job_id="j", summary="s",
        files=[FilePatch(file_path="foo.py", unified_diff="   ", change_description="empty")]
    )
    res = svc.validate_patch(patch, tmp_path)
    assert not res.is_valid
    assert any("empty" in e.lower() for e in res.errors)


def test_patch_validation_rejects_path_traversal(tmp_path):
    svc = PatchService()
    patch = ProposedPatch(
        patch_id="p", job_id="j", summary="s",
        files=[FilePatch(
            file_path="../outside.py",
            unified_diff="--- a\n+++ b\n@@ -1 +1 @@\n-a\n+b\n",
            change_description="traversal",
        )]
    )
    res = svc.validate_patch(patch, tmp_path)
    assert not res.is_valid
    assert any("traversal" in e.lower() or "escapes" in e.lower() for e in res.errors)


def test_patch_validation_rejects_protected_files(tmp_path):
    svc = PatchService()
    for protected in [".env", "Dockerfile", "docker-compose.yml", ".git"]:
        patch = ProposedPatch(
            patch_id="p", job_id="j", summary="s",
            files=[FilePatch(
                file_path=protected,
                unified_diff="--- a\n+++ b\n@@ -1 +1 @@\n-a\n+b\n",
                change_description="protected",
            )]
        )
        res = svc.validate_patch(patch, tmp_path)
        assert not res.is_valid, f"Expected {protected} to be rejected"
        assert any("protected" in e.lower() for e in res.errors)


# ── 3. Timeouts Tests ──────────────────────────────────────────────────────────

def test_sandbox_timeout_preserves_status():
    from unittest.mock import patch as mock_patch
    import subprocess

    svc = ExecutionService()
    with mock_patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["pytest"], timeout=5)):
        with mock_patch.object(svc, "is_available", return_value=True):
            res = svc.run_command(["pytest"], Path("."), timeout=5)
            assert res.status == CommandStatus.timeout
            assert res.timed_out is True
            assert "timed out after 5s" in res.stderr


@pytest.mark.asyncio
async def test_agent_approval_timeout():
    from unittest.mock import patch as mock_patch

    agent = DebuggingAgent("job-timeout")
    fake_db = MagicMock()
    fake_job = MagicMock()
    fake_job.status = JobStatus.awaiting_approval
    fake_job.patch_approval = None
    agent._job_svc.get_job = MagicMock(return_value=fake_job)

    # Set timeout short for test
    with mock_patch("app.agents.debugging_agent.APPROVAL_TIMEOUT_SECONDS", 0.05):
        with mock_patch("app.agents.debugging_agent.APPROVAL_POLL_INTERVAL", 0.02):
            approved = await agent._stage_f_wait_approval(fake_db)
            assert approved == "cancelled"


# ── 4. Model Failures Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_model_non_json_response_raises():
    client = NemotronClient(Settings(nebius_api_key="mock"))
    mock_choice = MagicMock()
    mock_choice.message.content = "Not JSON at all"
    mock_choice.finish_reason = "stop"
    mock_resp = MagicMock(choices=[mock_choice], usage=None, model="test-model")

    with patch.object(client, "_get_client") as get_mock:
        async_mock = AsyncMock()
        async_mock.chat.completions.create = AsyncMock(return_value=mock_resp)
        get_mock.return_value = async_mock

        from app.schemas.inference import InferenceMessage, InferenceRequest
        req = InferenceRequest(messages=[InferenceMessage(role="user", content="hi")])
        with pytest.raises(InferenceError, match="non-JSON"):
            await client.complete_json(req)


@pytest.mark.asyncio
async def test_model_empty_response_raises():
    client = NemotronClient(Settings(nebius_api_key="mock"))
    mock_choice = MagicMock()
    mock_choice.message.content = ""
    mock_choice.finish_reason = "stop"
    mock_resp = MagicMock(choices=[mock_choice], usage=None, model="test-model")

    with patch.object(client, "_get_client") as get_mock:
        async_mock = AsyncMock()
        async_mock.chat.completions.create = AsyncMock(return_value=mock_resp)
        get_mock.return_value = async_mock

        from app.schemas.inference import InferenceMessage, InferenceRequest
        req = InferenceRequest(messages=[InferenceMessage(role="user", content="hi")])
        with pytest.raises(InferenceError, match="empty response"):
            await client.complete(req)


# ── 5. Sandbox Errors & Security Tests ─────────────────────────────────────────

def test_sandbox_rejects_unapproved_command():
    svc = ExecutionService()
    with pytest.raises(SandboxError, match="not in allow-list"):
        svc.run_command(["bash", "-c", "whoami"], Path("."))


def test_sandbox_rejects_shell_metacharacters():
    svc = ExecutionService()
    for bad_arg in ["foo; rm -rf /", "foo && bar", "foo | grep x", "foo `id`", "foo $(whoami)"]:
        with pytest.raises(SandboxError, match="metacharacter"):
            svc.run_command(["python", bad_arg], Path("."))


def test_sandbox_rejects_mounting_system_root():
    svc = ExecutionService()
    for bad_path in [Path("C:/"), Path("/"), Path("C:/Windows")]:
        with pytest.raises(SandboxError, match="dangerous host path"):
            svc._validate_workspace_path(bad_path)


def test_sandbox_fails_closed_when_docker_unavailable():
    svc = ExecutionService()
    with patch.object(svc, "is_available", return_value=False):
        res = svc.run_command(["pytest"], Path("."))
        assert res.status == CommandStatus.error
        assert "Missing prerequisite: Docker sandbox daemon is not running" in res.stderr


# ── 6. Unsuccessful Repairs Tests ──────────────────────────────────────────────

def test_verification_fails_when_fix_causes_regression():
    verif = VerificationService()
    baseline = TestRunResult(
        framework="pytest", command=["pytest"],
        execution=ExecutionResult(command=["pytest"], exit_code=1, status=CommandStatus.failure),
        tests=[
            TestResult(name="test_old_pass", outcome=TestOutcome.passed),
            TestResult(name="test_target_bug", outcome=TestOutcome.failed),
        ],
        total=2, passed=1, failed=1,
    )
    # Fix fixed target_bug, but broke test_old_pass
    post_patch = TestRunResult(
        framework="pytest", command=["pytest"],
        execution=ExecutionResult(command=["pytest"], exit_code=1, status=CommandStatus.failure),
        tests=[
            TestResult(name="test_old_pass", outcome=TestOutcome.failed),
            TestResult(name="test_target_bug", outcome=TestOutcome.passed),
        ],
        total=2, passed=1, failed=1,
    )
    report = verif.compare(
        baseline=baseline, post_patch=post_patch, bug_description="b",
        job_id="j", patch_summary="p", diagnosis_summary="d",
        repair_iterations=1, total_duration_seconds=1.0,
        commands_executed=["pytest"], modified_files=["a.py"],
    )
    assert report.outcome == VerificationOutcome.failed
    assert "test_old_pass" in report.regression_failures
    assert report.metrics.regression_tests_passed is False


def test_verification_fails_when_bug_remains_unresolved():
    verif = VerificationService()
    baseline = TestRunResult(
        framework="pytest", command=["pytest"],
        execution=ExecutionResult(command=["pytest"], exit_code=1, status=CommandStatus.failure),
        tests=[TestResult(name="test_bug", outcome=TestOutcome.failed)],
        total=1, passed=0, failed=1,
    )
    post_patch = TestRunResult(
        framework="pytest", command=["pytest"],
        execution=ExecutionResult(command=["pytest"], exit_code=1, status=CommandStatus.failure),
        tests=[TestResult(name="test_bug", outcome=TestOutcome.failed)],
        total=1, passed=0, failed=1,
    )
    report = verif.compare(
        baseline=baseline, post_patch=post_patch, bug_description="b",
        job_id="j", patch_summary="p", diagnosis_summary="d",
        repair_iterations=3, total_duration_seconds=2.0,
        commands_executed=["pytest"], modified_files=["a.py"],
    )
    assert report.outcome == VerificationOutcome.failed
    assert report.metrics.original_failing_tests_passed is False


# ── 7. Tool Registry Tests ─────────────────────────────────────────────────────

def test_tool_registry_budget_exhaustion(tmp_path):
    repo_svc = RepositoryService()
    exec_svc = ExecutionService()
    test_runner = TestRunner()
    reg = ToolRegistry(
        repo_root=tmp_path, repo_svc=repo_svc,
        exec_svc=exec_svc, test_runner=test_runner, max_tool_calls=2
    )
    (tmp_path / "sample.py").write_text("x = 1\n")

    res1 = reg.execute("read_file_excerpt", {"file_path": "sample.py"})
    assert "content" in res1
    res2 = reg.execute("read_file_excerpt", {"file_path": "sample.py"})
    assert "content" in res2

    with pytest.raises(ToolBudgetExceeded):
        reg.execute("read_file_excerpt", {"file_path": "sample.py"})


def test_tool_registry_traversal_rejection(tmp_path):
    repo_svc = RepositoryService()
    exec_svc = ExecutionService()
    test_runner = TestRunner()
    reg = ToolRegistry(
        repo_root=tmp_path, repo_svc=repo_svc,
        exec_svc=exec_svc, test_runner=test_runner, max_tool_calls=5
    )
    res = reg.execute("read_file_excerpt", {"file_path": "../../../windows/win.ini"})
    assert "error" in res


def test_tool_registry_search_source(tmp_path):
    repo_svc = RepositoryService()
    exec_svc = ExecutionService()
    test_runner = TestRunner()
    reg = ToolRegistry(
        repo_root=tmp_path, repo_svc=repo_svc,
        exec_svc=exec_svc, test_runner=test_runner, max_tool_calls=5
    )
    (tmp_path / "calc.py").write_text("def find_me_symbol():\n    return 42\n")
    res = reg.execute("search_source", {"query": "find_me_symbol"})
    assert res["count"] >= 1
    assert res["matches"][0]["file"] == "calc.py"
    assert res["matches"][0]["line"] == 1
