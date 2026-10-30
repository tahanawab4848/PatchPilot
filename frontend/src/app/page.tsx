"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Bug,
  CheckCircle2,
  Clock,
  Cpu,
  FileCode,
  Flame,
  FlaskConical,
  RefreshCw,
  Search,
  ShieldCheck,
  Terminal,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { jobsApi, repositoriesApi } from "@/lib/api-client";
import { useHealth } from "@/hooks/useHealth";
import { formatDate } from "@/lib/utils";
import type { JobSummary } from "@/types/api";

export default function HomePage() {
  const { health, loading: healthLoading } = useHealth();
  const [recentJobs, setRecentJobs] = useState<JobSummary[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

  useEffect(() => {
    let mounted = true;
    jobsApi
      .list(5, 0)
      .then((jobs) => {
        if (mounted) setRecentJobs(jobs);
      })
      .catch(() => {})
      .finally(() => {
        if (mounted) setLoadingJobs(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const dbOk = health?.database.ok ?? false;
  const modelOk = health?.nebius.configured ?? false;
  const sandboxOk = health?.sandbox.available ?? false;

  return (
    <div className="flex flex-col min-h-full p-8 max-w-5xl mx-auto space-y-10">
      {/* Hero Workbench Header */}
      <div className="pt-2">
        <div className="mb-3 flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded border border-accent/30 bg-accent/10 px-2 py-0.5 text-[11px] font-mono font-medium text-accent">
            <Cpu className="h-3 w-3" />
            NVIDIA Nemotron · Nebius Token Factory
          </span>
          <span className="text-xs text-text-muted font-mono">
            Autonomous Debugging & Verification Engine
          </span>
        </div>

        <h1 className="text-3xl font-semibold text-text-primary tracking-tight font-sans">
          From failing tests to verified fixes.
        </h1>
        <p className="mt-2 text-sm text-text-secondary max-w-2xl leading-relaxed">
          PatchPilot reproduces code failures inside isolated sandboxes, requests structured
          root-cause diagnoses and minimal patches from NVIDIA Nemotron, waits for your explicit review,
          and validates repairs with real test runs.
        </p>

        {/* Primary Call-to-Actions */}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button asChild size="default" className="gap-2 bg-accent text-surface hover:bg-accent-bright font-medium">
            <Link href="/jobs/new">
              Start new debugging job
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>

          <Button variant="outline" asChild className="gap-2 border-border hover:bg-surface-2 text-text-primary">
            <Link href="/demo">
              <FlaskConical className="h-4 w-4 text-accent" />
              Launch bundled demo (python_buggy_app)
            </Link>
          </Button>
        </div>

        {/* Real-time readiness status bar */}
        <div className="mt-6 inline-flex flex-wrap items-center gap-4 rounded-md border border-border bg-surface-1 px-3 py-2 text-xs">
          <span className="text-[11px] font-mono text-text-muted uppercase tracking-wider">
            Engine Readiness:
          </span>
          <ReadinessPill
            label="Postgres/SQLite"
            ready={dbOk}
            loading={healthLoading}
          />
          <ReadinessPill
            label="NVIDIA Nemotron (Nebius)"
            ready={modelOk}
            loading={healthLoading}
            info="Llama-3.1-Nemotron-70B"
          />
          <ReadinessPill
            label="Docker Sandbox"
            ready={sandboxOk}
            loading={healthLoading}
            optional
          />
        </div>
      </div>

      {/* Visual Workflow Pipeline (Compact, Information-Dense) */}
      <div>
        <div className="flex items-center justify-between mb-3 border-b border-border pb-2">
          <h2 className="text-xs font-mono uppercase tracking-wider text-text-muted font-medium">
            Deterministic Repair Pipeline (Stages A → G)
          </h2>
          <span className="text-[11px] font-mono text-text-muted">
            Zero Simulated Results · Real Test Execution
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <StageCard
            num="A·B"
            title="Recon & Reproduce"
            desc="Indexes files, prunes secrets, and isolates failing tests in non-root Docker."
            icon={Search}
          />
          <StageCard
            num="C·D"
            title="Diagnose & Inspect"
            desc="Nemotron hypothesizes root causes; bounded tools search source code."
            icon={Bug}
          />
          <StageCard
            num="E·F"
            title="Patch & Review Gate"
            desc="Generates unified diff. Requires explicit human approval before any change is applied."
            icon={Wrench}
            highlight
          />
          <StageCard
            num="G"
            title="Sandbox Verification"
            desc="Tests re-run in isolated workspace copy; reports verified fix vs regression."
            icon={CheckCircle2}
          />
        </div>
      </div>

      {/* Recent Investigations */}
      <div>
        <div className="flex items-center justify-between mb-3 border-b border-border pb-2">
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 text-text-muted" />
            <h2 className="text-xs font-mono uppercase tracking-wider text-text-muted font-medium">
              Recent Investigations
            </h2>
          </div>
          <Link
            href="/jobs"
            className="text-xs font-mono text-accent hover:underline flex items-center gap-1"
          >
            View all jobs
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {loadingJobs ? (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-12 w-full animate-pulse rounded border border-border bg-surface-1"
              />
            ))}
          </div>
        ) : recentJobs.length === 0 ? (
          <div className="rounded border border-dashed border-border p-6 text-center text-xs text-text-muted">
            No investigations yet. Launch the bundled demo project or start a new job.
          </div>
        ) : (
          <div className="divide-y divide-border rounded border border-border bg-surface-1 overflow-hidden">
            {recentJobs.map((j) => (
              <Link
                key={j.id}
                href={`/jobs/${j.id}`}
                className="flex items-center justify-between p-3 text-xs hover:bg-surface-2 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <StatusBadge status={j.status} />
                  <div className="truncate">
                    <span className="font-semibold text-text-primary mr-2">
                      {j.repo_name}
                    </span>
                    <span className="text-text-secondary truncate">
                      {j.bug_description.slice(0, 60)}…
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-text-muted shrink-0 font-mono text-[11px]">
                  <span>{formatDate(j.created_at)}</span>
                  <ArrowRight className="h-3 w-3" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ReadinessPill({
  label,
  ready,
  loading,
  optional = false,
  info,
}: {
  label: string;
  ready: boolean;
  loading: boolean;
  optional?: boolean;
  info?: string;
}) {
  if (loading) {
    return (
      <span className="flex items-center gap-1.5 text-text-muted">
        <span className="h-2 w-2 rounded-full bg-text-muted animate-pulse" />
        <span>{label}</span>
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1.5 font-mono text-[11px]">
      <span
        className={`h-2 w-2 rounded-full ${
          ready
            ? "bg-status-success"
            : optional
              ? "bg-status-warning"
              : "bg-status-error"
        }`}
      />
      <span className={ready ? "text-text-primary" : "text-text-muted"}>
        {label}
      </span>
      {info && (
        <span className="text-[10px] text-text-muted">({info})</span>
      )}
    </span>
  );
}

function StageCard({
  num,
  title,
  desc,
  icon: Icon,
  highlight = false,
}: {
  num: string;
  title: string;
  desc: string;
  icon: React.ElementType;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-md border p-3.5 transition-colors ${
        highlight
          ? "border-accent/40 bg-accent/5 shadow-xs"
          : "border-border bg-surface-1 hover:border-border/80"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono font-medium uppercase text-accent">
          Stage {num}
        </span>
        <Icon className="h-4 w-4 text-text-muted" />
      </div>
      <h3 className="text-xs font-semibold text-text-primary mb-1">{title}</h3>
      <p className="text-[11px] text-text-secondary leading-snug">{desc}</p>
    </div>
  );
}
