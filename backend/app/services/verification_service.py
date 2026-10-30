"""
VerificationService: compares baseline and post-patch test results and
determines a structured VerificationOutcome.

Decision logic (deterministic, not model-dependent):
- verified:           all failing baseline tests now pass; no regressions.
- partially_verified: some (not all) failing tests pass; no regressions.
- failed:             no failing tests fixed OR new regressions introduced.
- unable_to_verify:   sandbox unavailable or execution errors on both runs.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.schemas.execution import CommandStatus, TestOutcome, TestRunResult
from app.schemas.job import VerificationOutcome
from app.schemas.patch import EvaluationMetrics, RepairReport

log = get_logger(__name__)


class VerificationService:
    def compare(
        self,
        baseline: TestRunResult,
        post_patch: TestRunResult,
        bug_description: str,
        job_id: str,
        patch_summary: str,
        diagnosis_summary: str,
        repair_iterations: int,
        total_duration_seconds: float,
        commands_executed: List[str],
        modified_files: List[str],
        model_failures: int = 0,
        sandbox_failures: int = 0,
        patch_applied_successfully: bool = True,
    ) -> RepairReport:
        """
        Compare two test runs and produce a final RepairReport.
        Never depends on model output to determine outcome.
        """
        baseline_summary = _summarize(baseline)
        post_summary = _summarize(post_patch)
        warnings: List[str] = []
        limitations: List[str] = []

        # Identify which tests were failing before
        baseline_failing = {
            t.name for t in baseline.tests
            if t.outcome in (TestOutcome.failed, TestOutcome.error)
        }
        # Identify which tests are failing after
        post_failing = {
            t.name for t in post_patch.tests
            if t.outcome in (TestOutcome.failed, TestOutcome.error)
        }

        # Tests that were previously passing but now fail = regressions
        baseline_passing = {
            t.name for t in baseline.tests
            if t.outcome == TestOutcome.passed
        }
        regressions = list(post_failing & baseline_passing)

        # Tests that were failing before and now pass = fixed
        fixed = baseline_failing - post_failing

        # Handle execution-level failures
        if post_patch.execution.status in (CommandStatus.error, CommandStatus.timeout):
            outcome = VerificationOutcome.unable_to_verify
            limitations.append(
                f"Post-patch execution did not complete: {post_patch.execution.status.value}"
            )
        elif baseline.execution.status in (CommandStatus.error, CommandStatus.timeout):
            outcome = VerificationOutcome.unable_to_verify
            limitations.append("Baseline execution did not complete; cannot compare.")
        elif regressions:
            outcome = VerificationOutcome.failed
            warnings.append(f"Regressions introduced: {', '.join(regressions[:10])}")
        elif not baseline_failing:
            # No tests were failing to begin with — odd, but report it
            if post_patch.execution.exit_code == 0:
                outcome = VerificationOutcome.partially_verified
                warnings.append(
                    "No failing tests were detected in the baseline. "
                    "Repair may not have been necessary or tests are insufficient."
                )
            else:
                outcome = VerificationOutcome.failed
        elif fixed == baseline_failing:
            outcome = VerificationOutcome.verified
        elif fixed:
            outcome = VerificationOutcome.partially_verified
            still_failing = baseline_failing - fixed
            warnings.append(
                f"Still failing after patch: {', '.join(sorted(still_failing)[:10])}"
            )
        else:
            outcome = VerificationOutcome.failed

        if post_patch.execution.timed_out:
            limitations.append("Post-patch test run timed out.")

        log.info(
            "verification_result",
            job_id=job_id,
            outcome=outcome.value,
            fixed=len(fixed),
            regressions=len(regressions),
            baseline_failing=len(baseline_failing),
        )

        metrics = EvaluationMetrics(
            bug_reproduced=bool(baseline_failing),
            valid_diagnosis_produced=bool(diagnosis_summary.strip()),
            patch_applied_successfully=patch_applied_successfully,
            original_failing_tests_passed=bool(fixed and not (baseline_failing - fixed)),
            regression_tests_passed=len(regressions) == 0,
            repair_iterations=repair_iterations,
            model_failures=model_failures,
            sandbox_failures=sandbox_failures,
            total_duration_seconds=total_duration_seconds,
        )

        return RepairReport(
            job_id=job_id,
            outcome=outcome.value,
            bug_description=bug_description,
            diagnosis_summary=diagnosis_summary,
            patch_summary=patch_summary,
            modified_files=modified_files,
            baseline_test_summary=baseline_summary,
            post_patch_test_summary=post_summary,
            regression_failures=regressions,
            commands_executed=commands_executed,
            repair_iterations=repair_iterations,
            total_duration_seconds=total_duration_seconds,
            metrics=metrics,
            warnings=warnings,
            limitations=limitations,
        )


def _summarize(run: TestRunResult) -> Dict:
    failing = [
        t.name for t in run.tests
        if t.outcome in (TestOutcome.failed, TestOutcome.error)
    ]
    return {
        "total": run.total,
        "passed": run.passed,
        "failed": run.failed,
        "errors": run.errors,
        "skipped": run.skipped,
        "failing_tests": failing[:50],
        "exit_code": run.execution.exit_code,
        "timed_out": run.execution.timed_out,
        "duration_seconds": run.execution.duration_seconds,
    }
