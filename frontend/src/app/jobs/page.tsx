"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, GitBranch, Plus, Repeat2 } from "lucide-react";
import { jobsApi } from "@/lib/api-client";
import { formatDate } from "@/lib/utils";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import type { JobSummary } from "@/types/api";

/** Small outcome badge rendered inline in the job row. */
function OutcomeBadge({ outcome }: { outcome: string }) {
  if (outcome === "verified_fixed" || outcome === "verified") {
    return (
      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-status-success/40 text-status-success bg-status-success/10">
        ✓ Verified Fixed
      </span>
    );
  }
  if (outcome === "fix_failed" || outcome === "failed") {
    return (
      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-status-error/40 text-status-error bg-status-error/10">
        ✗ Fix Failed
      </span>
    );
  }
  return (
    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border/40 text-text-muted bg-surface-2">
      No Change
    </span>
  );
}

/** Compute a human-readable elapsed time from two ISO strings. */
function calcDuration(createdAt: string, updatedAt: string): string | null {
  try {
    const start = new Date(createdAt).getTime();
    const end = new Date(updatedAt).getTime();
    const diffMs = end - start;
    if (diffMs <= 0) return null;
    const totalSeconds = Math.round(diffMs / 1000);
    if (totalSeconds < 60) return `${totalSeconds}s`;
    const m = Math.floor(totalSeconds / 60);
    const s = String(totalSeconds % 60).padStart(2, "0");
    return `${m}m ${s}s`;
  } catch {
    return null;
  }
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    jobsApi
      .list()
      .then(setJobs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Job History</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            All debugging investigations
          </p>
        </div>
        <Button asChild size="sm">
          <Link href="/jobs/new">
            <Plus className="h-3.5 w-3.5" />
            New investigation
          </Link>
        </Button>
      </div>

      {loading && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="h-[72px] rounded-md bg-surface-1 border border-border animate-pulse"
            />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-status-error/30 bg-status-error/10 p-4 text-sm text-status-error">
          {error}
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <div className="rounded-md border border-border bg-surface-1 p-10 text-center">
          <Clock className="h-8 w-8 text-text-muted mx-auto mb-3" />
          <p className="text-sm text-text-secondary mb-4">No investigations yet.</p>
          <Button asChild variant="outline" size="sm">
            <Link href="/jobs/new">Start your first investigation</Link>
          </Button>
        </div>
      )}

      {!loading && jobs.length > 0 && (
        <div className="space-y-1.5">
          {jobs.map((job) => {
            const duration = calcDuration(job.created_at, job.updated_at);
            return (
              <Link
                key={job.id}
                href={`/jobs/${job.id}`}
                className="flex items-center gap-4 rounded-md border border-border bg-surface-1 px-4 py-3 hover:bg-surface-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {/* LEFT: repo + badges */}
                <div className="flex flex-col gap-1 shrink-0 min-w-[180px] max-w-[220px]">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-sm font-semibold text-text-primary truncate">
                      {job.repo_name}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border bg-surface-2 text-text-muted">
                      <GitBranch className="h-2.5 w-2.5 inline-block mr-0.5 -mt-0.5" />
                      {job.repo_source}
                    </span>
                    <StatusBadge status={job.status} />
                  </div>
                </div>

                {/* MIDDLE: bug description */}
                <p className="flex-1 text-xs text-text-secondary truncate min-w-0">
                  {job.bug_description}
                </p>

                {/* RIGHT: date + duration + iterations */}
                <div className="flex flex-col items-end gap-1 shrink-0 text-right">
                  <span className="text-[11px] text-text-muted">
                    {formatDate(job.created_at)}
                  </span>
                  <div className="flex items-center gap-2">
                    {duration && (
                      <span className="text-[10px] font-mono text-text-muted flex items-center gap-0.5">
                        <Clock className="h-2.5 w-2.5" />
                        {duration}
                      </span>
                    )}
                    {job.repair_iterations > 0 && (
                      <span className="text-[10px] font-mono text-text-muted flex items-center gap-0.5">
                        <Repeat2 className="h-2.5 w-2.5" />
                        {job.repair_iterations}x
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
