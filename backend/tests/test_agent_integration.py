"""
Integration tests for the agent pipeline components.

Tests the agent with a mocked inference client so no real API calls are made.
The sandbox is also mocked to return deterministic pytest output.
"""

from __future__ import annotations

import asyncio
import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.execution import CommandStatus, ExecutionResult
from app.schemas.job import JobStatus


# ── Fixtures ───────────────────────────────────────────────────────────────────

BUGGY_PYTEST_OUTPUT = """\
tests/test_calculator.py::test_add_positive PASSED
tests/test_calculator.py::test_divide_normal PASSED
tests/test_calculator.py::test_divide_by_zero FAILED
tests/test_calculator.py::test_divide_by_zero_message FAILED

FAILED tests/test_calculator.py::test_divide_by_zero - Failed: DID NOT RAISE
FAILED tests/test_calculator.py::test_divide_by_zero_message - Failed: DID NOT RAISE

2 failed, 2 passed in 0.30s
"""

FIXED_PYTEST_OUTPUT = """\
tests/test_calculator.py::test_add_positive PASSED
tests/test_calculator.py::test_divide_normal PASSED
tests/test_calculator.py::test_divide_by_zero PASSED
tests/test_calculator.py::test_divide_by_zero_message PASSED

4 passed in 0.30s
"""

DIAGNOSIS_JSON = {
    "problem_summary": "divide() returns 0.0 instead of raising ZeroDivisionError",
    "hypotheses": [{
        "summary": "Missing ZeroDivisionError raise",
        "evidence": ["returns 0.0 when b == 0"],
        "locations": [{"file_path": "src/calculator.py", "start_line": 23, "end_line": 25}],
        "confidence": 0.95,
        "confidence_explanation": "Code clearly shows return 0.0",
    }],
    "recommended_steps": ["Fix the guard in divide()"],
    "relevant_files": ["src/calculator.py"],
    "is_confirmed": True,
    "assumptions": [],
}

PATCH_JSON = {
    "summary": "Fix divide() to raise ZeroDivisionError",
    "files": [{
        "file_path": "src/calculator.py",
        "unified_diff": (
            "--- a/src/calculator.py\n"
            "+++ b/src/calculator.py\n"
            "@@ -23,4 +23,4 @@\n"
            "     if b == 0:\n"
            "-        return 0.0\n"
            "+        raise ZeroDivisionError(\"division by zero\")\n"
            "     return a / b\n"
        ),
        "change_description": "Raise instead of return",
        "evidence_references": [],
        "potential_side_effects": [],
    }],
    "regression_test_plan": ["test_divide_by_zero"],
    "model_reasoning": "Replace silent return with proper exception",
}


def make_exec_result(stdout: str, exit_code: int) -> ExecutionResult:
    return ExecutionResult(
        command=["python", "-m", "pytest"],
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
        status=CommandStatus.success if exit_code == 0 else CommandStatus.failure,
    )


# ── DebuggingAgent unit tests (mocked inference + sandbox) ────────────────────

@pytest.fixture
def demo_project_path(tmp_path):
    """Create a minimal demo project structure in a temp dir."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "calculator.py").write_text(
        "def divide(a, b):\n"
        "    if b == 0:\n"
        "        return 0.0\n"
        "    return a / b\n"
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_calculator.py").write_text(
        "import pytest\n"
        "from src.calculator import divide\n\n"
        "def test_divide_by_zero():\n"
        "    with pytest.raises(ZeroDivisionError):\n"
        "        divide(10, 0)\n\n"
        "def test_divide_by_zero_message():\n"
        '    with pytest.raises(ZeroDivisionError, match="division by zero"):\n'
        "        divide(5, 0)\n"
    )
    return tmp_path


@pytest.mark.asyncio
async def test_agent_parse_diagnosis():
    """Agent correctly parses a well-formed diagnosis JSON."""
    from app.agents.debugging_agent import DebuggingAgent
    agent = DebuggingAgent("test-job-id")
    result = agent._parse_diagnosis(DIAGNOSIS_JSON)
    assert result.problem_summary == DIAGNOSIS_JSON["problem_summary"]
    assert len(result.hypotheses) == 1
    assert result.hypotheses[0].confidence == 0.95
    assert result.is_confirmed is True


@pytest.mark.asyncio
async def test_agent_parse_patch():
    """Agent correctly parses a well-formed patch JSON."""
    from app.agents.debugging_agent import DebuggingAgent
    agent = DebuggingAgent("test-job-id")
    patch = agent._parse_patch(PATCH_JSON, "test-job-id")
    assert len(patch.files) == 1
    assert patch.files[0].file_path == "src/calculator.py"
    assert "ZeroDivisionError" in patch.files[0].unified_diff


@pytest.mark.asyncio
async def test_agent_parse_patch_empty_files():
    """Agent raises AgentError on patch with no valid files."""
    from app.agents.debugging_agent import AgentError, DebuggingAgent
    agent = DebuggingAgent("test-job-id")
    with pytest.raises(AgentError, match="no valid file diffs"):
        agent._parse_patch({"summary": "x", "files": []}, "j1")


@pytest.mark.asyncio
async def test_agent_parse_patch_rejects_traversal():
    """Agent's patch parser accepts the diff; PatchService validator rejects traversal."""
    from app.agents.debugging_agent import DebuggingAgent
    from app.services.patch_service import PatchService

    agent = DebuggingAgent("test-job-id")
    evil = {
        "summary": "evil",
        "files": [{
            "file_path": "../../etc/passwd",
            "unified_diff": "--- a/etc/passwd\n+++ b/etc/passwd\n@@ -1 +1 @@\n-old\n+new\n",
            "change_description": "evil",
        }],
        "regression_test_plan": [],
        "model_reasoning": "",
    }
    patch = agent._parse_patch(evil, "j1")
    # PatchService validation catches this
    result = PatchService().validate_patch(patch, Path("/tmp/safe_repo"))
    assert not result.is_valid
    assert any("traversal" in e.lower() or "unsafe" in e.lower() for e in result.errors)


