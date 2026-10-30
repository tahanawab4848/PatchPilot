import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerificationReport } from "@/features/jobs/VerificationReport";
import type { RepairReport } from "@/types/api";

describe("VerificationReport Component", () => {
  const sampleReport: RepairReport = {
    job_id: "test-job-123",
    outcome: "verified",
    bug_description: "Division by zero crash on zero input",
    diagnosis_summary: "Missing validation for denominator zero check in divide function",
    patch_summary: "Added conditional zero check raising ValueError",
    modified_files: ["app/calculator.py"],
    baseline_test_summary: {
      passed: 3,
      failed: 1,
      failing_tests: ["tests/test_calculator.py::test_divide_zero"],
    },
    post_patch_test_summary: {
      passed: 4,
      failed: 0,
    },
    regression_failures: [],
    commands_executed: ["pytest tests/test_calculator.py"],
    repair_iterations: 1,
    total_duration_seconds: 12.4,
    metrics: {
      patch_syntax_valid: true,
      patch_applies_cleanly: true,
      baseline_reproduced: true,
      failing_tests_fixed: true,
      regression_tests_passed: true,
      no_prohibited_modifications: true,
      sandbox_contained: true,
      total_duration_seconds: 12.4,
    },
    warnings: [],
    limitations: [],
  };

  it("renders verified fix outcome and test matrix", () => {
    render(<VerificationReport report={sampleReport} />);

    expect(screen.getByText(/Outcome: verified/i)).toBeDefined();
    expect(screen.getByText(/All failing baseline tests now pass in the isolated workspace/i)).toBeDefined();
    expect(screen.getByText(/1 failed/i)).toBeDefined();
    expect(screen.getByText(/4 passed/i)).toBeDefined();
    expect(screen.getByText(/tests\/test_calculator\.py::test_divide_zero/i)).toBeDefined();
  });

  it("renders evaluation observability metrics", () => {
    render(<VerificationReport report={sampleReport} />);

    expect(screen.getByText("Evaluation Observability Metrics")).toBeDefined();
    expect(screen.getByText("Bug Reproduced")).toBeDefined();
    expect(screen.getByText("Patch Applied")).toBeDefined();
    expect(screen.getByText("Zero Regressions")).toBeDefined();
  });
});
