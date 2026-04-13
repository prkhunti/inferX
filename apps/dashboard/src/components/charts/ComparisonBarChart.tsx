"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CompareRunEntry } from "@/lib/types";

const PALETTE = ["#0ea5e9", "#34d399", "#f59e0b", "#f472b6", "#a78bfa", "#fb923c"];

export type CompareMetric =
  | "p50_latency_ms"
  | "p95_latency_ms"
  | "p99_latency_ms"
  | "avg_ttft_ms"
  | "throughput_rps"
  | "throughput_tps"
  | "avg_cost_per_request";

const METRIC_LABELS: Record<CompareMetric, { label: string; unit: string }> = {
  p50_latency_ms:       { label: "P50 Latency",   unit: "ms"  },
  p95_latency_ms:       { label: "P95 Latency",   unit: "ms"  },
  p99_latency_ms:       { label: "P99 Latency",   unit: "ms"  },
  avg_ttft_ms:          { label: "Avg TTFT",       unit: "ms"  },
  throughput_rps:       { label: "Throughput",     unit: "RPS" },
  throughput_tps:       { label: "Token Throughput", unit: "TPS" },
  avg_cost_per_request: { label: "Cost / request", unit: "USD" },
};

interface Props {
  runs: CompareRunEntry[];
  metric: CompareMetric;
  /** Group X-axis by this field. Default: concurrency. */
  groupBy?: "concurrency" | "prompt_length" | "output_length";
}

function runLabel(run: CompareRunEntry) {
  return `${run.model} (${run.suite_name})`;
}

/** Average a metric across all cases that share the same groupBy value. */
function buildData(
  runs: CompareRunEntry[],
  metric: CompareMetric,
  groupBy: "concurrency" | "prompt_length" | "output_length",
) {
  // Collect all distinct groupBy values across all runs
  const xValues = [...new Set(
    runs.flatMap((r) => r.cases.map((c) => c[groupBy] as number)),
  )].sort((a, b) => a - b);

  return xValues.map((xVal) => {
    const row: Record<string, number | string> = { x: xVal };
    for (const run of runs) {
      const matching = run.cases.filter((c) => c[groupBy] === xVal);
      if (matching.length === 0) continue;
      const avg = matching.reduce((s, c) => s + (c[metric] as number), 0) / matching.length;
      row[runLabel(run)] = parseFloat(avg.toFixed(4));
    }
    return row;
  });
}

export function ComparisonBarChart({ runs, metric, groupBy = "concurrency" }: Props) {
  const data = buildData(runs, metric, groupBy);
  const { unit } = METRIC_LABELS[metric];

  const xLabel = groupBy === "concurrency"
    ? "Concurrency"
    : groupBy === "prompt_length"
    ? "Prompt tokens"
    : "Output tokens";

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 16, bottom: 24, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis
          dataKey="x"
          tick={{ fill: "#71717a", fontSize: 10 }}
          label={{ value: xLabel, position: "insideBottom", offset: -12, fill: "#71717a", fontSize: 10 }}
        />
        <YAxis
          tick={{ fill: "#71717a", fontSize: 10 }}
          unit={` ${unit}`}
          width={64}
          tickFormatter={(v) =>
            unit === "USD" ? `$${Number(v).toFixed(4)}` : v
          }
        />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", fontSize: 12 }}
          formatter={(v: number, name: string) => [
            unit === "USD" ? `$${v.toFixed(5)}` : `${v.toFixed(2)} ${unit}`,
            name,
          ]}
        />
        <Legend
          wrapperStyle={{ fontSize: 10, color: "#a1a1aa", paddingTop: 4 }}
          formatter={(value) => (
            <span style={{ color: "#a1a1aa" }} title={value}>
              {value.length > 32 ? value.slice(0, 30) + "…" : value}
            </span>
          )}
        />
        {runs.map((run, i) => (
          <Bar
            key={run.id}
            dataKey={runLabel(run)}
            fill={PALETTE[i % PALETTE.length]}
            radius={[2, 2, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