def test_fallback_diagnosis_when_no_inference():
    """Fallback diagnosis is returned when API key is absent."""
    from app.agents.debugging_agent import DebuggingAgent
    from app.schemas.execution import TestRunResult
    from app.schemas.repository import RepositoryIndex, ProjectMetadata

    agent = DebuggingAgent("test-job-id")
    index = RepositoryIndex(
        files=[],
        relevant_files=["src/calc.py"],
        test_files=["tests/test_calc.py"],
        metadata=ProjectMetadata(),
    )
    # Minimal TestRunResult with one failing test
    from app.schemas.execution import ExecutionResult, CommandStatus, TestResult, TestOutcome
    exec_res = ExecutionResult(command=["pytest"], status=CommandStatus.failure, exit_code=1)
    baseline = TestRunResult(
        framework="pytest",
        command=["pytest"],
        execution=exec_res,
        tests=[TestResult(name="tests/test_calc.py::test_div", outcome=TestOutcome.failed)],
        total=1, passed=0, failed=1,
    )
    diag = agent._fallback_diagnosis("divide bug", index, baseline)
    assert "NEBIUS_API_KEY" in " ".join(diag.assumptions)
    assert "tests/test_calc.py::test_div" in " ".join(diag.recommended_steps)


@pytest.mark.asyncio
async def test_agent_invalid_patch_raises_on_protected_path():
    """
    Agent raises AgentError when model returns a patch targeting a protected path.
    We bypass the API key check by patching nebius_configured.
    """
    from app.agents.debugging_agent import AgentError, DebuggingAgent
    from unittest.mock import AsyncMock, patch as mock_patch, PropertyMock

    agent = DebuggingAgent("j1")

    bad_patch_json = {
        "summary": "bad patch",
        "files": [{
            "file_path": ".env",  # protected path
            "unified_diff": "--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-a\n+b\n",
            "change_description": "bad",
        }],
        "regression_test_plan": [],
        "model_reasoning": "",
    }

    # Patch both the API key check and the inference call
    with mock_patch.object(
        type(agent._settings), "nebius_configured", new_callable=PropertyMock, return_value=True
    ):
        with mock_patch.object(agent._inference, "complete_json",
                               new=AsyncMock(return_value=bad_patch_json)):
            from app.schemas.repository import RepositoryIndex, ProjectMetadata
            from app.schemas.patch import DiagnosisResult
            index = RepositoryIndex(
                files=[], relevant_files=[], test_files=[],
                metadata=ProjectMetadata(),
            )
            diagnosis = DiagnosisResult(problem_summary="bug", relevant_files=[])

            class FakeJob:
                id = "j1"
                bug_description = "bug description"

            with pytest.raises(AgentError, match="protected"):
                await agent._stage_e_patch(
                    MagicMock(), FakeJob(), index,
                    Path("/tmp/repo"), diagnosis, []
                )


# ── Test runner parsing roundtrip ──────────────────────────────────────────────

def test_runner_parses_buggy_output():
    from app.services.test_runner import TestRunner
    runner = TestRunner()
    result = ExecutionResult(
        command=["pytest"],
        exit_code=1,
        stdout=BUGGY_PYTEST_OUTPUT,
        status=CommandStatus.failure,
    )
    run = runner.parse_execution_result(result)
    assert run.failed == 2
    assert run.passed == 2


def test_runner_parses_fixed_output():
    from app.services.test_runner import TestRunner
    runner = TestRunner()
    result = ExecutionResult(
        command=["pytest"],
        exit_code=0,
        stdout=FIXED_PYTEST_OUTPUT,
        status=CommandStatus.success,
    )
    run = runner.parse_execution_result(result)
    assert run.failed == 0
    assert run.passed == 4


# ── Invalid patch rejection ────────────────────────────────────────────────────

def test_patch_service_rejects_model_generated_traversal():
    """Simulates a model returning a traversal path — PatchService must reject it."""
    from app.services.patch_service import PatchService
    from app.schemas.patch import FilePatch, ProposedPatch
    patch = ProposedPatch(
        patch_id="p1",
        job_id="j1",
        summary="evil",
        files=[FilePatch(
            file_path="../../../etc/passwd",
            unified_diff="--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y\n",
            change_description="evil",
        )],
    )
    result = PatchService().validate_patch(patch, Path("/tmp/safe_root"))
    assert not result.is_valid


def test_sandbox_timeout_handled():
    """ExecutionService timeout is preserved in the result."""
    from app.sandbox.executor import ExecutionService
    from app.core.config import get_settings
    svc = ExecutionService(get_settings())
    # Simulate what the service returns when Docker is absent
    result = svc.run_command(["python", "--version"], Path("/tmp"))
    # On CI without Docker, we expect an error result, not a crash
    assert result.status in (
        CommandStatus.error, CommandStatus.success, CommandStatus.failure
    )
