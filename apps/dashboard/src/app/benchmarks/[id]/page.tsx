"use client";

import { use, useEffect } from "react";
import Link from "next/link";
import { useBenchmarkPoll } from "@/hooks/useBenchmarkPoll";
import { LatencyChart } from "@/components/charts/LatencyChart";
import { PercentileDistributionChart } from "@/components/charts/PercentileDistributionChart";
import { TailLatencyChart } from "@/components/charts/TailLatencyChart";
import { ThroughputChart } from "@/components/charts/ThroughputChart";
import { TTFTChart } from "@/components/charts/TTFTChart";
import { StatCard } from "@/components/ui/Card";
import type { CaseStats } from "@/lib/types";
import { clsx } from "clsx";
import { ArrowLeft, Loader2 } from "lucide-react";

function mean(arr: number[]) {
  return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0;
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">
      {children}
    </h2>
  );
}

function CaseTable({ cases }: { cases: CaseStats[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left border-collapse">
        <thead>
          <tr className="border-b border-zinc-800">
            {["Case", "Conc", "min", "P25", "P50", "P75", "P90", "P95", "P99", "max", "TTFT p50", "TTFT p95", "RPS", "TPS", "Err %", "Cost/req"].map((h) => (
              <th key={h} className="px-3 py-2 text-zinc-500 font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.case_name} className="border-b border-zinc-900 hover:bg-zinc-900/50 transition-colors">
              <td className="px-3 py-2 text-zinc-300 font-mono max-w-[200px] truncate" title={c.case_name}>
                {c.case_name.split("__").slice(1).join(" ")}
                {c.streaming && <span className="ml-1 text-sky-500">~</span>}
              </td>
              <td className="px-3 py-2 text-zinc-400 tabular-nums">{c.concurrency}</td>
              <td className="px-3 py-2 text-zinc-500 tabular-nums">{c.min_latency_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-zinc-400 tabular-nums">{c.p25_latency_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-sky-400 tabular-nums">{c.p50_latency_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-zinc-400 tabular-nums">{c.p75_latency_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-zinc-400 tabular-nums">{c.p90_latency_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-amber-400 tabular-nums">{c.p95_latency_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-red-400 tabular-nums">{c.p99_latency_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-zinc-600 tabular-nums">{c.max_latency_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-violet-400 tabular-nums">{c.p50_ttft_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-fuchsia-400 tabular-nums">{c.p95_ttft_ms.toFixed(0)}</td>
              <td className="px-3 py-2 text-emerald-400 tabular-nums">{c.throughput_rps.toFixed(2)}</td>
              <td className="px-3 py-2 text-indigo-400 tabular-nums">{c.throughput_tps.toFixed(1)}</td>
              <td className={clsx("px-3 py-2 tabular-nums", c.error_rate > 0.05 ? "text-red-400" : "text-zinc-400")}>
                {(c.error_rate * 100).toFixed(1)}%
              </td>
              <td className="px-3 py-2 text-zinc-400 tabular-nums">
                {c.avg_cost_per_request > 0 ? `$${c.avg_cost_per_request.toFixed(5)}` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ResultsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { summary, results, error } = useBenchmarkPoll(id);

  const cases = results?.cases ?? [];

  const summaryStats = cases.length > 0 ? {
    p95: mean(cases.map((c) => c.p95_latency_ms)).toFixed(0),
    avgTTFT: mean(cases.map((c) => c.avg_ttft_ms)).toFixed(0),
    maxRPS: Math.max(...cases.map((c) => c.throughput_rps)).toFixed(2),
    errRate: (mean(cases.map((c) => c.error_rate)) * 100).toFixed(1),
  } : null;

  return (
    <div className="p-6 flex flex-col gap-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/benchmarks" className="text-zinc-500 hover:text-zinc-300">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest">
            {summary?.suite_name ?? "Loading…"}
          </h1>
          <p className="text-xs text-zinc-600 mt-0.5">{id}</p>
        </div>
        {summary && (
          <span className={clsx(
            "ml-auto px-2 py-0.5 rounded text-xs font-medium",
            summary.status === "completed" ? "text-emerald-400 bg-emerald-950" :
            summary.status === "running" ? "text-sky-400 bg-sky-950" :
            summary.status === "failed" ? "text-red-400 bg-red-950" :
            "text-zinc-400 bg-zinc-800",
          )}>
            {summary.status}
          </span>
        )}
      </div>

      {/* Running indicator */}
      {summary?.status === "running" && (
        <div className="flex items-center gap-2 text-sm text-sky-400 bg-sky-950/40 border border-sky-900 rounded-lg px-4 py-3">
          <Loader2 className="w-4 h-4 animate-spin" />
          Running — {summary.total_cases} cases completed so far…
        </div>
      )}

      {/* Error */}
      {(error || summary?.error) && (
        <div className="text-sm text-red-400 bg-red-950/40 border border-red-900 rounded-lg px-4 py-3">
          {error ?? summary?.error}
        </div>
      )}

      {/* Summary stat cards */}
      {summaryStats && (
        <div className="grid grid-cols-4 gap-3">
          <StatCard label="Avg P95 latency" value={summaryStats.p95} unit="ms" accent />
          <StatCard label="Avg TTFT" value={summaryStats.avgTTFT} unit="ms" />
          <StatCard label="Peak RPS" value={summaryStats.maxRPS} accent />
          <StatCard label="Avg error rate" value={`${summaryStats.errRate}%`} />
        </div>
      )}

      {cases.length > 0 && (
        <>
          {/* Charts row 1 */}
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <SectionHeader>Latency Percentiles — P50 / P95 / P99 per case</SectionHeader>
              <LatencyChart cases={cases} />
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <SectionHeader>Throughput vs Concurrency</SectionHeader>
              <ThroughputChart cases={cases} />
            </div>
          </div>

          {/* Percentile distribution curve */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <div className="flex items-start justify-between mb-1">
              <SectionHeader>Latency Distribution — min → P99 curve</SectionHeader>
            </div>
            <p className="text-xs text-zinc-600 mb-3">
              Each line is one benchmark case. Steep rise after P90 indicates tail-latency pressure.
            </p>
            <PercentileDistributionChart cases={cases} />
          </div>

          {/* Tail latency vs concurrency */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <SectionHeader>Tail Latency vs Concurrency — P95 (solid) · P99 (dashed)</SectionHeader>
            <p className="text-xs text-zinc-600 mb-3">
              Widening gap between P95 and P99 under load signals queuing pressure.
            </p>
            <TailLatencyChart cases={cases} />
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <SectionHeader>Time to First Token (ms)</SectionHeader>
            <TTFTChart cases={cases} />
          </div>

          {/* Full results table */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <SectionHeader>All Cases</SectionHeader>
            <CaseTable cases={cases} />
          </div>

          {/* Cost summary */}
          {cases.some((c) => c.total_cost > 0) && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <SectionHeader>Cost Estimates</SectionHeader>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      {["Case", "Avg cost/req", "Cost/1k output tokens", "Total cost"].map((h) => (
                        <th key={h} className="px-3 py-2 text-zinc-500 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {cases.filter((c) => c.avg_cost_per_request > 0).map((c) => (
                      <tr key={c.case_name} className="border-b border-zinc-900">
                        <td className="px-3 py-2 text-zinc-300 font-mono">
                          {c.case_name.split("__").slice(1).join(" ")}
                        </td>
                        <td className="px-3 py-2 text-zinc-400 tabular-nums">${c.avg_cost_per_request.toFixed(5)}</td>
                        <td className="px-3 py-2 text-zinc-400 tabular-nums">${c.cost_per_1k_output_tokens.toFixed(4)}</td>
                        <td className="px-3 py-2 text-zinc-400 tabular-nums">${c.total_cost.toFixed(5)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty state while pending */}
      {summary?.status === "pending" && (
        <p className="text-sm text-zinc-600">Run is queued, waiting to start…</p>
      )}
    </div>
  );
}
