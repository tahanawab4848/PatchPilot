"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  Cpu,
  GitCommit,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Zap,
  XCircle,
} from "lucide-react";
import { jobsApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { JobDetail } from "@/types/api";

interface PatchReviewProps {
  job: JobDetail;
  onDecision: () => void;
}

export function PatchReview({ job, onDecision }: PatchReviewProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showReviseModal, setShowReviseModal] = useState(false);
  const [revisionNotes, setRevisionNotes] = useState("");
  const [copied, setCopied] = useState(false);

  const handleDecision = async (
    decision: "approved" | "rejected" | "revised",
    notes?: string
  ) => {
    setSubmitting(true);
    setError(null);
    try {
      await jobsApi.approve(job.id, { decision, notes });
      setShowReviseModal(false);
      onDecision();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = () => {
    if (job.proposed_patch && navigator.clipboard) {
      navigator.clipboard.writeText(job.proposed_patch);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!job.proposed_patch) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-xs text-text-muted border border-dashed border-border rounded-md bg-surface-1">
        <GitCommit className="h-6 w-6 text-text-muted mb-2 opacity-50" />
        <p className="font-mono">No patch proposed yet.</p>
        <p className="text-[11px] text-text-secondary mt-1">
          Patch diff will appear here once Stage E completes.
        </p>
      </div>
    );
  }

  const diffLines = job.proposed_patch.split("\n");

  // Count additions / deletions
  let addedCount = 0;
  let removedCount = 0;
  for (const line of diffLines) {
    if (line.startsWith("+") && !line.startsWith("+++")) addedCount++;
    else if (line.startsWith("-") && !line.startsWith("---")) removedCount++;
  }

  const isAwaitingApproval = job.status === "awaiting_approval";

  return (
    <div className="space-y-4">
      {/* Verification state warning banner */}
      {isAwaitingApproval && (
        <div className="flex items-start gap-2.5 rounded border border-status-warning/40 bg-status-warning/10 p-3 text-xs text-status-warning">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold">Human Review Required:</span> This
            patch has been generated and validated, but has{" "}
            <strong>not yet been applied or verified</strong>. Approving will
            apply it to an isolated sandbox workspace and trigger the post-patch test suite.
          </div>
        </div>
      )}

      {/* NVIDIA Nemotron Dual-Pass Reasoner & Critic */}
      {job.nemotron_critique && (
        <div className="rounded-lg border border-accent/40 bg-gradient-to-b from-accent/10 to-surface-1 p-4 space-y-3 shadow-glow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="p-1.5 rounded-md bg-accent/20 text-accent border border-accent/30 shadow-inner-glow">
                <Cpu className="h-4 w-4" />
              </span>
              <div>
                <span className="text-xs font-semibold text-text-primary">
                  NVIDIA Nemotron Dual-Pass Reasoner & Critic
                </span>
                <span className="ml-2 text-[10px] font-mono px-2 py-0.5 rounded-full bg-surface-2 border border-border text-accent font-medium">
                  HelpSteer2 Reward Model
                </span>
              </div>
            </div>

            <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full border border-status-success/40 bg-status-success/15 text-status-success font-semibold flex items-center gap-1 shadow-glow-success">
              <ShieldCheck className="h-3.5 w-3.5" />
              {job.nemotron_critique.verdict}
            </span>
          </div>

          <p className="text-xs text-text-secondary leading-relaxed">
            {job.nemotron_critique.verdict_summary}
          </p>

          {/* HelpSteer2 Rubric Metrics */}
          <div className="grid grid-cols-3 gap-2.5 pt-1 font-mono text-[11px]">
            <div className="p-2.5 rounded-lg bg-surface-1/90 border border-border/70 flex flex-col items-center shadow-xs">
              <span className="text-[10px] text-text-muted">Correctness</span>
              <span className="font-bold text-status-success text-sm mt-0.5">
                {job.nemotron_critique.helpsteer_scores.correctness}/5
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-1/90 border border-border/70 flex flex-col items-center shadow-xs">
              <span className="text-[10px] text-text-muted">Coherence</span>
              <span className="font-bold text-accent text-sm mt-0.5">
                {job.nemotron_critique.helpsteer_scores.coherence}/5
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-1/90 border border-border/70 flex flex-col items-center shadow-xs">
              <span className="text-[10px] text-text-muted">Safety</span>
              <span className="font-bold text-status-success text-sm mt-0.5">
                {job.nemotron_critique.helpsteer_scores.safety}/5
              </span>
            </div>
          </div>

          {/* Side Effects & Security Audits */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1">
            <div className="p-2 rounded bg-surface-1/70 border border-border/50 text-text-secondary">
              <span className="font-semibold text-text-primary block text-[10px] uppercase font-mono text-text-muted mb-0.5">
                Side-Effects Audit:
              </span>
              {job.nemotron_critique.side_effects_analysis}
            </div>
            <div className="p-2 rounded bg-surface-1/70 border border-border/50 text-text-secondary">
              <span className="font-semibold text-text-primary block text-[10px] uppercase font-mono text-text-muted mb-0.5">
                Security Audit:
              </span>
              {job.nemotron_critique.security_audit}
            </div>
          </div>
        </div>
      )}

      {/* Diff container */}
      <div className="rounded-md border border-border bg-surface-1 overflow-hidden shadow-xs">
        {/* Header bar */}
        <div className="border-b border-border bg-surface-2/60 px-3.5 py-2 flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            <span className="font-mono font-medium text-text-primary">
              Unified Diff
            </span>
            <div className="flex items-center gap-1.5 font-mono text-[11px]">
              <span className="text-status-success font-semibold">+{addedCount}</span>
              <span className="text-status-error font-semibold">-{removedCount}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 text-[11px] font-mono text-text-muted hover:text-text-primary transition-colors px-2 py-0.5 rounded hover:bg-surface-3"
          >
            <Copy className="h-3 w-3" />
            {copied ? "Copied!" : "Copy Diff"}
          </button>
        </div>

        {/* Diff content */}
        <div className="overflow-auto max-h-[480px] p-3 text-xs font-mono leading-5 select-text">
          <pre className="whitespace-pre">
            {diffLines.map((line, i) => {
              const isAdd = line.startsWith("+") && !line.startsWith("+++");
              const isDel = line.startsWith("-") && !line.startsWith("---");
              const isHunk = line.startsWith("@@");
              const isHeader = line.startsWith("---") || line.startsWith("+++");

              return (
                <div
                  key={i}
                  className={`px-2 py-0.2 rounded-xs flex ${
                    isAdd
                      ? "bg-status-success/15 text-status-success font-medium"
                      : isDel
                      ? "bg-status-error/15 text-status-error font-medium"
                      : isHunk
                      ? "bg-accent/10 text-accent font-semibold my-1"
                      : isHeader
                      ? "text-text-primary font-bold opacity-80"
                      : "text-text-secondary"
                  }`}
                >
                  <span className="w-8 shrink-0 text-text-muted select-none text-right pr-3 opacity-40">
                    {i + 1}
                  </span>
                  <span className="flex-1 break-all">{line || " "}</span>
                </div>
              );
            })}
          </pre>
        </div>
      </div>

      {/* Decision action bar */}
      {isAwaitingApproval && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-md border border-border bg-surface-2/40">
          <div className="text-xs text-text-secondary">
            Select an action to continue the workflow:
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={() => handleDecision("approved")}
              disabled={submitting}
              className="gap-1.5 bg-status-success text-surface hover:bg-status-success/90 font-medium text-xs h-8"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Approve Patch
            </Button>

            <Button
              variant="outline"
              onClick={() => setShowReviseModal(true)}
              disabled={submitting}
              className="gap-1.5 border-border hover:bg-surface-2 text-text-primary text-xs h-8"
            >
              <RotateCcw className="h-3.5 w-3.5 text-accent" />
              Request Revision
            </Button>

            <Button
              variant="outline"
              onClick={() => handleDecision("rejected")}
              disabled={submitting}
              className="gap-1.5 text-status-error border-status-error/40 hover:bg-status-error/10 text-xs h-8"
            >
              <XCircle className="h-3.5 w-3.5" />
              Reject
            </Button>
          </div>
        </div>
      )}

      {/* Display decision status if already determined */}
      {job.patch_approval && (
        <div
          className={`flex items-center justify-between p-3 rounded-md border text-xs font-mono ${
            job.patch_approval === "approved"
              ? "border-status-success/40 bg-status-success/10 text-status-success"
              : job.patch_approval === "revised"
              ? "border-accent/40 bg-accent/10 text-accent"
              : "border-status-error/40 bg-status-error/10 text-status-error"
          }`}
        >
          <span className="font-semibold capitalize">
            Patch Decision: {job.patch_approval}
          </span>
          {job.patch_feedback && (
            <span className="text-[11px] text-text-secondary truncate max-w-sm">
              Note: {job.patch_feedback}
            </span>
          )}
        </div>
      )}

      {error && (
        <div className="p-2.5 rounded border border-status-error/40 bg-status-error/10 text-xs text-status-error font-mono">
          {error}
        </div>
      )}

      {/* Revision Modal */}
      {showReviseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xs">
          <div className="relative w-full max-w-lg rounded-lg border border-border bg-surface-1 p-5 shadow-2xl space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-text-primary">
                Request Patch Revision
              </h3>
              <p className="text-xs text-text-secondary mt-1">
                Provide specific guidance or corrections to NVIDIA Nemotron for
                the next repair iteration.
              </p>
            </div>

            <Textarea
              value={revisionNotes}
              onChange={(e) => setRevisionNotes(e.target.value)}
              placeholder="e.g. Please ensure you raise ZeroDivisionError('division by zero') with the exact message, and don't change other arithmetic logic..."
              rows={4}
              className="font-mono text-xs bg-surface border-border focus:border-accent"
            />

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowReviseModal(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => handleDecision("revised", revisionNotes)}
                disabled={submitting || !revisionNotes.trim()}
                className="bg-accent text-surface hover:bg-accent-bright"
              >
                Submit Revision Request
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
