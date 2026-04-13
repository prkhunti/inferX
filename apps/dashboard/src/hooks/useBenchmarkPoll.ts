"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getBenchmark, getBenchmarkResults } from "@/lib/api";
import type { RunResults, RunSummary } from "@/lib/types";

const POLL_MS = 2000;

export function useBenchmarkPoll(runId: string | null) {
  const [summary, setSummary] = useState<RunSummary | null>(null);
  const [results, setResults] = useState<RunResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(async (id: string) => {
    try {
      const s = await getBenchmark(id);
      setSummary(s);

      if (s.status === "completed") {
        const r = await getBenchmarkResults(id);
        setResults(r);
        return; // stop polling
      }

      if (s.status === "failed") {
        setError(s.error ?? "Run failed");
        return;
      }

      // still running — schedule next poll
      timerRef.current = setTimeout(() => poll(id), POLL_MS);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Poll failed");
    }
  }, []);

  useEffect(() => {
    if (!runId) return;
    setResults(null);
    setError(null);
    poll(runId);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [runId, poll]);

  return { summary, results, error };
}
