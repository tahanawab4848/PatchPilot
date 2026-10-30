import { cn } from "@/lib/utils";
import { STATUS_LABELS } from "@/lib/utils";
import type { JobStatus } from "@/types/api";

const STATUS_STYLE: Record<string, string> = {
  queued: "border-border/60 text-text-secondary bg-surface-2",
  analyzing: "border-status-info/40 text-status-info bg-status-info/10 animate-pulse-subtle",
  reproducing: "border-status-info/40 text-status-info bg-status-info/10 animate-pulse-subtle",
  diagnosing: "border-status-info/40 text-status-info bg-status-info/10 animate-pulse-subtle",
  patch_proposed: "border-status-warning/40 text-status-warning bg-status-warning/10",
  awaiting_approval: "border-status-warning/40 text-status-warning bg-status-warning/10",
  applying_patch: "border-accent/40 text-accent bg-accent/10 animate-pulse-subtle",
  verifying: "border-accent/40 text-accent bg-accent/10 animate-pulse-subtle",
  completed: "border-status-success/40 text-status-success bg-status-success/10",
  failed: "border-status-error/40 text-status-error bg-status-error/10",
  cancelled: "border-border/40 text-text-muted bg-surface-2",
};

interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-1.5 py-0.5 text-xs font-mono font-medium",
        STATUS_STYLE[status] ?? "border-border text-text-secondary",
        className
      )}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}
