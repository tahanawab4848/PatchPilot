"use client";

import { useHealth } from "@/hooks/useHealth";
import { cn } from "@/lib/utils";

export function SystemStatus() {
  const { health, loading } = useHealth();

  if (loading) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-text-muted">
        <span className="h-1.5 w-1.5 rounded-full bg-text-muted animate-pulse" />
        Checking…
      </div>
    );
  }

  if (!health) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-status-error">
        <span className="h-1.5 w-1.5 rounded-full bg-status-error" />
        Backend offline
      </div>
    );
  }

  const dbOk = health.database.ok;
  const modelConfigured = health.nebius.configured;
  const sandboxReady = health.sandbox.available;

  const allGood = dbOk && modelConfigured;

  return (
    <div className="flex items-center gap-3 text-xs text-text-secondary">
      <Dot ok={dbOk} label="DB" />
      <Dot ok={modelConfigured} label="Model" />
      <Dot ok={sandboxReady} label="Sandbox" optional />
    </div>
  );
}

function Dot({
  ok,
  label,
  optional = false,
}: {
  ok: boolean;
  label: string;
  optional?: boolean;
}) {
  return (
    <span className="flex items-center gap-1">
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          ok
            ? "bg-status-success"
            : optional
              ? "bg-status-warning"
              : "bg-status-error"
        )}
      />
      <span className={cn(ok ? "text-text-secondary" : optional ? "text-status-warning" : "text-status-error")}>
        {label}
      </span>
    </span>
  );
}
