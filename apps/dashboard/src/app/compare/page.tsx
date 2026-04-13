"use client";

import { useCallback, useEffect, useState } from "react";
import { compareRuns, listBenchmarks } from "@/lib/api";
import type { CompareResponse, CompareRunEntry, RunSummary } from "@/lib/types";
import { ComparisonBarChart, type CompareMetric } from "@/components/charts/ComparisonBarChart";
import { StatCard } from "@/components/ui/Card";
import { clsx } from "clsx";
import { GitCompare, Loader2 } from "lucide-react";

// ── Metric picker ──────────────────────────────────────────────────────────

const METRICS: Array<{ key: CompareMetric; label: string }> = [
  { key: "p50_latency_ms",       label: "P50 Latency"     },
  { key: "p95_latency_ms",       label: "P95 Latency"     },
  { key: "p99_latency_ms",       label: "P99 Latency"     },
  { key: "avg_ttft_ms",          label: "Avg TTFT"        },
  { key: "throughput_rps",       label: "Throughput RPS"  },
  { key: "throughput_tps",       label: "Throughput TPS"  },
  { key: "avg_cost_per_request", label: "Cost / request"  },
];

// ── Summary table ──────────────────────────────────────────────────────────

function mean(vals: number[]) {
  return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : 0;
}

/** For a metric, lower is better unless it's throughput. */
function lowerIsBetter(metric: CompareMetric) {
  return !metric.startsWith("throughput");
}

interface RunAggregate {
  run: CompareRunEntry;
  p50: number;
  p95: number;
  p99: number;
  ttft: number;
  rps: number;
  tps: number;
  cost: number;
}

function aggregate(run: CompareRunEntry): RunAggregate {
  const c = run.cases;
  return {
    run,
    p50:  mean(c.map((x) => x.p50_latency_ms)),
    p95:  mean(c.map((x) => x.p95_latency_ms)),
    p99:  mean(c.map((x) => x.p99_latency_ms)),
    ttft: mean(c.map((x) => x.avg_ttft_ms)),
    rps:  mean(c.map((x) => x.throughput_rps)),
    tps:  mean(c.map((x) => x.throughput_tps)),
    cost: mean(c.map((x) => x.avg_cost_per_request)),
  };
}

type AggKey = Exclude<keyof RunAggregate, "run">;

const SUMMARY_COLS: Array<{ key: AggKey; label: string; unit: string; lowerBetter: boolean }> = [
  { key: "p50",  label: "P50 ms",    unit: "ms",  lowerBetter: true  },
  { key: "p95",  label: "P95 ms",    unit: "ms",  lowerBetter: true  },
  { key: "p99",  label: "P99 ms",    unit: "ms",  lowerBetter: true  },
  { key: "ttft", label: "TTFT ms",   unit: "ms",  lowerBetter: true  },
  { key: "rps",  label: "RPS",       unit: "",    lowerBetter: false },
  { key: "tps",  label: "TPS",       unit: "",    lowerBetter: false },
  { key: "cost", label: "$/req",     unit: "$",   lowerBetter: true  },
];

