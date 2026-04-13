"use client";

import { useCallback, useRef, useState } from "react";
import { streamGenerate } from "@/lib/api";
import type { GenerateRequest, LatencyStats, UsageStats } from "@/lib/types";

interface StreamState {
  text: string;
  isStreaming: boolean;
  usage: UsageStats | null;
  latency: LatencyStats | null;
  error: string | null;
}

export function useStream() {
  const [state, setState] = useState<StreamState>({
    text: "",
    isStreaming: false,
    usage: null,
    latency: null,
    error: null,
  });

  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (req: GenerateRequest) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({ text: "", isStreaming: true, usage: null, latency: null, error: null });

    await streamGenerate(
      req,
      (token) => setState((s) => ({ ...s, text: s.text + token })),
      (usage, latency) =>
        setState((s) => ({ ...s, usage, latency, isStreaming: false })),
      (msg) => setState((s) => ({ ...s, error: msg, isStreaming: false })),
      ctrl.signal,
    );
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return { ...state, start, stop };
}
