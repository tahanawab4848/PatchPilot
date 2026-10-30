"use client";

import { useEffect, useState } from "react";
import { healthApi } from "@/lib/api-client";
import type { HealthResponse } from "@/types/api";

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [modelStatus, setModelStatus] = useState<{
    reachable?: boolean;
    error?: string;
  }>({});

  useEffect(() => {
    healthApi
      .readiness()
      .then(setHealth)
      .finally(() => setLoading(false));
  }, []);

  const checkModel = async () => {
    setChecking(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health/model`
      );
      const data = await res.json();
      setModelStatus({ reachable: data.reachable, error: data.error });
    } catch (e) {
      setModelStatus({ reachable: false, error: "Could not reach backend." });
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="border-b border-border/80 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Configuration & Engine Status</h1>
        <p className="text-sm text-text-secondary mt-1">
          Verify runtime connectivity to the Nebius Token Factory inference provider and sandboxed test execution environment.
        </p>
      </div>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono">
            Model Configuration
          </h2>
        </div>

        {loading ? (
          <div className="h-28 rounded-lg bg-surface-1/70 border border-border/80 animate-pulse" />
        ) : (
          <div className="rounded-lg border border-border/80 bg-surface-1/90 p-5 space-y-3.5 text-xs shadow-xs backdrop-blur-xs">
            <Row label="Model" value={health?.nebius.model_id ?? "—"} mono />
            <Row label="Endpoint" value={health?.nebius.base_url ?? "—"} mono />
            <Row
              label="API key"
              value={health?.nebius.configured ? "Configured ✓" : "Not configured"}
              accent={health?.nebius.configured}
            />

            {modelStatus.reachable !== undefined && (
              <div
                className={`mt-2 rounded-md p-2.5 text-xs font-mono flex items-center gap-2 ${
                  modelStatus.reachable
                    ? "bg-status-success/10 text-status-success border border-status-success/30 shadow-[0_0_10px_rgba(52,211,153,0.15)]"
                    : "bg-status-error/10 text-status-error border border-status-error/30"
                }`}
              >
                <span className={`h-2 w-2 rounded-full ${modelStatus.reachable ? "bg-status-success" : "bg-status-error"}`} />
                {modelStatus.reachable
                  ? "Model endpoint reachable & verified."
                  : `Unreachable: ${modelStatus.error}`}
              </div>
            )}

            <div className="pt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={checkModel}
                disabled={checking || !health?.nebius.configured}
                className="rounded-md border border-border/80 bg-surface-2/80 px-3.5 py-1.5 text-xs font-medium text-text-primary hover:bg-surface-3 hover:border-accent/40 disabled:opacity-50 transition-all duration-150 shadow-xs"
              >
                {checking ? "Checking inference connection…" : "Test model connection"}
              </button>

              {!health?.nebius.configured && (
                <p className="text-[11px] text-text-muted font-mono">
                  Set <code className="bg-surface-2 px-1 py-0.5 rounded text-accent">NEBIUS_API_KEY</code> in <code className="bg-surface-2 px-1 py-0.5 rounded">.env</code>
                </p>
              )}
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 pt-4">
          <span className="h-1.5 w-1.5 rounded-full bg-status-info" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono">
            Infrastructure & Sandboxing
          </h2>
        </div>

        {health && (
          <div className="rounded-lg border border-border/80 bg-surface-1/90 p-5 space-y-3.5 text-xs shadow-xs backdrop-blur-xs">
            <Row
              label="Database"
              value={health.database.ok ? "Connected (Healthy)" : `Error: ${health.database.error}`}
              accent={health.database.ok}
            />
            <Row
              label="Sandbox"
              value={
                health.sandbox.enabled
                  ? health.sandbox.available
                    ? "Docker daemon operational"
                    : "Docker not available on this host"
                  : "Disabled"
              }
              accent={health.sandbox.available}
            />
          </div>
        )}
      </section>
    </div>
  );
}

function Row({
  label,
  value,
  mono = false,
  accent = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="flex gap-2 items-start">
      <span className="text-text-muted w-24 shrink-0">{label}</span>
      <span
        className={`${mono ? "font-mono" : ""} ${accent ? "text-status-success" : "text-text-secondary"}`}
      >
        {value}
      </span>
    </div>
  );
}
