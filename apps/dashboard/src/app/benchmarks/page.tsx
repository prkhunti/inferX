"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { listBenchmarks, listModels, startBenchmark } from "@/lib/api";
import type { ModelProfile, RunSummary } from "@/lib/types";
import { Card } from "@/components/ui/Card";
import { clsx } from "clsx";
import { ChevronRight, Loader2, Play } from "lucide-react";

const STATUS_COLOR: Record<string, string> = {
  pending: "text-zinc-400 bg-zinc-800",
  running: "text-sky-400 bg-sky-950",
  completed: "text-emerald-400 bg-emerald-950",
  failed: "text-red-400 bg-red-950",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx("px-2 py-0.5 rounded text-xs font-medium", STATUS_COLOR[status] ?? "text-zinc-400 bg-zinc-800")}>
      {status}
    </span>
  );
}

export default function BenchmarksPage() {
  const [models, setModels] = useState<ModelProfile[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [suiteName, setSuiteName] = useState("my_experiment");
  const [model, setModel] = useState("gpt-4o-mini");
  const [concurrency, setConcurrency] = useState("1, 5, 10");
  const [promptLengths, setPromptLengths] = useState("100, 500");
  const [outputLengths, setOutputLengths] = useState("150");
  const [streaming, setStreaming] = useState(false);
  const [runsPerCase, setRunsPerCase] = useState(5);
  const [temperature, setTemperature] = useState(0.0);

  const parseInts = (val: string) =>
    val.split(",").map((v) => parseInt(v.trim())).filter((n) => !isNaN(n));

  const fetchRuns = useCallback(async () => {
    try {
      const r = await listBenchmarks();
      setRuns(r);
    } catch {}
  }, []);

  useEffect(() => {
    listModels().then(setModels).catch(() => {});
    fetchRuns();
  }, [fetchRuns]);

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      await startBenchmark({
        name: suiteName,
        model,
        concurrency_levels: parseInts(concurrency),
        prompt_lengths: parseInts(promptLengths),
        output_lengths: parseInts(outputLengths),
        streaming: [streaming],
        runs_per_case: runsPerCase,
        temperature,
      });
      await fetchRuns();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start run");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 grid grid-cols-[380px_1fr] gap-6 h-full overflow-auto">
      {/* ── Builder ── */}
      <div className="flex flex-col gap-5">
        <h1 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest">
          Benchmark Builder
        </h1>

        <Card className="flex flex-col gap-4">
          <Field label="Suite name">
            <input value={suiteName} onChange={(e) => setSuiteName(e.target.value)} className={inputCls} />
          </Field>

          <Field label="Model">
            <select value={model} onChange={(e) => setModel(e.target.value)} className={inputCls}>
              {models.length > 0
                ? models.map((m) => <option key={m.model_id} value={m.model_id}>{m.name}</option>)
                : <>
                    <option value="gpt-4o-mini">gpt-4o-mini</option>
                    <option value="gpt-4o">gpt-4o</option>
                  </>}
            </select>
          </Field>

          <Field label="Concurrency levels (comma-separated)">
            <input value={concurrency} onChange={(e) => setConcurrency(e.target.value)} className={inputCls} placeholder="1, 5, 10, 25" />
          </Field>

          <Field label="Prompt lengths — tokens (comma-separated)">
            <input value={promptLengths} onChange={(e) => setPromptLengths(e.target.value)} className={inputCls} placeholder="100, 500, 2000" />
          </Field>

          <Field label="Output lengths — max tokens (comma-separated)">
            <input value={outputLengths} onChange={(e) => setOutputLengths(e.target.value)} className={inputCls} placeholder="150, 400" />
          </Field>

          <Field label={`Runs per case — ${runsPerCase}`}>
            <input type="range" min={1} max={30} value={runsPerCase}
              onChange={(e) => setRunsPerCase(parseInt(e.target.value))}
              className="accent-sky-500 w-full" />
          </Field>

          <Field label={`Temperature — ${temperature}`}>
            <input type="range" min={0} max={2} step={0.05} value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="accent-sky-500 w-full" />
          </Field>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setStreaming((v) => !v)}
              className={clsx("relative w-10 h-5 rounded-full transition-colors flex-shrink-0",
                streaming ? "bg-sky-600" : "bg-zinc-700")}
            >
              <span className={clsx("absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform",
                streaming ? "translate-x-5" : "translate-x-0.5")} />
            </button>
            <span className="text-xs text-zinc-400">Include streaming cases</span>
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center justify-center gap-2 w-full py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm font-medium text-white disabled:opacity-40"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {loading ? "Starting…" : "Run Benchmark"}
          </button>
        </Card>

        {/* Case count preview */}
        <p className="text-xs text-zinc-600">
          {parseInts(concurrency).length} × {parseInts(promptLengths).length} × {parseInts(outputLengths).length}
          {streaming ? " × 2 (sync + stream)" : ""} × {runsPerCase} runs ={" "}
          <span className="text-zinc-400">
            {parseInts(concurrency).length *
              parseInts(promptLengths).length *
              parseInts(outputLengths).length *
              (streaming ? 2 : 1) *
              runsPerCase} total requests
          </span>
        </p>
      </div>

      {/* ── Run list ── */}
      <div className="flex flex-col gap-4 overflow-auto">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest">Runs</h2>
          <button onClick={fetchRuns} className="text-xs text-zinc-500 hover:text-zinc-300">
            refresh
          </button>
        </div>

        {runs.length === 0 ? (
          <p className="text-sm text-zinc-600">No runs yet. Start a benchmark above.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {runs.map((run) => (
              <Link key={run.id} href={`/benchmarks/${run.id}`}
                className="flex items-center justify-between bg-zinc-900 border border-zinc-800 hover:border-zinc-600 rounded-lg px-4 py-3 transition-colors group"
              >
                <div className="flex flex-col gap-1">
                  <span className="text-sm text-zinc-200 font-medium">{run.suite_name}</span>
                  <span className="text-xs text-zinc-500">
                    {run.started_at ? new Date(run.started_at).toLocaleString() : "—"} · {run.total_cases} cases
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={run.status} />
                  <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs text-zinc-500">{label}</label>
      {children}
    </div>
  );
}

const inputCls =
  "bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500 w-full";
