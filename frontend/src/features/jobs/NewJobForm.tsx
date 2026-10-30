"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  FileArchive,
  Flame,
  FlaskConical,
  Info,
  ShieldCheck,
  Sparkles,
  Upload,
  Zap,
} from "lucide-react";
import { jobsApi, repositoriesApi } from "@/lib/api-client";
import { formatBytes } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import type { DemoProject } from "@/types/api";

type Mode = "demo" | "upload";
type DiagnosticProfile = "standard" | "fast" | "thorough";

const DEMO_PRESETS: Record<string, { name: string; tag: string; framework: string; description: string; bug: string }> = {
  python_buggy_app: {
    name: "Python Arithmetic Defect",
    tag: "Python / Pytest",
    framework: "pytest · Python",
    description: "divide() returns 0.0 on zero divisor instead of raising ZeroDivisionError.",
    bug: "The `divide` function in `src/calculator.py` returns `0.0` instead of raising ZeroDivisionError when the divisor is zero. Tests `test_divide_by_zero` and `test_divide_by_zero_message` both fail. The fix should raise ZeroDivisionError('division by zero') inside the zero-guard.",
  },
  fastapi_auth_service: {
    name: "FastAPI Async JWT Auth Service",
    tag: "FastAPI / Pydantic V2",
    framework: "pytest-asyncio · HTTPX",
    description: "Asynchronous microservice token expiration logic defect (inverted comparison).",
    bug: "In `src/auth.py`, the token expiration verification function `verify_access_token` checks `if payload.get('exp') is not None and payload['exp'] > time.time(): raise TokenExpiredError('Token has expired')`. The operator is inverted (> instead of <), causing valid active tokens to fail with HTTP 401 Unauthorized, and expired tokens to pass. Fix the comparison so only tokens where exp < time.time() raise TokenExpiredError.",
  },
  typescript_state_cart: {
    name: "TypeScript Shopping Cart Service",
    tag: "Polyglot / Jest",
    framework: "Jest · Node.js",
    description: "Concurrent checkout state mutation bug where cart items are mutated in-place.",
    bug: "In `src/cart.js`, `applyDiscount(cart, discountPercent)` mutates `cart.items` array in-place (`item.price = item.price * ...`) instead of creating an immutable cloned copy. This causes subsequent or concurrent discount computations to compound prices improperly and corrupt catalog prices. Fix `applyDiscount` to map items immutably without mutating original objects.",
  },
};

const DEMO_BUG_DESCRIPTION = DEMO_PRESETS.python_buggy_app.bug;

