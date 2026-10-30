"""Tests for VerificationService comparison logic."""

from __future__ import annotations

import pytest
from app.schemas.execution import CommandStatus, ExecutionResult, TestOutcome, TestRunResult
from app.schemas.job import VerificationOutcome
from app.services.test_runner import TestRunner
from app.services.verification_service import VerificationService


def make_run(passed_names, failed_names, exit_code=None):
    tests = []
    for n in passed_names:
        tests.append(
            __import__("app.schemas.execution", fromlist=["TestResult"]).TestResult(
                name=n, outcome=TestOutcome.passed
            )
        )
    for n in failed_names:
        tests.append(
            __import__("app.schemas.execution", fromlist=["TestResult"]).TestResult(
                name=n, outcome=TestOutcome.failed
            )
        )
    if exit_code is None:
        exit_code = 1 if failed_names else 0
    status = CommandStatus.failure if failed_names else CommandStatus.success
    exec_result = ExecutionResult(
        command=["pytest"],
        exit_code=exit_code,
        status=status,
    )
    return TestRunResult(
        framework="pytest",
        command=["pytest"],
        execution=exec_result,
        tests=tests,
        total=len(tests),
        passed=len(passed_names),
        failed=len(failed_names),
    )


@pytest.fixture
def svc():
    return VerificationService()


COMMON_KWARGS = dict(
    bug_description="Bug",
    job_id="job1",
    patch_summary="Fix divide",
    diagnosis_summary="Divide returns 0",
    repair_iterations=1,
    total_duration_seconds=5.0,
    commands_executed=["pytest"],
    modified_files=["src/calc.py"],
)


def test_verified_when_all_failing_tests_fixed(svc):
    baseline = make_run(["test_pass"], ["test_fail"])
    post_patch = make_run(["test_pass", "test_fail"], [])
    report = svc.compare(baseline=baseline, post_patch=post_patch, **COMMON_KWARGS)
    assert report.outcome == VerificationOutcome.verified
    assert report.regression_failures == []


def test_partially_verified_when_some_fixed(svc):
    baseline = make_run(["test_pass"], ["test_fail_a", "test_fail_b"])
    post_patch = make_run(["test_pass", "test_fail_a"], ["test_fail_b"])
    report = svc.compare(baseline=baseline, post_patch=post_patch, **COMMON_KWARGS)
    assert report.outcome == VerificationOutcome.partially_verified


def test_failed_when_no_tests_fixed(svc):
    baseline = make_run(["test_pass"], ["test_fail"])
    post_patch = make_run(["test_pass"], ["test_fail"])  # still failing
    report = svc.compare(baseline=baseline, post_patch=post_patch, **COMMON_KWARGS)
    assert report.outcome == VerificationOutcome.failed


def test_failed_with_regression(svc):
    baseline = make_run(["test_pass", "test_other"], ["test_fail"])
    # Fixed target but broke test_other
    post_patch = make_run(["test_fail"], ["test_pass", "test_other"])
    report = svc.compare(baseline=baseline, post_patch=post_patch, **COMMON_KWARGS)
    assert report.outcome == VerificationOutcome.failed
    assert "test_other" in report.regression_failures or "test_pass" in report.regression_failures


def test_unable_to_verify_on_sandbox_error(svc):
    baseline = make_run(["test_pass"], ["test_fail"])
    exec_result = ExecutionResult(
        command=["pytest"],
        status=CommandStatus.error,
        stderr="Docker not available",
    )
    post_patch = TestRunResult(
        framework="pytest",
        command=["pytest"],
        execution=exec_result,
        tests=[],
        total=0,
        passed=0,
        failed=0,
    )
    report = svc.compare(baseline=baseline, post_patch=post_patch, **COMMON_KWARGS)
    assert report.outcome == VerificationOutcome.unable_to_verify
    assert report.limitations


def test_report_fields(svc):
    baseline = make_run([], ["test_fail"])
    post_patch = make_run(["test_fail"], [])
    report = svc.compare(baseline=baseline, post_patch=post_patch, **COMMON_KWARGS)
    assert report.job_id == "job1"
    assert report.repair_iterations == 1
    assert report.modified_files == ["src/calc.py"]
    assert report.baseline_test_summary is not None
    assert report.post_patch_test_summary is not None
