"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { generate, listModels } from "@/lib/api";
import { useStream } from "@/hooks/useStream";
import type { GenerateResponse, ModelProfile } from "@/lib/types";
import { Card, StatCard } from "@/components/ui/Card";
import { clsx } from "clsx";
import { Loader2, Square, Zap } from "lucide-react";

const DEFAULT_PROMPT =
  "Explain the tradeoff between batching and tail latency in LLM serving systems. Be concise.";

export default function PlaygroundPage() {
  const [models, setModels] = useState<ModelProfile[]>([]);
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(256);
  const [useStreamMode, setUseStreamMode] = useState(true);
  const [syncResult, setSyncResult] = useState<GenerateResponse | null>(null);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const { text, isStreaming, usage, latency, error: streamError, start, stop } = useStream();

  useEffect(() => {
    listModels()
      .then((m) => {
        setModels(m);
        if (m.length > 0) setSelectedModel(m[0].model_id);
      })
      .catch(() => {}); // models endpoint optional
  }, []);

  const handleSubmit = useCallback(async () => {
    setSyncResult(null);
    setSyncError(null);
    const req = { prompt, model: selectedModel, temperature, max_tokens: maxTokens, stream: useStreamMode };

    if (useStreamMode) {
      await start(req);
    } else {
      setSyncLoading(true);
      try {
        const res = await generate(req);
        setSyncResult(res);
      } catch (e: unknown) {
        setSyncError(e instanceof Error ? e.message : "Request failed");
      } finally {
        setSyncLoading(false);
      }
    }
  }, [prompt, selectedModel, temperature, maxTokens, useStreamMode, start]);

  const activeLatency = useStreamMode ? latency : syncResult?.latency ?? null;
  const activeUsage = useStreamMode ? usage : syncResult?.usage ?? null;
  const activeText = useStreamMode ? text : syncResult?.text ?? "";
  const activeError = useStreamMode ? streamError : syncError;
  const activeRequestId = syncResult?.request_id;
  const isLoading = useStreamMode ? isStreaming : syncLoading;

  return (
    <div className="h-full grid grid-cols-[1fr_320px] divide-x divide-zinc-800">
      {/* ── Left: prompt + output ── */}
      <div className="flex flex-col p-6 gap-4 overflow-auto">
        <div className="flex items-center justify-between">
          <h1 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest">
            Inference Playground
          </h1>
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <span>stream</span>
            <button
              onClick={() => setUseStreamMode((v) => !v)}
              className={clsx(
                "relative w-10 h-5 rounded-full transition-colors",
                useStreamMode ? "bg-sky-600" : "bg-zinc-700",
              )}
            >
              <span
                className={clsx(
                  "absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform",
                  useStreamMode ? "translate-x-5" : "translate-x-0.5",
                )}
              />
            </button>
            <span className={useStreamMode ? "text-sky-400" : "text-zinc-500"}>
              {useStreamMode ? "on" : "off"}
            </span>
          </div>
        </div>

        {/* Prompt */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-zinc-500">Prompt</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={5}
            className="w-full bg-zinc-900 border border-zinc-700 rounded p-3 text-sm text-zinc-100 resize-none focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600"
            placeholder="Enter a prompt…"
          />
        </div>

        {/* Submit */}
        <div className="flex gap-2">
          <button
            onClick={isLoading ? stop : handleSubmit}
            disabled={!prompt.trim()}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors",
              isLoading
                ? "bg-red-900/50 border border-red-700 text-red-300 hover:bg-red-900"
                : "bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-40 disabled:cursor-not-allowed",
            )}
          >
            {isLoading ? (
              <><Square className="w-3.5 h-3.5" /> Stop</>
            ) : (
              <><Zap className="w-3.5 h-3.5" /> Run</>
            )}
          </button>
          {isLoading && (
            <div className="flex items-center gap-1.5 text-xs text-zinc-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              {useStreamMode ? "Streaming…" : "Generating…"}
            </div>
          )}
        </div>

        {/* Output */}
        {(activeText || activeError) && (
          <Card className="flex-1 min-h-[180px]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-zinc-500 uppercase tracking-wider">Output</span>
              {activeRequestId && (
                <Link
                  href={`/requests/${activeRequestId}`}
                  className="text-xs text-sky-500 hover:text-sky-300"
                >
                  trace →
                </Link>
              )}
            </div>
            {activeError ? (
              <p className="text-sm text-red-400">{activeError}</p>
            ) : (
              <p className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">
                {activeText}
                {isStreaming && (
                  <span className="inline-block w-2 h-4 ml-0.5 bg-sky-400 animate-pulse align-middle" />
                )}
              </p>
            )}
          </Card>
        )}
      </div>

      {/* ── Right: config + timings ── */}
      <div className="flex flex-col p-6 gap-6 overflow-auto">
        {/* Config */}
        <section className="flex flex-col gap-4">
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Config</h2>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-zinc-500">Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
            >
              {models.length > 0
                ? models.map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.name}
                    </option>
                  ))
                : (
                    <>
                      <option value="gpt-4o-mini">gpt-4o-mini</option>
                      <option value="gpt-4o">gpt-4o</option>
                    </>
                  )}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-zinc-500">
              Temperature — <span className="text-zinc-300">{temperature}</span>
            </label>
            <input
              type="range"
              min={0} max={2} step={0.05}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="accent-sky-500"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-zinc-500">Max tokens</label>
            <input
              type="number"
              min={16} max={4096} step={16}
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              className="bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500 w-full"
            />
          </div>
        </section>

        {/* Timings */}
        {activeLatency && (
          <section className="flex flex-col gap-3">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Timings</h2>
            <StatCard label="TTFT" value={activeLatency.ttft_ms.toFixed(0)} unit="ms" accent />
            <StatCard label="Total latency" value={activeLatency.total_latency_ms.toFixed(0)} unit="ms" />
            <StatCard label="Tokens / sec" value={activeLatency.tokens_per_sec.toFixed(1)} accent />
            <StatCard label="Queue" value={activeLatency.queue_ms.toFixed(1)} unit="ms" />
          </section>
        )}

        {/* Usage */}
        {activeUsage && (
          <section className="flex flex-col gap-3">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Tokens</h2>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-zinc-900 border border-zinc-800 rounded p-3">
                <p className="text-zinc-500 mb-1">Prompt</p>
                <p className="text-zinc-100 tabular-nums">{activeUsage.prompt_tokens}</p>
              </div>
              <div className="bg-zinc-900 border border-zinc-800 rounded p-3">
                <p className="text-zinc-500 mb-1">Completion</p>
                <p className="text-zinc-100 tabular-nums">{activeUsage.completion_tokens}</p>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