export function NewJobForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const demoParam = searchParams.get("demo");

  const [mode, setMode] = useState<Mode>("demo");
  const [profile, setProfile] = useState<DiagnosticProfile>("standard");
  const [file, setFile] = useState<File | null>(null);
  const [bugDescription, setBugDescription] = useState(DEMO_BUG_DESCRIPTION);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [demoProjects, setDemoProjects] = useState<DemoProject[]>([]);
  const [selectedDemoId, setSelectedDemoId] = useState("python_buggy_app");

  useEffect(() => {
    if (demoParam && DEMO_PRESETS[demoParam]) {
      setSelectedDemoId(demoParam);
      setBugDescription(DEMO_PRESETS[demoParam].bug);
    }
  }, [demoParam]);

  useEffect(() => {
    repositoriesApi
      .listDemos()
      .then((res) => {
        if (res.demos && res.demos.length > 0) {
          setDemoProjects(res.demos);
        }
      })
      .catch(() => {});
  }, []);

  const handleFileSelect = (f: File) => {
    if (!f.name.endsWith(".zip")) {
      setError("Only .zip archives are supported.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError("Archive exceeds the 50 MB limit.");
      return;
    }
    setFile(f);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const desc = bugDescription.trim();
    if (!desc || desc.length < 10) {
      setError("Bug description must be at least 10 characters.");
      return;
    }

    try {
      if (mode === "demo") {
        setCreating(true);
        const job = await jobsApi.create({
          repo_name: selectedDemoId,
          repo_source: "demo",
          bug_description: desc,
        });
        router.push(`/jobs/${job.id}`);
      } else {
        if (!file) {
          setError("Please select a ZIP repository archive.");
          return;
        }
        setUploading(true);
        setUploadProgress(40);
        const upload = await repositoriesApi.upload(file);
        setUploadProgress(100);
        setUploading(false);
        setCreating(true);
        const job = await jobsApi.create({
          repo_name: file.name.replace(".zip", ""),
          repo_source: "upload",
          archive_path: upload.archive_path,
          bug_description: desc,
        });
        router.push(`/jobs/${job.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create debugging job.");
      setUploading(false);
      setCreating(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-3xl">
      {/* 1. Repository Source Selection */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-mono uppercase tracking-wider text-text-muted">
            1. Select Repository Source
          </Label>
          <span className="text-[11px] font-mono text-text-muted">
            Isolated Sandbox Guarantee
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => {
              setMode("demo");
              setFile(null);
              setError(null);
              setBugDescription(DEMO_BUG_DESCRIPTION);
            }}
            className={`flex items-start gap-3 rounded-lg border p-3.5 text-left transition-all duration-150 ${
              mode === "demo"
                ? "border-accent bg-accent/10 shadow-glow-sm ring-1 ring-accent/40"
                : "border-border/80 bg-surface-1/90 hover:bg-surface-2/80 hover:border-border text-text-secondary"
            }`}
          >
            <div className={`mt-0.5 rounded-md p-2 transition-colors ${mode === "demo" ? "bg-accent/20 text-accent" : "bg-surface-2 text-text-muted"}`}>
              <FlaskConical className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-text-primary">
                Bundled Demo Project
              </div>
              <p className="text-[11px] text-text-secondary mt-0.5 leading-snug">
                Pre-configured Python calculator with known reproducible failure.
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => {
              setMode("upload");
              setError(null);
              if (bugDescription === DEMO_BUG_DESCRIPTION) {
                setBugDescription("");
              }
            }}
            className={`flex items-start gap-3 rounded-lg border p-3.5 text-left transition-all duration-150 ${
              mode === "upload"
                ? "border-accent bg-accent/10 shadow-glow-sm ring-1 ring-accent/40"
                : "border-border/80 bg-surface-1/90 hover:bg-surface-2/80 hover:border-border text-text-secondary"
            }`}
          >
            <div className={`mt-0.5 rounded-md p-2 transition-colors ${mode === "upload" ? "bg-accent/20 text-accent" : "bg-surface-2 text-text-muted"}`}>
              <Upload className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-text-primary">
                Upload Repository ZIP
              </div>
              <p className="text-[11px] text-text-secondary mt-0.5 leading-snug">
                Upload your local codebase (.zip up to 50 MB, extracted safely).
              </p>
            </div>
          </button>
        </div>
      </div>

      {/* Mode Details: Demo project selector */}
      {mode === "demo" && (
        <div className="rounded-md border border-border bg-surface-1 p-3.5 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-mono text-text-muted uppercase text-[10px]">
              Select Demo Target Project
            </span>
            <span className="font-mono text-status-success text-[11px] flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Verified Reproducible Defect Suites
            </span>
          </div>

          <div className="space-y-2">
            {Object.entries(DEMO_PRESETS).map(([demoId, preset]) => {
              const isSelected = selectedDemoId === demoId;
              return (
                <button
                  key={demoId}
                  type="button"
                  onClick={() => {
                    setSelectedDemoId(demoId);
                    setBugDescription(preset.bug);
                  }}
                  className={`w-full rounded border p-3 text-left transition-all flex items-start justify-between gap-3 ${
                    isSelected
                      ? "border-accent bg-accent/10 shadow-xs ring-1 ring-accent/40"
                      : "border-border bg-surface hover:bg-surface-2"
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-text-primary">
                        {preset.name}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-2 border border-border/60 text-accent font-medium">
                        {preset.tag}
                      </span>
                    </div>
                    <div className="text-[11px] text-text-secondary mt-1 leading-snug">
                      {preset.description}
                    </div>
                  </div>

                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-2 border border-border text-text-muted shrink-0 mt-0.5">
                    {preset.framework}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Mode Details: File Upload Area */}
      {mode === "upload" && (
        <div className="space-y-2">
          <div
            className={`relative flex flex-col items-center justify-center rounded-md border-2 border-dashed p-6 transition-colors cursor-pointer ${
              dragOver
                ? "border-accent bg-accent/5"
                : "border-border bg-surface-1 hover:border-border/80"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files[0];
              if (f) handleFileSelect(f);
            }}
            onClick={() => document.getElementById("file-input")?.click()}
            role="button"
            tabIndex={0}
            aria-label="Upload ZIP archive"
            onKeyDown={(e) => e.key === "Enter" && document.getElementById("file-input")?.click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".zip"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileSelect(f);
              }}
            />

            {file ? (
              <div className="text-center py-2">
                <FileArchive className="h-7 w-7 text-accent mx-auto mb-1" />
                <p className="text-xs font-mono font-medium text-text-primary">
                  {file.name}
                </p>
                <p className="text-[11px] text-text-secondary font-mono mt-0.5">
                  {formatBytes(file.size)} · Ready for inspection
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                  className="mt-2 text-[11px] font-mono text-status-error hover:underline"
                >
                  Change archive
                </button>
              </div>
            ) : (
              <div className="text-center py-2">
                <Upload className="h-6 w-6 text-text-muted mx-auto mb-1" />
                <p className="text-xs text-text-primary font-medium">
                  Drop a repository ZIP archive here, or browse
                </p>
                <p className="text-[11px] text-text-muted font-mono mt-0.5">
                  Max 50 MB · Standard .zip · Path traversal validated on extract
                </p>
              </div>
            )}

            {uploading && (
              <div className="mt-3 w-full max-w-xs">
                <div className="h-1.5 w-full bg-surface-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-[10px] font-mono text-text-muted text-center mt-1">
                  Uploading archive… {uploadProgress}%
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. Diagnostic Profile Selector */}
      <div className="space-y-2">
        <Label className="text-xs font-mono uppercase tracking-wider text-text-muted">
          2. Diagnostic Execution Profile
        </Label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <ProfilePill
            id="standard"
            active={profile === "standard"}
            onClick={() => setProfile("standard")}
            icon={Sparkles}
            label="Standard"
            desc="Full reproduction, Nemotron diagnosis, patch & sandbox verification."
          />
          <ProfilePill
            id="fast"
            active={profile === "fast"}
            onClick={() => setProfile("fast")}
            icon={Zap}
            label="Fast Check"
            desc="Focused diagnosis targeting primary failing stack trace."
          />
          <ProfilePill
            id="thorough"
            active={profile === "thorough"}
            onClick={() => setProfile("thorough")}
            icon={ShieldCheck}
            label="Thorough"
            desc="Deep multi-tool investigation with full regression audit."
          />
        </div>
      </div>

      {/* 3. Bug Description */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="bug-desc" className="text-xs font-mono uppercase tracking-wider text-text-muted">
            3. Bug Description & Failing Test Trace
          </Label>
          {mode === "demo" && (
            <button
              type="button"
              onClick={() => setBugDescription(DEMO_BUG_DESCRIPTION)}
              className="text-[11px] font-mono text-accent hover:underline"
            >
              Reset to demo description
            </button>
          )}
        </div>

        <Textarea
          id="bug-desc"
          value={bugDescription}
          onChange={(e) => setBugDescription(e.target.value)}
          placeholder="Describe the bug: failing test command, expected behavior, stack traces, and relevant file paths..."
          rows={5}
          maxLength={4000}
          className="font-mono text-xs leading-relaxed bg-surface-1 border-border focus:border-accent"
          required
        />

        <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
          <span>Be specific: include failing test names and expected outcomes.</span>
          <span>{bugDescription.length} / 4000</span>
        </div>
      </div>

      {/* Pre-flight Security & Isolation Guarantee Banner */}
      <div className="rounded border border-border/80 bg-surface-1 p-3 text-xs text-text-secondary flex items-start gap-2.5">
        <Info className="h-4 w-4 text-accent shrink-0 mt-0.5" />
        <div className="space-y-1 text-[11px] leading-relaxed">
          <span className="font-semibold text-text-primary">Sandbox Guarantee:</span> Untrusted repository code will be executed exclusively inside a hardened Docker sandbox (UID 65534, non-root, no network access). No patch will modify original repository files before explicit approval.
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="flex items-start gap-2 rounded border border-status-error/40 bg-status-error/10 p-3 text-xs text-status-error font-mono">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Action button */}
      <div className="pt-2">
        <Button
          type="submit"
          disabled={uploading || creating}
          size="lg"
          className="w-full sm:w-auto bg-accent text-surface hover:bg-accent-bright font-medium gap-2"
        >
          {uploading
            ? "Uploading archive…"
            : creating
              ? "Initializing investigation…"
              : "Launch Autonomous Investigation"}
        </Button>
      </div>
    </form>
  );
}

function ProfilePill({
  id,
  active,
  onClick,
  icon: Icon,
  label,
  desc,
}: {
  id: string;
  active: boolean;
  onClick: () => void;
  icon: React.ElementType;
  label: string;
  desc: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border p-3 text-left transition-all duration-150 ${
        active
          ? "border-accent bg-accent/10 shadow-glow-sm ring-1 ring-accent/40"
          : "border-border/80 bg-surface-1/90 hover:bg-surface-2/80 hover:border-border text-text-secondary"
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`h-4 w-4 ${active ? "text-accent" : "text-text-muted"}`} />
        <span className={`text-xs font-semibold ${active ? "text-text-primary" : "text-text-secondary"}`}>
          {label}
        </span>
      </div>
      <p className="text-[11px] text-text-muted leading-relaxed">{desc}</p>
    </button>
  );
}
