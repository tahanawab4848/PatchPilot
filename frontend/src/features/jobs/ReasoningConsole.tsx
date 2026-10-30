"use client";

import { useEffect, useRef, useState } from "react";
import {
  Check,
  Copy,
  Cpu,
  Download,
  Flame,
  Radio,
  Terminal,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { JobDetail } from "@/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ReasoningConsoleProps {
  job: JobDetail;
}

export function ReasoningConsole({ job }: ReasoningConsoleProps) {
  const [thoughts, setThoughts] = useState<string>(job.reasoning_log || "");
  const [copied, setCopied] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const isActive = [
    "analyzing",
    "reproducing",
    "diagnosing",
    "patch_proposed",
    "applying_patch",
    "verifying",
  ].includes(job.status);

  // Sync initial reasoning_log from job
  useEffect(() => {
    if (job.reasoning_log && job.reasoning_log.length > thoughts.length) {
      setThoughts(job.reasoning_log);
    }
  }, [job.reasoning_log, thoughts.length]);

  // Connect to live thought stream
  useEffect(() => {
    if (!job.id) return;

    let es: EventSource | null = null;
    try {
      es = new EventSource(`${BASE_URL}/api/v1/jobs/${job.id}/thoughts/stream`);
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.text) {
            setThoughts(data.text);
          } else if (data.chunk) {
            setThoughts((prev) => prev + data.chunk);
          }
        } catch {
          // ignore parsing error
        }
      };

      es.onerror = () => {
        es?.close();
      };
    } catch {
      // ignore
    }

    return () => {
      es?.close();
    };
  }, [job.id]);

  // Auto-scroll to bottom on new thoughts
  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [thoughts, autoScroll]);

  const handleCopy = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(thoughts);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const lines = thoughts.split("\n");

  return (
    <div className="rounded-md border border-border bg-[#0b0f17] overflow-hidden flex flex-col font-mono shadow-md">
      {/* Console Header Bar */}
      <div className="flex items-center justify-between border-b border-border/60 bg-[#111827] px-3.5 py-2 text-xs">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5">
            <span
              className={`h-2 w-2 rounded-full ${
                isActive
                  ? "bg-status-success animate-pulse shadow-xs shadow-status-success/50"
                  : "bg-text-muted"
              }`}
            />
            <span className="font-semibold text-text-primary text-[11px] uppercase tracking-wider flex items-center gap-1.5">
              <Terminal className="h-3.5 w-3.5 text-accent" />
              Live Nemotron-70B Reasoning Console
            </span>
          </div>

          <span className="hidden sm:inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30 font-medium">
            <Zap className="h-2.5 w-2.5 fill-accent" />
            Nebius Token Factory (FP8 HGX H100)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-[10px] text-text-muted flex items-center gap-1 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded bg-surface-2 border-border text-accent focus:ring-0 h-3 w-3"
            />
            <span>Auto-scroll</span>
          </label>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-6 px-2 text-[10px] text-text-muted hover:text-text-primary hover:bg-surface-2 gap-1"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-status-success" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                Copy
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Terminal Content Screen */}
      <div className="p-3.5 overflow-y-auto max-h-[500px] min-h-[300px] text-xs leading-relaxed select-text space-y-0.5">
        {!thoughts.trim() ? (
          <div className="flex items-center gap-2 text-text-muted italic py-6 px-2">
            <Radio className="h-4 w-4 animate-spin text-accent" />
            <span>Awaiting inference stream from Nebius Token Factory...</span>
          </div>
        ) : (
          lines.map((line, idx) => {
            const isStage = line.startsWith("[STAGE") || line.startsWith("[SYSTEM");
            const isPass = line.startsWith("[DUAL-PASS") || line.startsWith("[PASS");
            const isCheck = line.startsWith("✓");
            const isBullet = line.startsWith("►");
            const isDiff = line.startsWith("+") || line.startsWith("-");

            let lineClass = "text-text-secondary";
            if (isStage) {
              lineClass = "text-accent font-semibold pt-2 pb-0.5 border-b border-border/30";
            } else if (isPass) {
              lineClass = "text-status-warning font-semibold pt-2 pb-0.5";
            } else if (isCheck) {
              lineClass = "text-status-success font-semibold";
            } else if (isBullet) {
              lineClass = "text-text-primary font-medium pl-1";
            } else if (isDiff) {
              lineClass = line.startsWith("+")
                ? "text-status-success bg-status-success/10 px-1 rounded-xs"
                : "text-status-error bg-status-error/10 px-1 rounded-xs";
            }

            return (
              <div key={idx} className={`${lineClass} font-mono break-words`}>
                {line || " "}
              </div>
            );
          })
        )}

        {/* Live typing cursor */}
        {isActive && (
          <div className="flex items-center gap-1 text-accent pt-1">
            <span className="inline-block h-4 w-2 bg-accent animate-pulse" />
            <span className="text-[10px] text-text-muted italic">
              NVIDIA Nemotron-70B thinking token-by-token...
            </span>
          </div>
        )}

        <div ref={terminalEndRef} />
      </div>
    </div>
  );
}
