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
    <div className="p-8 max-w-xl">
      <h1 className="text-xl font-semibold text-text-primary mb-6">Settings</h1>

      <section className="space-y-4">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-text-muted">
          Model configuration
        </h2>

        {loading ? (
          <div className="h-24 rounded-md bg-surface-1 border border-border animate-pulse" />
        ) : (
          <div className="rounded-md border border-border bg-surface-1 p-4 space-y-3 text-xs">
            <Row label="Model" value={health?.nebius.model_id ?? "—"} mono />
            <Row label="Endpoint" value={health?.nebius.base_url ?? "—"} mono />
            <Row
              label="API key"
              value={health?.nebius.configured ? "Configured ✓" : "Not configured"}
              accent={health?.nebius.configured}
            />

            {modelStatus.reachable !== undefined && (
              <div
                className={`mt-2 rounded-sm px-2 py-1.5 text-xs ${
                  modelStatus.reachable
                    ? "bg-status-success/10 text-status-success border border-status-success/30"
                    : "bg-status-error/10 text-status-error border border-status-error/30"
                }`}
              >
                {modelStatus.reachable
                  ? "Model endpoint reachable."
                  : `Unreachable: ${modelStatus.error}`}
              </div>
            )}

            <button
              type="button"
              onClick={checkModel}
              disabled={checking || !health?.nebius.configured}
              className="mt-2 rounded border border-border bg-surface-2 px-3 py-1.5 text-xs text-text-secondary hover:bg-surface-3 disabled:opacity-50 transition-colors"
            >
              {checking ? "Checking…" : "Test model connection"}
            </button>

            {!health?.nebius.configured && (
              <p className="text-text-muted">
                Set <code className="font-mono bg-surface-2 px-1 rounded">NEBIUS_API_KEY</code> in{" "}
                <code className="font-mono bg-surface-2 px-1 rounded">.env</code> to enable inference.
              </p>
            )}
          </div>
        )}

        <h2 className="text-xs font-semibold uppercase tracking-widest text-text-muted pt-2">
          Infrastructure
        </h2>

        {health && (
          <div className="rounded-md border border-border bg-surface-1 p-4 space-y-3 text-xs">
            <Row
              label="Database"
              value={health.database.ok ? "Connected" : `Error: ${health.database.error}`}
              accent={health.database.ok}
            />
            <Row
              label="Sandbox"
              value={
                health.sandbox.enabled
                  ? health.sandbox.available
                    ? "Docker available"
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
