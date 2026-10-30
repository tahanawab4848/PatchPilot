"use client";

import { useState } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  Download,
  FileArchive,
  FileCheck,
  GitPullRequest,
  ShieldAlert,
  Sparkles,
  Terminal,
  X,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { jobsApi } from "@/lib/api-client";
import type { RepairReport } from "@/types/api";

interface VerificationReportProps {
  report: RepairReport;
}

export function VerificationReport({ report }: VerificationReportProps) {
  const [copied, setCopied] = useState(false);
  const [showPrModal, setShowPrModal] = useState(false);
  const [prLoading, setPrLoading] = useState(false);
  const [prData, setPrData] = useState<{ title: string; body: string } | null>(null);
  const [copiedPrTitle, setCopiedPrTitle] = useState(false);
  const [copiedPrBody, setCopiedPrBody] = useState(false);

  const handleOpenPrModal = async () => {
    setShowPrModal(true);
    if (!prData) {
      setPrLoading(true);
      try {
        const data = await jobsApi.getPrTemplate(report.job_id);
        setPrData({ title: data.title, body: data.body });
      } catch (err) {
        console.error("Failed to load PR template:", err);
      } finally {
        setPrLoading(false);
      }
    }
  };

  const handleCopyPrTitle = () => {
    if (prData && navigator.clipboard) {
      navigator.clipboard.writeText(prData.title);
      setCopiedPrTitle(true);
      setTimeout(() => setCopiedPrTitle(false), 2000);
    }
  };

  const handleCopyPrBody = () => {
    if (prData && navigator.clipboard) {
      navigator.clipboard.writeText(prData.body);
      setCopiedPrBody(true);
      setTimeout(() => setCopiedPrBody(false), 2000);
    }
  };

  const handleCopyMarkdown = () => {
    const md = generateMarkdownReport(report);
    if (navigator.clipboard) {
      navigator.clipboard.writeText(md);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `repair_report_${report.job_id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isVerified = report.outcome === "verified";
  const isPartial = report.outcome === "partially_verified";
  const isFailed = report.outcome === "failed";
  const isUnable = report.outcome === "unable_to_verify";

  return (
    <div className="space-y-4">
      {/* Top Outcome Card */}
      <div
        className={`p-4 rounded-md border flex items-start gap-3.5 ${
          isVerified
            ? "border-status-success/40 bg-status-success/10 text-status-success"
            : isPartial
            ? "border-status-warning/40 bg-status-warning/10 text-status-warning"
            : isFailed
            ? "border-status-error/40 bg-status-error/10 text-status-error"
            : "border-border bg-surface-2 text-text-secondary"
        }`}
      >
        {isVerified && <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5" />}
        {isPartial && <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />}
        {isFailed && <XCircle className="h-5 w-5 shrink-0 mt-0.5" />}
        {isUnable && <AlertOctagon className="h-5 w-5 shrink-0 mt-0.5" />}

        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold tracking-tight uppercase font-mono">
              Outcome: {report.outcome.replace("_", " ")}
            </h3>
            <span className="text-[11px] font-mono opacity-80">
              {report.total_duration_seconds.toFixed(2)}s elapsed
            </span>
          </div>

          <p className="text-xs opacity-90 leading-relaxed font-sans">
            {isVerified &&
              "All failing baseline tests now pass in the isolated workspace. Zero regressions detected."}
            {isPartial &&
              "Some targeted test failures were resolved, but other issues or unverified tests remain."}
            {isFailed &&
              "The patch failed verification: baseline failures persisted or regressions were introduced."}
            {isUnable &&
              "Unable to verify: sandbox infrastructure error or timeout occurred during execution."}
          </p>
        </div>
      </div>

      {/* ── Enterprise Delivery & PR Climax Toolbar ── */}
      <div className="rounded-md border border-accent/40 bg-accent/10 p-3.5 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-sm">
        <div className="space-y-0.5 text-center sm:text-left">
          <div className="text-xs font-semibold text-text-primary flex items-center gap-1.5 justify-center sm:justify-start">
            <Sparkles className="h-4 w-4 text-accent fill-accent/20" />
            <span>Autonomous Repair Verified & Export-Ready</span>
          </div>
          <p className="text-[11px] text-text-secondary">
            Deliver the fix into your engineering workflow via verified git patch, ZIP, or 1-click PR.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-center sm:justify-end">
          <a
            href={jobsApi.getDownloadPatchUrl(report.job_id)}
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-surface-1 border border-border hover:bg-surface-2 hover:border-accent text-text-primary transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-accent" />
            Download .patch
          </a>

          <a
            href={jobsApi.getDownloadRepairedUrl(report.job_id)}
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-surface-1 border border-border hover:bg-surface-2 hover:border-accent text-text-primary transition-colors"
          >
            <FileArchive className="h-3.5 w-3.5 text-accent" />
            Export ZIP
          </a>

          <Button
            size="sm"
            onClick={handleOpenPrModal}
            className="text-xs gap-1.5 bg-accent text-surface hover:bg-accent-bright font-semibold shadow-xs"
          >
            <GitPullRequest className="h-3.5 w-3.5" />
            1-Click GitHub PR
          </Button>
        </div>
      </div>

      {/* Evaluation Metrics Breakdown */}
      {report.metrics && (
        <div className="rounded-md border border-border bg-surface-1 p-3.5 space-y-2.5">
          <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted font-medium">
            Evaluation Observability Metrics
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
            <MetricItem
              label="Bug Reproduced"
              val={report.metrics.bug_reproduced ? "Yes" : "No"}
              ok={report.metrics.bug_reproduced}
            />
            <MetricItem
              label="Diagnosis Valid"
              val={report.metrics.valid_diagnosis_produced ? "Yes" : "No"}
              ok={report.metrics.valid_diagnosis_produced}
            />
            <MetricItem
              label="Patch Applied"
              val={report.metrics.patch_applied_successfully ? "Yes" : "No"}
              ok={report.metrics.patch_applied_successfully}
            />
            <MetricItem
              label="Zero Regressions"
              val={report.metrics.regression_tests_passed ? "Pass" : "Failed"}
              ok={report.metrics.regression_tests_passed}
            />
          </div>
        </div>
      )}

      {/* Test Results Comparison Matrix */}
      <div className="rounded-md border border-border bg-surface-1 overflow-hidden">
        <div className="border-b border-border bg-surface-2/40 px-3 py-2 text-xs font-mono text-text-muted uppercase tracking-wider">
          Baseline vs Post-Patch Verification Summary
        </div>

        <div className="grid grid-cols-2 divide-x divide-border p-3 text-xs font-mono">
          {/* Baseline summary */}
          <div className="space-y-1.5 pr-3">
            <span className="text-[11px] text-text-muted uppercase">
              Baseline (Before Patch)
            </span>
            <div className="flex gap-3 text-xs">
              <span className="text-status-success">
                {report.baseline_test_summary?.passed ?? 0} passed
              </span>
              <span className="text-status-error">
                {report.baseline_test_summary?.failed ?? 0} failed
              </span>
            </div>
            {Array.isArray(report.baseline_test_summary?.failing_tests) &&
              report.baseline_test_summary.failing_tests.length > 0 && (
                <div className="space-y-0.5 pt-1">
                  {report.baseline_test_summary.failing_tests.map((t: string) => (
                    <div
                      key={t}
                      className="text-[11px] text-status-error truncate"
                    >
                      ✗ {t}
                    </div>
                  ))}
                </div>
              )}
          </div>

          {/* Post-patch summary */}
          <div className="space-y-1.5 pl-3">
            <span className="text-[11px] text-text-muted uppercase">
              Post-Patch (Isolated Sandbox)
            </span>
            <div className="flex gap-3 text-xs">
              <span className="text-status-success">
                {report.post_patch_test_summary?.passed ?? 0} passed
              </span>
              <span className="text-status-error">
                {report.post_patch_test_summary?.failed ?? 0} failed
              </span>
            </div>
            {report.regression_failures && report.regression_failures.length > 0 ? (
              <div className="space-y-0.5 pt-1">
                {report.regression_failures.map((r) => (
                  <div key={r} className="text-[11px] text-status-error truncate">
                    Regression: {r}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[11px] text-status-success pt-1">
                ✓ No regressions detected
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Warnings & Limitations */}
      {(report.warnings.length > 0 || report.limitations.length > 0) && (
        <div className="rounded-md border border-border bg-surface-1 p-3 text-xs space-y-2">
          {report.warnings.length > 0 && (
            <div className="text-status-warning space-y-1 font-mono text-[11px]">
              <span className="font-semibold uppercase">Warnings:</span>
              <ul className="list-disc pl-4 space-y-0.5">
                {report.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {report.limitations.length > 0 && (
            <div className="text-text-muted space-y-1 font-mono text-[11px]">
              <span className="font-semibold uppercase">Limitations:</span>
              <ul className="list-disc pl-4 space-y-0.5">
                {report.limitations.map((l, idx) => (
                  <li key={idx}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Copy / Export Report actions */}
      <div className="flex justify-end gap-2 pt-1">
        <Button
          variant="outline"
          size="sm"
          onClick={handleCopyMarkdown}
          className="text-xs gap-1.5 border-border hover:bg-surface-2 text-text-primary"
        >
          <Copy className="h-3 w-3" />
          {copied ? "Report Copied!" : "Copy Markdown Report"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownloadJson}
          className="text-xs gap-1.5 border-border hover:bg-surface-2 text-text-primary"
        >
          <Download className="h-3 w-3" />
          Export JSON
        </Button>
      </div>

      {/* GitHub PR Ready Modal */}
      {showPrModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-xs">
          <div className="relative w-full max-w-2xl rounded-lg border border-border bg-surface-1 p-5 shadow-2xl space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded bg-accent/20 text-accent">
                  <GitPullRequest className="h-4 w-4" />
                </span>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary">
                    GitHub Pull Request Artifact
                  </h3>
                  <p className="text-[11px] text-text-secondary">
                    Ready to copy into your repository or CI/CD branch.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowPrModal(false)}
                className="text-text-muted hover:text-text-primary p-1 rounded hover:bg-surface-2"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {prLoading ? (
              <div className="p-12 text-center text-xs text-text-muted font-mono animate-pulse">
                Synthesizing PR markdown from verification evidence...
              </div>
            ) : prData ? (
              <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs pr-1">
                {/* PR Title */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-text-muted uppercase text-[10px]">PR Title</span>
                    <button
                      type="button"
                      onClick={handleCopyPrTitle}
                      className="text-accent hover:underline flex items-center gap-1 text-[11px]"
                    >
                      {copiedPrTitle ? <Check className="h-3 w-3 text-status-success" /> : <Copy className="h-3 w-3" />}
                      {copiedPrTitle ? "Copied" : "Copy Title"}
                    </button>
                  </div>
                  <div className="p-2 rounded bg-surface border border-border font-medium text-text-primary select-text">
                    {prData.title}
                  </div>
                </div>

                {/* PR Markdown Body */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-text-muted uppercase text-[10px]">PR Description (Markdown)</span>
                    <button
                      type="button"
                      onClick={handleCopyPrBody}
                      className="text-accent hover:underline flex items-center gap-1 text-[11px]"
                    >
                      {copiedPrBody ? <Check className="h-3 w-3 text-status-success" /> : <Copy className="h-3 w-3" />}
                      {copiedPrBody ? "Copied Body" : "Copy Markdown"}
                    </button>
                  </div>
                  <pre className="p-3 rounded bg-surface border border-border text-[11px] leading-relaxed overflow-x-auto max-h-72 select-text whitespace-pre-wrap text-text-secondary">
                    {prData.body}
                  </pre>
                </div>
              </div>
            ) : null}

            <div className="flex justify-between items-center pt-2 border-t border-border/60">
              <a
                href={jobsApi.getDownloadPatchUrl(report.job_id)}
                download
                className="text-xs text-accent hover:underline flex items-center gap-1"
              >
                <Download className="h-3.5 w-3.5" />
                Download raw .patch file
              </a>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowPrModal(false)}
                  className="text-xs"
                >
                  Close
                </Button>
                <Button
                  size="sm"
                  onClick={handleCopyPrBody}
                  className="text-xs bg-accent text-surface hover:bg-accent-bright font-semibold gap-1"
                >
                  <Copy className="h-3.5 w-3.5" />
                  {copiedPrBody ? "Copied All!" : "Copy PR Markdown"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricItem({
  label,
  val,
  ok,
}: {
  label: string;
  val: string;
  ok: boolean;
}) {
  return (
    <div className="p-2 rounded bg-surface border border-border">
      <div className="text-[10px] text-text-muted">{label}</div>
      <div
        className={`font-semibold mt-0.5 ${
          ok ? "text-status-success" : "text-status-error"
        }`}
      >
        {val}
      </div>
    </div>
  );
}

function generateMarkdownReport(r: RepairReport): string {
  return `# PatchPilot Verification Report

- **Job ID:** \`${r.job_id}\`
- **Outcome:** ${r.outcome.toUpperCase()}
- **Duration:** ${r.total_duration_seconds.toFixed(2)}s
- **Repair Iterations:** ${r.repair_iterations}

## Diagnosis Summary
${r.diagnosis_summary}

## Patch Summary
${r.patch_summary}
- **Modified Files:** ${r.modified_files.join(", ")}

## Test Suite Results
- **Baseline Tests:** ${r.baseline_test_summary?.passed ?? 0} passed, ${
    r.baseline_test_summary?.failed ?? 0
  } failed
- **Post-Patch Tests:** ${r.post_patch_test_summary?.passed ?? 0} passed, ${
    r.post_patch_test_summary?.failed ?? 0
  } failed
- **Regressions:** ${
    r.regression_failures?.length > 0 ? r.regression_failures.join(", ") : "None"
  }
`;
}
