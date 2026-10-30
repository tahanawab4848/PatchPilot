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
    <div className="flex flex-col min-h-full p-8 max-w-5xl mx-auto space-y-10 animate-fade-in">
      {/* Hero Workbench Header with Ambient Glow */}
      <div className="relative pt-2 pb-4">
        {/* Ambient background aura */}
        <div className="pointer-events-none absolute -top-12 left-1/4 h-64 w-96 -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />

        <div className="relative">
          <div className="mb-3.5 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-[11px] font-mono font-medium text-accent shadow-glow-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
              </span>
              <Cpu className="h-3.5 w-3.5" />
              NVIDIA Nemotron · Nebius Token Factory
            </span>
            <span className="text-xs text-text-muted font-mono tracking-tight">
              Autonomous Debugging & Verification Engine
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-text-primary font-sans">
            From failing tests to <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent via-accent-bright to-status-info">verified fixes</span>.
          </h1>
          <p className="mt-3 text-sm text-text-secondary max-w-2xl leading-relaxed">
            PatchPilot reproduces code failures inside isolated sandboxes, requests structured
            root-cause diagnoses and minimal patches from NVIDIA Nemotron, waits for your explicit review,
            and validates repairs with real test runs.
          </p>

          {/* Primary Call-to-Actions */}
          <div className="mt-7 flex flex-wrap items-center gap-3.5">
            <Button asChild size="default" className="gap-2 font-medium">
              <Link href="/jobs/new">
                Start new debugging job
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>

            <Button variant="outline" asChild className="gap-2">
              <Link href="/demo">
                <FlaskConical className="h-4 w-4 text-accent" />
                Launch bundled demo (python_buggy_app)
              </Link>
            </Button>
          </div>

          {/* Real-time readiness status bar */}
          <div className="mt-7 inline-flex flex-wrap items-center gap-4 rounded-lg border border-border/80 bg-surface-1/90 px-3.5 py-2.5 text-xs shadow-inner-glow backdrop-blur-xs">
            <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider font-semibold">
              Engine Readiness:
            </span>
            <ReadinessPill
              label="Postgres/SQLite"
              ready={dbOk}
              loading={healthLoading}
            />
            <div className="h-3 w-px bg-border/60" />
            <ReadinessPill
              label="NVIDIA Nemotron (Nebius)"
              ready={modelOk}
              loading={healthLoading}
              info="Llama-3.1-Nemotron-70B"
            />
            <div className="h-3 w-px bg-border/60" />
            <ReadinessPill
              label="Docker Sandbox"
              ready={sandboxOk}
              loading={healthLoading}
              optional
            />
          </div>
        </div>
      </div>

      {/* Visual Workflow Pipeline (Compact, Information-Dense) */}
      <div>
        <div className="flex items-center justify-between mb-3 border-b border-border/80 pb-2.5">
          <h2 className="text-xs font-mono uppercase tracking-wider text-text-muted font-semibold flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            Deterministic Repair Pipeline (Stages A → G)
          </h2>
          <span className="text-[11px] font-mono text-text-muted">
            Zero Simulated Results · Real Test Execution
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3.5">
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
        <div className="flex items-center justify-between mb-3 border-b border-border/80 pb-2.5">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-text-muted" />
            <h2 className="text-xs font-mono uppercase tracking-wider text-text-muted font-semibold">
              Recent Investigations
            </h2>
          </div>
          <Link
            href="/jobs"
            className="text-xs font-mono text-accent hover:text-accent-bright flex items-center gap-1 transition-colors"
          >
            View all jobs
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {loadingJobs ? (
          <div className="space-y-2.5">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-14 w-full animate-pulse rounded-lg border border-border/80 bg-surface-1/60"
              />
            ))}
          </div>
        ) : recentJobs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border/80 bg-surface-1/40 p-8 text-center text-xs text-text-muted space-y-3">
            <p>No investigations yet. Launch the bundled demo project or start a new job.</p>
            <Button variant="outline" size="sm" asChild>
              <Link href="/demo">
                <FlaskConical className="h-3.5 w-3.5 text-accent" />
                Explore Demo Projects
              </Link>
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-border/60 rounded-lg border border-border/80 bg-surface-1/80 overflow-hidden shadow-xs backdrop-blur-xs">
            {recentJobs.map((j) => (
              <Link
                key={j.id}
                href={`/jobs/${j.id}`}
                className="group flex items-center justify-between p-3.5 text-xs hover:bg-surface-2/70 transition-all duration-150"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <StatusBadge status={j.status} />
                  <div className="truncate">
                    <span className="font-semibold text-text-primary mr-2.5 group-hover:text-accent transition-colors">
                      {j.repo_name}
                    </span>
                    <span className="text-text-secondary truncate">
                      {j.bug_description.slice(0, 65)}…
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-text-muted shrink-0 font-mono text-[11px]">
                  <span>{formatDate(j.created_at)}</span>
                  <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 group-hover:text-accent transition-transform duration-150" />
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
        className={`h-2 w-2 rounded-full transition-all ${
          ready
            ? "bg-status-success shadow-[0_0_8px_rgba(52,211,153,0.6)]"
            : optional
              ? "bg-status-warning shadow-[0_0_8px_rgba(251,191,36,0.5)]"
              : "bg-status-error shadow-[0_0_8px_rgba(248,113,113,0.5)]"
        }`}
      />
      <span className={ready ? "text-text-primary font-medium" : "text-text-muted"}>
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
      className={`rounded-lg border p-4 transition-all duration-200 hover:-translate-y-0.5 ${
        highlight
          ? "border-accent/50 bg-gradient-to-b from-accent/10 to-surface-1 shadow-glow-sm hover:shadow-glow-md hover:border-accent"
          : "border-border/80 bg-surface-1/90 hover:border-accent/30 hover:bg-surface-2/60 hover:shadow-xs"
      }`}
    >
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-accent bg-accent/10 border border-accent/20 px-1.5 py-0.5 rounded">
          Stage {num}
        </span>
        <div className={`p-1 rounded-md ${highlight ? "bg-accent/15 text-accent" : "text-text-muted"}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <h3 className="text-xs font-semibold text-text-primary mb-1.5 tracking-tight">{title}</h3>
      <p className="text-[11px] text-text-secondary leading-relaxed">{desc}</p>
    </div>
  );
}
