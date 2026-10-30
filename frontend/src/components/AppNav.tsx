"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BookOpen,
  Bug,
  Clock,
  Compass,
  FlaskConical,
  HelpCircle,
  Home,
  Plus,
  Settings,
  ShieldAlert,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SystemStatus } from "./SystemStatus";

const NAV_ITEMS = [
  { href: "/", label: "Workbench Home", icon: Home },
  { href: "/jobs/new", label: "New Investigation", icon: Plus },
  { href: "/jobs", label: "Job History", icon: Clock },
  { href: "/demo", label: "Demo Projects", icon: FlaskConical },
  { href: "/settings", label: "Configuration", icon: Settings },
];

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AppNav() {
  const pathname = usePathname();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);

  // Poll for any currently running jobs to surface an "Active Investigation" quick-link
  useEffect(() => {
    let mounted = true;
    const checkRunning = async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/v1/jobs/running`);
        if (res.ok) {
          const data = await res.json();
          if (mounted && data.running && data.running.length > 0) {
            setActiveJobId(data.running[0]);
          } else if (mounted) {
            setActiveJobId(null);
          }
        }
      } catch {
        // silent
      }
    };

    checkRunning();
    const interval = setInterval(checkRunning, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <>
      <nav
        className="flex h-screen w-60 flex-col border-r border-border bg-surface-1 select-none shrink-0"
        aria-label="Main navigation"
      >
        {/* Brand header */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-border/80 bg-surface-1/90 backdrop-blur-xs">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-accent/25 to-accent/5 border border-accent/40 shadow-glow-sm">
            <Bug className="h-4 w-4 text-accent animate-pulse-subtle" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-semibold tracking-tight text-text-primary">
                PatchPilot
              </span>
              <span className="rounded-full bg-accent/15 px-1.5 py-0.5 text-[9px] font-mono text-accent font-semibold border border-accent/20">
                v0.1
              </span>
            </div>
            <p className="text-[10px] text-text-muted leading-tight font-mono tracking-tight">
              Self-Healing Engineer
            </p>
          </div>
        </div>

        {/* Active job pill banner if an investigation is underway */}
        {activeJobId && (
          <div className="mx-2.5 mt-2.5">
            <Link
              href={`/jobs/${activeJobId}`}
              className={cn(
                "group flex items-center justify-between gap-2 rounded-md border px-2.5 py-2 text-xs transition-all shadow-xs",
                pathname === `/jobs/${activeJobId}`
                  ? "border-accent bg-accent/15 text-accent shadow-glow-sm font-medium"
                  : "border-status-info/40 bg-status-info/10 text-status-info hover:border-status-info/70 hover:bg-status-info/15"
              )}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
                </span>
                <span className="truncate font-mono text-[11px] font-medium">
                  Job {activeJobId.slice(0, 8)}…
                </span>
              </div>
              <Activity className="h-3 w-3 shrink-0 opacity-70 group-hover:opacity-100 animate-spin" />
            </Link>
          </div>
        )}

        {/* Nav links */}
        <ul className="flex-1 space-y-1 p-2.5" role="list">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-all duration-150",
                    "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent",
                    active
                      ? "bg-gradient-to-r from-accent/15 to-accent/5 text-accent border border-accent/30 shadow-xs font-semibold"
                      : "text-text-secondary hover:bg-surface-2/80 hover:text-text-primary"
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon className={cn("h-4 w-4 shrink-0 transition-transform duration-150", active ? "text-accent scale-105" : "text-text-muted group-hover:text-text-secondary")} />
                  <span>{label}</span>
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Help & Documentation trigger */}
        <div className="px-2.5 py-2 border-t border-border">
          <button
            type="button"
            onClick={() => setShowHelp(true)}
            className="flex w-full items-center gap-2.5 rounded px-3 py-1.5 text-xs text-text-muted hover:bg-surface-2 hover:text-text-secondary transition-colors"
          >
            <HelpCircle className="h-3.5 w-3.5 shrink-0" />
            <span>Workflow & Help</span>
          </button>
        </div>

        {/* System readiness footer */}
        <div className="border-t border-border bg-surface/50 p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-medium uppercase tracking-wider text-text-muted font-mono">
              Sandbox & Engine
            </span>
          </div>
          <SystemStatus />
        </div>
      </nav>

      {/* Workflow & Help Modal */}
      {showHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xs">
          <div className="relative w-full max-w-xl rounded-lg border border-border bg-surface-1 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-border mb-4">
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-accent" />
                <h2 className="text-sm font-semibold text-text-primary">
                  PatchPilot Workbench Architecture
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setShowHelp(false)}
                className="text-text-muted hover:text-text-primary transition-colors"
                aria-label="Close dialog"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs text-text-secondary leading-relaxed">
              <p>
                PatchPilot is a self-healing engineering tool. Unlike generic LLM chat
                interfaces, it operates through a deterministic 7-stage state machine
                where real tests—not confident prose—determine success:
              </p>

              <div className="space-y-2 rounded border border-border bg-surface p-3 font-mono text-[11px]">
                <div className="text-accent font-semibold">Deterministic Stages:</div>
                <div className="text-text-muted">A. Recon: Index files, exclude binaries & secrets.</div>
                <div className="text-text-muted">B. Baseline: Run tests in Docker; isolate defect.</div>
                <div className="text-text-muted">C. Diagnose: NVIDIA Nemotron root-cause analysis.</div>
                <div className="text-text-muted">D. Investigate: Bounded file & search tool calls.</div>
                <div className="text-text-muted">E. Patch: Generate minimal validated unified diff.</div>
                <div className="text-status-warning">F. Human Gate: User approves, revises, or rejects.</div>
                <div className="text-status-success">G. Verify: Post-patch test run in clean workspace copy.</div>
              </div>

              <div className="rounded border border-status-warning/30 bg-status-warning/10 p-2.5 text-[11px] text-status-warning flex gap-2">
                <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  <strong>Safety Model:</strong> Untrusted code never executes on the host. All sandbox commands run inside isolated Docker containers with no network, non-root user (UID 65534), and dropped capabilities.
                </span>
              </div>
            </div>

            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={() => setShowHelp(false)}
                className="rounded bg-surface-2 px-3.5 py-1.5 text-xs font-medium text-text-primary hover:bg-surface-3 transition-colors"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