function SummaryTable({ aggs }: { aggs: RunAggregate[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left border-collapse">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className="px-3 py-2 text-zinc-500 font-medium">Run / Model</th>
            {SUMMARY_COLS.map((c) => (
              <th key={c.key} className="px-3 py-2 text-zinc-500 font-medium whitespace-nowrap">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {aggs.map((agg) => (
            <tr key={agg.run.id} className="border-b border-zinc-900 hover:bg-zinc-900/50">
              <td className="px-3 py-2">
                <p className="text-zinc-200 font-medium">{agg.run.model}</p>
                <p className="text-zinc-600 mt-0.5">{agg.run.suite_name}</p>
              </td>
              {SUMMARY_COLS.map((col) => {
                const val = agg[col.key] as number;
                const best = col.lowerBetter
                  ? Math.min(...aggs.map((a) => a[col.key] as number))
                  : Math.max(...aggs.map((a) => a[col.key] as number));
                const isBest = Math.abs(val - best) < 0.0001;
                return (
                  <td
                    key={col.key}
                    className={clsx(
                      "px-3 py-2 tabular-nums font-mono",
                      isBest ? "text-emerald-400 font-semibold" : "text-zinc-400",
                    )}
                  >
                    {col.unit === "$"
                      ? val > 0 ? `$${val.toFixed(5)}` : "—"
                      : val.toFixed(col.key === "rps" || col.key === "tps" ? 2 : 0)}
                    {isBest && <span className="ml-1 text-emerald-600 text-[10px]">★</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function ComparePage() {
  const [allRuns, setAllRuns] = useState<RunSummary[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeMetric, setActiveMetric] = useState<CompareMetric>("p95_latency_ms");
  const [groupBy, setGroupBy] = useState<"concurrency" | "prompt_length" | "output_length">("concurrency");

  useEffect(() => {
    listBenchmarks()
      .then((runs) => setAllRuns(runs.filter((r) => r.status === "completed")))
      .catch(() => {});
  }, []);

  const toggleRun = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const handleCompare = useCallback(async () => {
    if (selected.size < 2) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await compareRuns([...selected]);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  }, [selected]);

  const aggs = result?.runs.map(aggregate) ?? [];

  return (
    <div className="p-6 grid grid-cols-[300px_1fr] gap-6 h-full overflow-auto">
      {/* ── Left: run selector ── */}
      <div className="flex flex-col gap-4">
        <h1 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest">
          Compare Runs
        </h1>
        <p className="text-xs text-zinc-600">
          Select two or more completed runs to compare models or configs side-by-side.
        </p>

        {allRuns.length === 0 ? (
          <p className="text-xs text-zinc-600">No completed runs yet.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {allRuns.map((run) => (
              <button
                key={run.id}
                onClick={() => toggleRun(run.id)}
                className={clsx(
                  "flex items-start gap-3 text-left px-3 py-2.5 rounded border transition-colors",
                  selected.has(run.id)
                    ? "border-sky-600 bg-sky-950/40"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-600",
                )}
              >
                <span className={clsx(
                  "mt-0.5 w-4 h-4 rounded shrink-0 border-2 flex items-center justify-center",
                  selected.has(run.id) ? "border-sky-500 bg-sky-500" : "border-zinc-600",
                )}>
                  {selected.has(run.id) && (
                    <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </span>
                <div className="min-w-0">
                  <p className="text-xs text-zinc-200 font-medium truncate">{run.suite_name}</p>
                  <p className="text-xs text-zinc-600 mt-0.5">{run.total_cases} cases</p>
                </div>
              </button>
            ))}
          </div>
        )}

        <button
          onClick={handleCompare}
          disabled={selected.size < 2 || loading}
          className="flex items-center justify-center gap-2 w-full py-2 rounded bg-sky-600 hover:bg-sky-500 text-sm font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed mt-auto"
        >
          {loading
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Comparing…</>
            : <><GitCompare className="w-4 h-4" /> Compare {selected.size > 0 ? `(${selected.size})` : ""}</>
          }
        </button>

        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>

      {/* ── Right: charts + table ── */}
      <div className="flex flex-col gap-6 overflow-auto">
        {!result && !loading && (
          <div className="flex items-center justify-center h-64 text-zinc-700 text-sm">
            Select runs on the left and click Compare.
          </div>
        )}

        {result && (
          <>
            {/* Headline stat cards */}
            <div className="grid grid-cols-4 gap-3">
              {aggs.map((agg) => (
                <StatCard
                  key={agg.run.id}
                  label={agg.run.model}
                  value={`${agg.p95.toFixed(0)} ms`}
                  unit="P95"
                />
              ))}
            </div>

            {/* Summary table */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">
                  Summary — averaged across all cases ★ = best
                </h2>
              </div>
              <SummaryTable aggs={aggs} />
            </div>

            {/* Chart controls */}
            <div className="flex items-center gap-4 flex-wrap">
              <span className="text-xs text-zinc-500">Metric:</span>
              <div className="flex flex-wrap gap-1">
                {METRICS.map((m) => (
                  <button
                    key={m.key}
                    onClick={() => setActiveMetric(m.key)}
                    className={clsx(
                      "px-2.5 py-1 rounded text-xs font-medium transition-colors",
                      activeMetric === m.key
                        ? "bg-sky-700 text-white"
                        : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700",
                    )}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              <span className="text-xs text-zinc-500 ml-4">Group by:</span>
              {(["concurrency", "prompt_length", "output_length"] as const).map((g) => (
                <button
                  key={g}
                  onClick={() => setGroupBy(g)}
                  className={clsx(
                    "px-2.5 py-1 rounded text-xs font-medium transition-colors",
                    groupBy === g
                      ? "bg-zinc-600 text-white"
                      : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700",
                  )}
                >
                  {g.replace("_", " ")}
                </button>
              ))}
            </div>

            {/* Main comparison chart */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-1">
                {METRICS.find((m) => m.key === activeMetric)?.label} by {groupBy.replace("_", " ")}
              </h2>
              <p className="text-xs text-zinc-600 mb-4">
                Each bar group is one {groupBy.replace("_", " ")} level. Bars within a group are the compared runs.
              </p>
              <ComparisonBarChart
                runs={result.runs}
                metric={activeMetric}
                groupBy={groupBy}
              />
            </div>

            {/* Always-visible P95 + TTFT side-by-side */}
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">P95 Latency</h2>
                <ComparisonBarChart runs={result.runs} metric="p95_latency_ms" groupBy={groupBy} />
              </div>
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">Avg TTFT</h2>
                <ComparisonBarChart runs={result.runs} metric="avg_ttft_ms" groupBy={groupBy} />
              </div>
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">Throughput (RPS)</h2>
                <ComparisonBarChart runs={result.runs} metric="throughput_rps" groupBy={groupBy} />
              </div>
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">Cost / Request</h2>
                <ComparisonBarChart runs={result.runs} metric="avg_cost_per_request" groupBy={groupBy} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
