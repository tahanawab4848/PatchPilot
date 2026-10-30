"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Code2,
  Copy,
  Cpu,
  Download,
  FileCode,
  FileText,
  FolderGit2,
  RefreshCw,
  Search,
  ShieldCheck,
  Terminal,
  Wrench,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import { useJob } from "@/hooks/useJob";
import { StatusBadge } from "@/components/StatusBadge";
import { JobTimeline } from "@/features/jobs/JobTimeline";
import { PatchReview } from "@/features/jobs/PatchReview";
import { ReasoningConsole } from "@/features/jobs/ReasoningConsole";
import { VerificationReport } from "@/features/jobs/VerificationReport";
import { Button } from "@/components/ui/button";
import { jobsApi, repositoriesApi } from "@/lib/api-client";
import { formatDate } from "@/lib/utils";
import type { FileContentResponse, RepositoryIndex } from "@/types/api";

type CenterTab = "patch" | "reasoning" | "file" | "verification";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { job, loading, error, isConnected, refresh } = useJob(id);

  const [activeTab, setActiveTab] = useState<CenterTab>("reasoning");
  const [cancelling, setCancelling] = useState(false);
  const [fileSearch, setFileSearch] = useState("");
  const [fileFilter, setFileFilter] = useState<"all" | "relevant" | "tests">("all");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<FileContentResponse | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  // Switch to patch tab when patch is proposed and ready for review
  useEffect(() => {
    if (job?.status === "awaiting_approval" && activeTab === "reasoning") {
      setActiveTab("patch");
    } else if (job?.repair_report && (activeTab === "file" || activeTab === "patch") && !selectedFile) {
      setActiveTab("verification");
    }
  }, [job?.status, job?.repair_report]);

  // Load file content when selectedFile changes
  useEffect(() => {
    if (!selectedFile || !job) return;
    setFileLoading(true);
    repositoriesApi
      .getFileContent(job.id, selectedFile)
      .then((data) => {
        setFileContent(data);
        setActiveTab("file");
      })
      .catch((err) => {
        console.error("Failed to load file content:", err);
      })
      .finally(() => {
        setFileLoading(false);
      });
  }, [selectedFile, job?.id]);

  const handleCancel = async () => {
    if (!job) return;
    setCancelling(true);
    try {
      await jobsApi.cancel(job.id);
      refresh();
    } catch (e) {
      console.error(e);
    } finally {
      setCancelling(false);
    }
  };

  const handleCopyJobId = () => {
    if (job?.id && navigator.clipboard) {
      navigator.clipboard.writeText(job.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-4">
        <div className="h-8 w-64 bg-surface-1 border border-border rounded animate-pulse" />
        <div className="h-4 w-96 bg-surface-1 border border-border rounded animate-pulse" />
        <div className="grid grid-cols-12 gap-4 pt-4">
          <div className="col-span-3 h-96 bg-surface-1 border border-border rounded animate-pulse" />
          <div className="col-span-6 h-96 bg-surface-1 border border-border rounded animate-pulse" />
          <div className="col-span-3 h-96 bg-surface-1 border border-border rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <div className="rounded-md border border-status-error/30 bg-status-error/10 p-5 text-sm text-status-error space-y-2">
          <div className="font-semibold flex items-center gap-2">
            <XCircle className="h-4 w-4" />
            Unable to load debugging job
          </div>
          <p>{error ?? "Job was not found."}</p>
          <div className="pt-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/jobs">Return to job history</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const metadata = job.project_metadata;
  const isTerminal = ["completed", "failed", "cancelled"].includes(job.status);

  // Filter file list
  const allFiles = metadata?.total_files ? [] : []; // from metadata
  const candidateFiles: string[] = [];
  if (job.proposed_patch) {
    // extract files from patch if available
    const lines = job.proposed_patch.split("\n");
    for (const l of lines) {
      if (l.startsWith("--- a/")) candidateFiles.push(l.slice(6));
    }
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface">
      {/* ── Top Header Toolbar ── */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-border bg-surface-1/90 select-none shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/jobs"
            className="text-text-muted hover:text-text-primary transition-colors p-1 rounded hover:bg-surface-2"
            title="Back to Jobs"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>

          <div className="flex items-center gap-2 min-w-0">
            <FolderGit2 className="h-4 w-4 text-accent shrink-0" />
            <h1 className="text-sm font-semibold text-text-primary truncate">
              {job.repo_name}
            </h1>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded border border-border bg-surface-2 text-text-muted shrink-0">
              {job.repo_source}
            </span>
            <StatusBadge status={job.status} />
            {job.repair_report?.outcome && (
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                job.repair_report.outcome === "verified"
                  ? "border-status-success/40 text-status-success bg-status-success/10"
                  : job.repair_report.outcome === "failed"
                  ? "border-status-error/40 text-status-error bg-status-error/10"
                  : "border-border/40 text-text-muted bg-surface-2"
              }`}>
                {job.repair_report.outcome === "verified"
                  ? "✓ Verified Fixed"
                  : job.repair_report.outcome === "failed"
                  ? "✗ Fix Failed"
                  : "Partial / Incomplete"}
              </span>
            )}
          </div>
        </div>

        {/* Right meta controls */}
        <div className="flex items-center gap-3">
          {/* Live connection indicator */}
          <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono text-text-muted">
            <span
              className={`h-2 w-2 rounded-full ${
                isConnected
                  ? "bg-status-success animate-pulse"
                  : isTerminal
                  ? "bg-text-muted"
                  : "bg-status-warning"
              }`}
            />
            <span>{isConnected ? "SSE Live" : isTerminal ? "Static" : "Polling"}</span>
          </div>

          <div className="h-3 w-px bg-border hidden sm:block" />

          {/* Quick .patch download button */}
          {job.proposed_patch && (
            <a
              href={jobsApi.getDownloadPatchUrl(job.id)}
              download
              className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-medium bg-surface-2 border border-border/70 hover:border-accent text-text-primary transition-colors"
              title="Download Verified .patch file"
            >
              <Download className="h-3 w-3 text-accent" />
              <span>.patch</span>
            </a>
          )}

          {/* Job ID copy button */}
          <button
            type="button"
            onClick={handleCopyJobId}
            className="hidden md:flex items-center gap-1.5 text-[11px] font-mono text-text-muted hover:text-text-secondary px-2 py-1 rounded hover:bg-surface-2 transition-colors border border-border/50"
            title="Copy full Job ID"
          >
            <Copy className="h-3 w-3" />
            <span>{job.id.slice(0, 8)}…</span>
            {copiedId && <span className="text-status-success font-bold">✓</span>}
          </button>

          {/* Refresh button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={refresh}
            className="h-7 px-2 text-xs text-text-secondary hover:text-text-primary"
            title="Refresh status"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>

          {/* Cancel button if active */}
          {!isTerminal && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={cancelling}
              className="h-7 text-xs text-status-error border-status-error/30 hover:bg-status-error/10 gap-1"
            >
              <X className="h-3 w-3" />
              Cancel Job
            </Button>
          )}
        </div>
      </header>

      {/* ── Three-Region Main Workbench ── */}
      <div className="flex-1 grid grid-cols-12 overflow-hidden">
        {/* ========================================================
            LEFT REGION: Repository Inspection & Timeline (Col 3)
           ======================================================== */}
        <aside className="col-span-12 md:col-span-3 border-r border-border bg-surface-1 flex flex-col overflow-hidden">
          {/* Repo metadata card */}
          <div className="p-3.5 border-b border-border bg-surface-2/30 space-y-2 shrink-0">
            <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
              <span>Primary Language</span>
              <span className="text-text-primary font-semibold">
                {metadata?.primary_language ?? "Python"}
              </span>
            </div>

            {metadata?.frameworks && metadata.frameworks.length > 0 && (
              <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
                <span>Frameworks</span>
                <span className="text-accent">
                  {metadata.frameworks.join(", ")}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between text-[11px] font-mono text-text-muted">
              <span>Iterations</span>
              <span className="text-text-primary font-semibold">
                {job.repair_iterations} / 3
              </span>
            </div>
          </div>

          {/* Investigation Timeline */}
          <div className="p-3 border-b border-border overflow-y-auto max-h-56 shrink-0">
            <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted font-medium mb-2 block">
              Investigation Stages
            </span>
            <JobTimeline job={job} />
          </div>

          {/* File Explorer */}
          <div className="flex-1 flex flex-col min-h-0 p-3 overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted font-medium">
                Repository Files
              </span>
              <span className="text-[10px] font-mono text-text-muted">
                Click to inspect
              </span>
            </div>

            {/* Quick search input */}
            <div className="relative mb-2">
              <Search className="h-3 w-3 text-text-muted absolute left-2.5 top-2" />
              <input
                type="text"
                placeholder="Filter files..."
                value={fileSearch}
                onChange={(e) => setFileSearch(e.target.value)}
                className="w-full bg-surface border border-border rounded pl-7 pr-2 py-1 text-xs font-mono placeholder:text-text-muted focus:outline-none focus:border-accent"
              />
            </div>

            {/* File List */}
            <div className="flex-1 overflow-y-auto space-y-1 font-mono text-xs pr-1">
              {/* Canonical demo files if demo source */}
              {job.repo_source === "demo" && job.repo_name === "fastapi_auth_service" && (
                <>
                  <FileTreeItem
                    path="src/auth.py"
                    active={selectedFile === "src/auth.py"}
                    tag="Defect Source"
                    onClick={() => setSelectedFile("src/auth.py")}
                  />
                  <FileTreeItem
                    path="tests/test_auth_service.py"
                    active={selectedFile === "tests/test_auth_service.py"}
                    tag="Failing Test"
                    onClick={() => setSelectedFile("tests/test_auth_service.py")}
                  />
                  <FileTreeItem
                    path="src/main.py"
                    active={selectedFile === "src/main.py"}
                    onClick={() => setSelectedFile("src/main.py")}
                  />
                  <FileTreeItem
                    path="src/models.py"
                    active={selectedFile === "src/models.py"}
                    onClick={() => setSelectedFile("src/models.py")}
                  />
                  <FileTreeItem
                    path="README.md"
                    active={selectedFile === "README.md"}
                    onClick={() => setSelectedFile("README.md")}
                  />
                </>
              )}

              {job.repo_source === "demo" && job.repo_name === "typescript_state_cart" && (
                <>
                  <FileTreeItem
                    path="src/cart.js"
                    active={selectedFile === "src/cart.js"}
                    tag="Defect Source"
                    onClick={() => setSelectedFile("src/cart.js")}
                  />
                  <FileTreeItem
                    path="tests/cart.test.js"
                    active={selectedFile === "tests/cart.test.js"}
                    tag="Failing Test"
                    onClick={() => setSelectedFile("tests/cart.test.js")}
                  />
                  <FileTreeItem
                    path="package.json"
                    active={selectedFile === "package.json"}
                    onClick={() => setSelectedFile("package.json")}
                  />
                  <FileTreeItem
                    path="README.md"
                    active={selectedFile === "README.md"}
                    onClick={() => setSelectedFile("README.md")}
                  />
                </>
              )}

              {job.repo_source === "demo" && job.repo_name !== "fastapi_auth_service" && job.repo_name !== "typescript_state_cart" && (
                <>
                  <FileTreeItem
                    path="src/calculator.py"
                    active={selectedFile === "src/calculator.py"}
                    tag="Defect Source"
                    onClick={() => setSelectedFile("src/calculator.py")}
                  />
                  <FileTreeItem
                    path="tests/test_calculator.py"
                    active={selectedFile === "tests/test_calculator.py"}
                    tag="Failing Test"
                    onClick={() => setSelectedFile("tests/test_calculator.py")}
                  />
                  <FileTreeItem
                    path="README.md"
                    active={selectedFile === "README.md"}
                    onClick={() => setSelectedFile("README.md")}
                  />
                  <FileTreeItem
                    path="requirements.txt"
                    active={selectedFile === "requirements.txt"}
                    onClick={() => setSelectedFile("requirements.txt")}
                  />
                </>
              )}

              {/* Extra candidate files if uploaded */}
              {job.repo_source !== "demo" && candidateFiles.length === 0 && (
                <div className="text-xs text-text-muted p-2">
                  Source files indexed in workspace.
                </div>
              )}
              {candidateFiles.map((p) => (
                <FileTreeItem
                  key={p}
                  path={p}
                  active={selectedFile === p}
                  tag="Patched"
                  onClick={() => setSelectedFile(p)}
                />
              ))}
            </div>
          </div>
        </aside>

        {/* ========================================================
            CENTER REGION: Code & Patch Review Workbench (Col 6)
           ======================================================== */}
        <main className="col-span-12 md:col-span-6 flex flex-col border-r border-border bg-surface overflow-hidden">
          {/* Failure/Cancellation Banner */}
          {job.status === "failed" && (
            <div className="shrink-0 flex items-start gap-3 px-4 py-3 border-b border-status-error/20 bg-status-error/8 text-sm">
              <XCircle className="h-4 w-4 text-status-error shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-status-error">Investigation failed</p>
                <p className="text-xs text-text-secondary mt-0.5">
                  {job.error_message || "The agent could not complete the repair. Check the right panel for details."}
                </p>
                <div className="flex gap-2 mt-2">
                  <Link href="/jobs/new" className="text-xs text-accent hover:underline">
                    Start a new investigation →
                  </Link>
                </div>
              </div>
            </div>
          )}
          {job.status === "cancelled" && (
            <div className="shrink-0 flex items-start gap-3 px-4 py-3 border-b border-border/50 bg-surface-2/30 text-sm">
              <AlertCircle className="h-4 w-4 text-text-muted shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-text-secondary">Job cancelled</p>
                <p className="text-xs text-text-muted mt-0.5">
                  This investigation was cancelled before completing.
                </p>
                <div className="flex gap-2 mt-2">
                  <Link href="/jobs/new" className="text-xs text-accent hover:underline">
                    Start a new investigation →
                  </Link>
                </div>
              </div>
            </div>
          )}
          {/* Tab navigation */}
          <div className="flex items-center justify-between border-b border-border bg-surface-1/50 px-3 py-1.5 shrink-0">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setActiveTab("reasoning")}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-sm transition-colors ${
                  activeTab === "reasoning"
                    ? "bg-accent/15 text-accent border border-accent/30 font-semibold"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-2"
                }`}
              >
                <Terminal className="h-3 w-3" />
                Live Reasoning
                {["analyzing", "reproducing", "diagnosing", "patch_proposed", "applying_patch", "verifying"].includes(job.status) ? (
                  <span className="h-1.5 w-1.5 rounded-full bg-status-success animate-pulse" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-text-muted opacity-40" />
                )}
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("patch")}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-sm transition-colors ${
                  activeTab === "patch"
                    ? "bg-accent/15 text-accent border border-accent/30 font-semibold"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-2"
                }`}
              >
                <Wrench className="h-3 w-3" />
                Proposed Patch
                {job.proposed_patch && (
                  <span className="h-1.5 w-1.5 rounded-full bg-status-warning" />
                )}
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("file")}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-sm transition-colors ${
                  activeTab === "file"
                    ? "bg-accent/15 text-accent border border-accent/30 font-semibold"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-2"
                }`}
              >
                <Code2 className="h-3 w-3" />
                File Source
                {selectedFile && (
                  <span className="text-[10px] text-text-muted font-mono truncate max-w-[100px]">
                    ({selectedFile.split("/").pop()})
                  </span>
                )}
              </button>

              {job.repair_report && (
                <button
                  type="button"
                  onClick={() => setActiveTab("verification")}
                  className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-sm transition-colors ${
                    activeTab === "verification"
                      ? "bg-accent/15 text-accent border border-accent/30 font-semibold"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-2"
                  }`}
                >
                  <ShieldCheck className="h-3 w-3" />
                  Verification Report
                  <span className="h-1.5 w-1.5 rounded-full bg-status-success" />
                </button>
              )}
            </div>

            {/* Quick tab info */}
            <span className="text-[10px] font-mono text-text-muted hidden lg:inline">
              Engineering Workbench
            </span>
          </div>

          {/* Center Tab Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {activeTab === "reasoning" && (
              <ReasoningConsole job={job} />
            )}

            {activeTab === "patch" && (
              <PatchReview job={job} onDecision={refresh} />
            )}

            {activeTab === "file" && (
              <div>
                {fileLoading ? (
                  <div className="p-8 text-center text-xs text-text-muted font-mono animate-pulse">
                    Loading source excerpt from workspace…
                  </div>
                ) : fileContent ? (
                  <div className="rounded border border-border bg-surface-1 overflow-hidden">
                    <div className="flex items-center justify-between border-b border-border bg-surface-2/60 px-3 py-1.5 text-xs font-mono">
                      <span className="text-text-primary font-semibold">
                        {fileContent.path}
                      </span>
                      <span className="text-text-muted text-[11px]">
                        {fileContent.total_lines} total lines
                      </span>
                    </div>
                    <pre className="p-3 text-xs font-mono leading-5 overflow-auto max-h-[600px] select-text">
                      {fileContent.content.split("\n").map((line, idx) => (
                        <div key={idx} className="flex hover:bg-surface-2/50 px-1">
                          <span className="w-10 shrink-0 text-text-muted select-none text-right pr-3 opacity-40">
                            {idx + 1}
                          </span>
                          <span className="flex-1">{line || " "}</span>
                        </div>
                      ))}
                    </pre>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 text-center text-xs text-text-muted border border-dashed border-border rounded-md bg-surface-1">
                    <FileCode className="h-6 w-6 text-text-muted mb-2 opacity-50" />
                    <p className="font-mono">Select a file from the repository tree.</p>
                    <p className="text-[11px] text-text-secondary mt-1">
                      Inspect code referenced in hypotheses or test executions.
                    </p>
                  </div>
                )}
              </div>
            )}

            {activeTab === "verification" && job.repair_report && (
              <VerificationReport report={job.repair_report} />
            )}
          </div>
        </main>

        {/* ========================================================
            RIGHT REGION: Agent Evidence & Metrics (Col 3)
           ======================================================== */}
        <aside className="col-span-12 md:col-span-3 bg-surface-1 overflow-y-auto p-4 space-y-4">
          {/* Current Stage Indicator */}
          <div className="p-3 rounded-md border border-border bg-surface-2/30 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted">
                Active Phase
              </span>
              <span className="text-xs font-mono text-accent capitalize">
                {job.status.replace("_", " ")}
              </span>
            </div>
            <p className="text-xs text-text-secondary leading-snug">
              {job.status === "reproducing" &&
                "Running tests in the isolated Docker sandbox to confirm failure."}
              {job.status === "diagnosing" &&
                "Requesting root-cause hypotheses from NVIDIA Nemotron."}
              {job.status === "patch_proposed" &&
                "Validating unified diff boundaries and syntax."}
              {job.status === "awaiting_approval" &&
                "Awaiting your review before applying patch to isolated workspace."}
              {job.status === "applying_patch" &&
                "Applying approved changes to clean workspace clone."}
              {job.status === "verifying" &&
                "Executing test suite again to confirm repair."}
              {job.status === "completed" &&
                "Repair verification complete with evidence-backed report."}
              {job.status === "failed" && (
                <span>{job.error_message || "Job halted or repair verification did not succeed."}</span>
              )}
              {job.status === "cancelled" && "This investigation was cancelled before reaching a conclusion."}
            </p>
          </div>

          {/* Bug Report Card */}
          <div className="p-3 rounded-md border border-border bg-surface space-y-1.5">
            <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted font-medium block">
              User Bug Report
            </span>
            <p className="text-xs font-mono text-text-secondary leading-relaxed break-words bg-surface-2/40 p-2 rounded border border-border/40">
              {job.bug_description}
            </p>
          </div>

          {/* Nebius Token Factory Telemetry */}
          {job.nebius_telemetry && (
            <div className="p-3 rounded-md border border-accent/40 bg-accent/5 space-y-2 font-mono">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 font-semibold text-accent text-[11px] uppercase tracking-wider">
                  <Zap className="h-3 w-3 fill-accent" />
                  Nebius Token Factory
                </span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-accent/20 text-accent font-bold">
                  {job.nebius_telemetry.tokens_per_second} tok/s
                </span>
              </div>

              <div className="text-[10px] text-text-muted leading-tight truncate">
                {job.nebius_telemetry.model_id}
              </div>

              <div className="grid grid-cols-2 gap-1.5 text-[11px] pt-1">
                <div className="p-1.5 rounded bg-surface-1 border border-border/60">
                  <div className="text-[9px] text-text-muted uppercase">TTFT</div>
                  <div className="font-semibold text-text-primary">
                    {job.nebius_telemetry.time_to_first_token_ms} ms
                  </div>
                </div>
                <div className="p-1.5 rounded bg-surface-1 border border-border/60">
                  <div className="text-[9px] text-text-muted uppercase">Tokens</div>
                  <div className="font-semibold text-text-primary">
                    {job.nebius_telemetry.completion_tokens} gen
                  </div>
                </div>
              </div>

              <div className="text-[9px] text-text-muted pt-0.5 flex items-center justify-between border-t border-border/40">
                <span>{job.nebius_telemetry.accelerator}</span>
                <span className="text-status-success font-semibold">FP8 Active</span>
              </div>
            </div>
          )}

          {/* Root-cause diagnosis summary (if available) */}
          {job.repair_report?.diagnosis_summary && (
            <div className="p-3 rounded-md border border-border bg-surface space-y-1.5">
              <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-accent font-medium">
                <Cpu className="h-3 w-3" />
                Diagnosis Evidence
              </div>
              <p className="text-xs text-text-primary leading-snug">
                {job.repair_report.diagnosis_summary}
              </p>
            </div>
          )}

          {/* Test Outcomes Matrix (Baseline vs Post-Patch) */}
          {job.repair_report && (
            <div className="p-3 rounded-md border border-border bg-surface space-y-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted font-medium block">
                Test Suite Comparison
              </span>

              <div className="space-y-1.5 font-mono text-xs">
                <div className="flex justify-between items-center text-[11px] p-1.5 rounded bg-surface-2 border border-border">
                  <span className="text-text-muted">Baseline:</span>
                  <span className="text-status-error font-semibold">
                    {job.repair_report.baseline_test_summary?.failed ?? 0} Failed /{" "}
                    {job.repair_report.baseline_test_summary?.passed ?? 0} Passed
                  </span>
                </div>

                <div className="flex justify-between items-center text-[11px] p-1.5 rounded bg-surface-2 border border-border">
                  <span className="text-text-muted">Post-Patch:</span>
                  <span className="text-status-success font-semibold">
                    {job.repair_report.post_patch_test_summary?.passed ?? 0} Passed /{" "}
                    {job.repair_report.post_patch_test_summary?.failed ?? 0} Failed
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Commands execution log */}
          {job.repair_report?.commands_executed && (
            <div className="p-3 rounded-md border border-border bg-surface space-y-1.5">
              <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-text-muted font-medium">
                <Terminal className="h-3 w-3" />
                Commands Executed
              </div>
              <div className="space-y-1 font-mono text-[11px] text-text-muted bg-surface-2/60 p-2 rounded border border-border">
                {job.repair_report.commands_executed.map((c, idx) => (
                  <div key={idx} className="truncate text-text-secondary">
                    $ {c}
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function FileTreeItem({
  path,
  active,
  tag,
  onClick,
}: {
  path: string;
  active: boolean;
  tag?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left px-2 py-1.5 rounded flex items-center justify-between text-xs transition-colors ${
        active
          ? "bg-accent/15 text-accent font-medium border border-accent/30"
          : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
      }`}
    >
      <div className="flex items-center gap-1.5 truncate">
        <FileCode className="h-3.5 w-3.5 shrink-0 opacity-70" />
        <span className="truncate">{path}</span>
      </div>
      {tag && (
        <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-surface-2 text-text-muted border border-border/50 shrink-0">
          {tag}
        </span>
      )}
    </button>
  );
}
