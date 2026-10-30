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
    <div className="space-y-0.5">
      {STAGES.map((stage, idx) => {
        const done = idx < current && !isFailed;
        const active = idx === current && !isFailed;
        const failed = isFailed && idx === current;
        const pending = idx > current;

        // Find corresponding event
        const event = job.events.find((e) => e.stage === stage.key);

        return (
          <div key={stage.key} className="flex items-start gap-3 py-1.5">
            {/* Icon */}
            <div className="relative flex flex-col items-center">
              {done && (
                <CheckCircle2 className="h-4 w-4 text-status-success mt-0.5" />
              )}
              {active && !failed && (
                <Loader2 className="h-4 w-4 text-accent mt-0.5 animate-spin" />
              )}
              {failed && idx === current && (
                <XCircle className="h-4 w-4 text-status-error mt-0.5" />
              )}
              {pending && (
                <Circle className="h-4 w-4 text-border mt-0.5" />
              )}
              {idx < STAGES.length - 1 && (
                <div
                  className={`w-px h-4 mt-0.5 ${
                    done ? "bg-status-success/30" : "bg-border"
                  }`}
                />
              )}
            </div>

            {/* Label */}
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2">
                <span
                  className={`text-xs font-medium ${
                    done
                      ? "text-text-primary"
                      : active
                        ? "text-accent"
                        : failed && idx === current
                          ? "text-status-error"
                          : "text-text-muted"
                  }`}
                >
                  {stage.label}
                </span>
                {event?.created_at && (
                  <span className="text-[10px] text-text-muted shrink-0">
                    {formatDate(event.created_at)}
                  </span>
                )}
              </div>
              {event?.message && (
                <p className="text-[11px] text-text-secondary mt-0.5 truncate">
                  {event.message}
                </p>
              )}
            </div>
          </div>
        );
      })}

      {/* Failed/cancelled extra info */}
      {isFailed && job.error_message && (
        <div className="mt-2 rounded-sm border border-status-error/30 bg-status-error/10 p-2 text-xs text-status-error">
          {job.error_message}
        </div>
      )}
    </div>
  );
}
