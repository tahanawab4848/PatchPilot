import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/StatusBadge";

describe("StatusBadge", () => {
  it("renders the correct label for queued", () => {
    render(<StatusBadge status="queued" />);
    expect(screen.getByText("Queued")).toBeInTheDocument();
  });

  it("renders completed with success styling", () => {
    const { container } = render(<StatusBadge status="completed" />);
    expect(container.firstChild).toHaveClass("text-status-success");
  });

  it("renders failed with error styling", () => {
    const { container } = render(<StatusBadge status="failed" />);
    expect(container.firstChild).toHaveClass("text-status-error");
  });

  it("renders awaiting_approval label", () => {
    render(<StatusBadge status="awaiting_approval" />);
    expect(screen.getByText("Awaiting Approval")).toBeInTheDocument();
  });
});
