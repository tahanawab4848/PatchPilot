"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import type { JobDetail, JobStatus } from "@/types/api";
import { formatDate } from "@/lib/utils";

const STAGES: { key: JobStatus; label: string }[] = [
  { key: "queued", label: "Queued" },
  { key: "analyzing", label: "Repository analysis" },
  { key: "reproducing", label: "Baseline execution" },
  { key: "diagnosing", label: "Root-cause diagnosis" },
  { key: "patch_proposed", label: "Patch generated" },
  { key: "awaiting_approval", label: "Awaiting approval" },
  { key: "applying_patch", label: "Applying patch" },
  { key: "verifying", label: "Verification" },
  { key: "completed", label: "Completed" },
];

const STAGE_ORDER = STAGES.map((s) => s.key);

function stageIndex(status: JobStatus): number {
  const idx = STAGE_ORDER.indexOf(status);
  return idx === -1 ? 0 : idx;
}

interface JobTimelineProps {
  job: JobDetail;
}

export function JobTimeline({ job }: JobTimelineProps) {
  const current = stageIndex(job.status);
  const isFailed = job.status === "failed" || job.status === "cancelled";

  return (
    <div className="space-y-1">
      {STAGES.map((stage, idx) => {
        const done = idx < current && !isFailed;
        const active = idx === current && !isFailed;
        const failed = isFailed && idx === current;
        const pending = idx > current;

        // Find corresponding event
        const event = job.events.find((e) => e.stage === stage.key);

        return (
          <div key={stage.key} className="flex items-start gap-3 py-1.5 group">
            {/* Icon & connecting line */}
            <div className="relative flex flex-col items-center">
              {done && (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-status-success/15 text-status-success border border-status-success/30 shadow-[0_0_10px_rgba(52,211,153,0.3)]">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                </div>
              )}
              {active && !failed && (
                <div className="relative flex h-5 w-5 items-center justify-center rounded-full bg-accent/20 text-accent border border-accent shadow-glow-sm">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span className="absolute -inset-1 rounded-full bg-accent/20 animate-ping opacity-75" />
                </div>
              )}
              {failed && idx === current && (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-status-error/15 text-status-error border border-status-error/40 shadow-[0_0_10px_rgba(248,113,113,0.3)]">
                  <XCircle className="h-3.5 w-3.5" />
                </div>
              )}
              {pending && (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-surface-2 text-border border border-border/80">
                  <Circle className="h-2.5 w-2.5 text-text-muted/40 fill-text-muted/20" />
                </div>
              )}
              {idx < STAGES.length - 1 && (
                <div
                  className={`w-0.5 h-5 mt-1 transition-colors ${
                    done
                      ? "bg-gradient-to-b from-status-success/50 to-status-success/20"
                      : active
                        ? "bg-gradient-to-b from-accent/50 to-border/40"
                        : "bg-border/40"
                  }`}
                />
              )}
            </div>

            {/* Label */}
            <div className="flex-1 min-w-0 pt-0.5">
              <div className="flex items-baseline justify-between gap-2">
                <span
                  className={`text-xs font-medium transition-colors ${
                    done
                      ? "text-text-primary"
                      : active
                        ? "text-accent font-semibold"
                        : failed && idx === current
                          ? "text-status-error font-semibold"
                          : "text-text-muted"
                  }`}
                >
                  {stage.label}
                </span>
                {event?.created_at && (
                  <span className="text-[10px] text-text-muted shrink-0 font-mono">
                    {formatDate(event.created_at)}
                  </span>
                )}
              </div>
              {event?.message && (
                <p className="text-[11px] text-text-secondary mt-0.5 truncate font-mono">
                  {event.message}
                </p>
              )}
            </div>
          </div>
        );
      })}

      {/* Failed/cancelled extra info */}
      {isFailed && job.error_message && (
        <div className="mt-3 rounded-lg border border-status-error/40 bg-status-error/10 p-3 text-xs text-status-error shadow-xs">
          <div className="font-semibold mb-1 flex items-center gap-1.5">
            <XCircle className="h-3.5 w-3.5" />
            Execution Failure
          </div>
          {job.error_message}
        </div>
      )}
    </div>
  );
}
