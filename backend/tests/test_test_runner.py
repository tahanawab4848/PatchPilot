"""Tests for TestRunner (pytest output parsing)."""

from __future__ import annotations

import pytest
from app.schemas.execution import CommandStatus, ExecutionResult, TestOutcome
from app.services.test_runner import TestRunner


@pytest.fixture
def runner() -> TestRunner:
    return TestRunner()


def make_result(stdout: str, stderr: str = "", exit_code: int = 0) -> ExecutionResult:
    status = CommandStatus.success if exit_code == 0 else CommandStatus.failure
    return ExecutionResult(
        command=["python", "-m", "pytest"],
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        status=status,
    )


PYTEST_VERBOSE_OUTPUT = """\
tests/test_calculator.py::test_add_positive PASSED
tests/test_calculator.py::test_subtract PASSED
tests/test_calculator.py::test_divide_by_zero FAILED
tests/test_calculator.py::test_divide_by_zero_message FAILED

FAILED tests/test_calculator.py::test_divide_by_zero - Failed: DID NOT RAISE
FAILED tests/test_calculator.py::test_divide_by_zero_message - Failed: DID NOT RAISE

2 failed, 2 passed in 0.30s
"""

PYTEST_ALL_PASS = """\
tests/test_calculator.py::test_add_positive PASSED
tests/test_calculator.py::test_subtract PASSED

2 passed in 0.10s
"""


def test_parse_passed_and_failed(runner):
    result = make_result(PYTEST_VERBOSE_OUTPUT, exit_code=1)
    run = runner.parse_execution_result(result)
    assert run.passed == 2
    assert run.failed == 2
    assert run.total == 4
    names = {t.name for t in run.tests}
    assert "tests/test_calculator.py::test_divide_by_zero" in names


def test_failure_messages_attached(runner):
    result = make_result(PYTEST_VERBOSE_OUTPUT, exit_code=1)
    run = runner.parse_execution_result(result)
    failing = [t for t in run.tests if t.outcome == TestOutcome.failed]
    assert len(failing) == 2
    assert any("DID NOT RAISE" in (t.message or "") for t in failing)


def test_all_pass(runner):
    result = make_result(PYTEST_ALL_PASS, exit_code=0)
    run = runner.parse_execution_result(result)
    assert run.passed == 2
    assert run.failed == 0
    assert all(t.outcome == TestOutcome.passed for t in run.tests)


def test_empty_output_non_zero_exit(runner):
    result = make_result("", "ModuleNotFoundError: No module named 'src'", exit_code=1)
    run = runner.parse_execution_result(result)
    assert run.errors >= 1
    assert run.tests[0].outcome == TestOutcome.error
    assert "ModuleNotFoundError" in (run.tests[0].message or "")


def test_build_pytest_command(runner):
    cmd = runner.build_pytest_command()
    assert cmd[0] == "python"
    assert "pytest" in cmd
    assert "--tb=short" in cmd


def test_build_pytest_command_rejects_metachar(runner):
    cmd = runner.build_pytest_command(test_paths=["tests/; rm -rf /"])
    # The malicious path should be filtered out
    for arg in cmd:
        assert ";" not in arg
        assert "rm" not in arg


def test_to_summary_dict(runner):
    result = make_result(PYTEST_VERBOSE_OUTPUT, exit_code=1)
    run = runner.parse_execution_result(result)
    summary = runner.to_summary_dict(run)
    assert summary["total"] == 4
    assert summary["passed"] == 2
    assert summary["failed"] == 2
    assert len(summary["failing_tests"]) == 2


def test_jest_runner_parse_json():
    import json
    from app.services.test_runner import JestTestRunner

    jest_runner = JestTestRunner()
    jest_json = {
        "numPassedTests": 2,
        "numFailedTests": 1,
        "numTotalTests": 3,
        "testResults": [
            {
                "testResults": [
                    {"fullName": "adds numbers", "status": "passed", "duration": 12},
                    {"fullName": "subtracts numbers", "status": "passed", "duration": 8},
                    {
                        "fullName": "divides by zero",
                        "status": "failed",
                        "duration": 5,
                        "failureMessages": ["Error: Division by zero expected"],
                    },
                ]
            }
        ],
    }

    result = ExecutionResult(
        command=["npx", "jest", "--json"],
        exit_code=1,
        stdout=json.dumps(jest_json),
        stderr="",
        status=CommandStatus.failure,
    )

    run = jest_runner.parse_execution_result(result)
    assert run.total == 3
    assert run.passed == 2
    assert run.failed == 1
    assert run.framework == "jest"
    failing = [t for t in run.tests if t.outcome == TestOutcome.failed]
    assert len(failing) == 1
    assert failing[0].name == "divides by zero"
    assert "Division by zero" in (failing[0].message or "")


def test_go_test_runner_parse_json():
    import json
    from app.services.test_runner import GoTestRunner

    go_runner = GoTestRunner()
    ndjson = "\n".join([
        json.dumps({"Action": "run", "Test": "TestAdd"}),
        json.dumps({"Action": "pass", "Test": "TestAdd", "Elapsed": 0.01}),
        json.dumps({"Action": "run", "Test": "TestSubtract"}),
        json.dumps({"Action": "pass", "Test": "TestSubtract", "Elapsed": 0.02}),
        json.dumps({"Action": "run", "Test": "TestDivideZero"}),
        json.dumps({"Action": "fail", "Test": "TestDivideZero", "Elapsed": 0.03}),
    ])

    result = ExecutionResult(
        command=["go", "test", "-json", "./..."],
        exit_code=1,
        stdout=ndjson,
        stderr="",
        status=CommandStatus.failure,
    )

    run = go_runner.parse_execution_result(result)
    assert run.total == 3
    assert run.passed == 2
    assert run.failed == 1
    assert run.framework == "go_test"
    failing = [t for t in run.tests if t.outcome == TestOutcome.failed]
    assert len(failing) == 1
    assert failing[0].name == "TestDivideZero"
