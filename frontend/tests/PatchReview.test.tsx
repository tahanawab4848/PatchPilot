import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PatchReview } from "@/features/jobs/PatchReview";
import { jobsApi } from "@/lib/api-client";
import type { JobDetail } from "@/types/api";

// Mock jobsApi
vi.mock("@/lib/api-client", () => ({
  jobsApi: {
    approve: vi.fn().mockResolvedValue({ status: "success" }),
  },
}));

describe("PatchReview Component", () => {
  const sampleDiff = `diff --git a/app/calculator.py b/app/calculator.py
--- a/app/calculator.py
+++ b/app/calculator.py
@@ -1,3 +1,3 @@
 def divide(a, b):
-    return a / b
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
+    return a / b
`;

  const mockJob: JobDetail = {
    id: "test-job-456",
    repo_name: "calculator-service",
    repo_source: "demo",
    bug_description: "Division by zero crashes application",
    status: "awaiting_approval",
    repair_iterations: 1,
    proposed_patch: sampleDiff,
    events: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  it("renders diff statistics and action controls", () => {
    render(
      <PatchReview
        job={mockJob}
        onDecision={vi.fn()}
      />
    );

    expect(screen.getByText("Approve Patch")).toBeDefined();
    expect(screen.getByText("Reject")).toBeDefined();
    expect(screen.getByText("Request Revision")).toBeDefined();
    expect(screen.getByText("Unified Diff")).toBeDefined();
  });

  it("submits approval when Approve Patch is clicked", async () => {
    const handleDecision = vi.fn();
    render(
      <PatchReview
        job={mockJob}
        onDecision={handleDecision}
      />
    );

    fireEvent.click(screen.getByText("Approve Patch"));

    await waitFor(() => {
      expect(jobsApi.approve).toHaveBeenCalledWith("test-job-456", {
        decision: "approved",
        notes: undefined,
      });
      expect(handleDecision).toHaveBeenCalledTimes(1);
    });
  });

  it("submits rejection when Reject is clicked", async () => {
    const handleDecision = vi.fn();
    render(
      <PatchReview
        job={mockJob}
        onDecision={handleDecision}
      />
    );

    fireEvent.click(screen.getByText("Reject"));

    await waitFor(() => {
      expect(jobsApi.approve).toHaveBeenCalledWith("test-job-456", {
        decision: "rejected",
        notes: undefined,
      });
      expect(handleDecision).toHaveBeenCalledTimes(1);
    });
  });
});
