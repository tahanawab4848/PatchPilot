import { cn } from "@/lib/utils";
import { STATUS_LABELS } from "@/lib/utils";
import type { JobStatus } from "@/types/api";

const STATUS_CONFIG: Record<string, { badge: string; dot: string; pulse?: boolean }> = {
  queued: {
    badge: "border-border/80 text-text-secondary bg-surface-2/70",
    dot: "bg-text-muted",
  },
  analyzing: {
    badge: "border-status-info/40 text-status-info bg-status-info/10",
    dot: "bg-status-info",
    pulse: true,
  },
  reproducing: {
    badge: "border-status-info/40 text-status-info bg-status-info/10",
    dot: "bg-status-info",
    pulse: true,
  },
  diagnosing: {
    badge: "border-accent/40 text-accent bg-accent/10 shadow-glow-sm",
    dot: "bg-accent-bright",
    pulse: true,
  },
  patch_proposed: {
    badge: "border-status-warning/50 text-status-warning bg-status-warning/10",
    dot: "bg-status-warning",
  },
  awaiting_approval: {
    badge: "border-status-warning/60 text-status-warning bg-status-warning/15 animate-pulse-subtle",
    dot: "bg-status-warning",
    pulse: true,
  },
  applying_patch: {
    badge: "border-accent/50 text-accent bg-accent/10",
    dot: "bg-accent",
    pulse: true,
  },
  verifying: {
    badge: "border-status-info/50 text-status-info bg-status-info/10",
    dot: "bg-status-info",
    pulse: true,
  },
  completed: {
    badge: "border-status-success/40 text-status-success bg-status-success/10 shadow-[0_0_12px_-3px_rgba(52,211,153,0.25)]",
    dot: "bg-status-success",
  },
  failed: {
    badge: "border-status-error/40 text-status-error bg-status-error/10",
    dot: "bg-status-error",
  },
  cancelled: {
    badge: "border-border/60 text-text-muted bg-surface-2/50",
    dot: "bg-text-muted/60",
  },
};

interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
  showDot?: boolean;
}

export function StatusBadge({ status, className, showDot = true }: StatusBadgeProps) {
  const conf = STATUS_CONFIG[status] ?? {
    badge: "border-border text-text-secondary bg-surface-2",
    dot: "bg-text-muted",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-mono font-medium tracking-tight transition-colors shadow-inner-glow",
        conf.badge,
        className
      )}
    >
      {showDot && (
        <span className="relative flex h-1.5 w-1.5 shrink-0">
          {conf.pulse && (
            <span
              className={cn(
                "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
                conf.dot
              )}
            />
          )}
          <span className={cn("relative inline-flex rounded-full h-1.5 w-1.5", conf.dot)} />
        </span>
      )}
      <span>{STATUS_LABELS[status] ?? status}</span>
    </span>
  );
}
