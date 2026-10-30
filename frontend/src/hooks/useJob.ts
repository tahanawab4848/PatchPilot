"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { jobsApi } from "@/lib/api-client";
import type { JobDetail } from "@/types/api";

const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * useJob hook providing real-time job updates via Server-Sent Events (SSE)
 * with graceful fallback to exponential-backoff polling.
 */
export function useJob(jobId: string | null, pollIntervalMs = 2000) {
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const isTerminalRef = useRef(false);

  const fetchJobDirectly = useCallback(async () => {
    if (!jobId) return;
    try {
      const data = await jobsApi.get(jobId);
      setJob(data);
      setError(null);
      if (TERMINAL_STATES.has(data.status)) {
        isTerminalRef.current = true;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch job.");
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setIsConnected(false);
      return;
    }

    setLoading(true);
    isTerminalRef.current = false;

    // Initial fetch to get state immediately
    fetchJobDirectly().finally(() => setLoading(false));

    // Attempt Server-Sent Events stream for zero-latency live updates
    let es: EventSource | null = null;
    let sseFailed = false;

    try {
      es = new EventSource(`${BASE_URL}/api/v1/jobs/${jobId}/stream`);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
      };

      es.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload && !payload.error) {
            setJob(payload as JobDetail);
            setError(null);
            if (TERMINAL_STATES.has(payload.status)) {
              isTerminalRef.current = true;
              es?.close();
              setIsConnected(false);
            }
          }
        } catch {
          // ignore parse glitch
        }
      };

      es.onerror = () => {
        // SSE disconnected or unsupported — fall back to polling
        setIsConnected(false);
        sseFailed = true;
        es?.close();
        schedulePolling();
      };
    } catch {
      sseFailed = true;
      schedulePolling();
    }

    function schedulePolling() {
      if (isTerminalRef.current) return;
      pollTimerRef.current = setTimeout(async () => {
        await fetchJobDirectly();
        if (!isTerminalRef.current) {
          schedulePolling();
        }
      }, pollIntervalMs);
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      setIsConnected(false);
    };
  }, [jobId, fetchJobDirectly, pollIntervalMs]);

  const refresh = useCallback(() => {
    return fetchJobDirectly();
  }, [fetchJobDirectly]);

  return { job, loading, error, isConnected, refresh };
}
