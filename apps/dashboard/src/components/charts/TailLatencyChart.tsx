"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CaseStats } from "@/lib/types";

interface Props {
  cases: CaseStats[];
}

/**
 * Shows how P95 and P99 latency grow as concurrency increases.
 *
 * When the benchmark has multiple prompt/output length combos, each unique
 * (prompt_length × output_length × streaming) combination gets its own pair
 * of lines so you can see which config is most sensitive to load.
 */
export function TailLatencyChart({ cases }: Props) {
  // Group by (prompt_length, output_length, streaming) — each group = 2 lines
  const groupKey = (c: CaseStats) =>
    `p${c.prompt_length} o${c.output_length}${c.streaming ? " ~stream" : ""}`;

  const groups = new Map<string, CaseStats[]>();
  for (const c of cases) {
    const k = groupKey(c);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k)!.push(c);
  }

  // Build one row per distinct concurrency level
  const concurrencies = [...new Set(cases.map((c) => c.concurrency))].sort((a, b) => a - b);

  const data = concurrencies.map((conc) => {
    const row: Record<string, number | string> = { concurrency: conc };
    for (const [label, groupCases] of groups) {
      const match = groupCases.find((c) => c.concurrency === conc);
      if (match) {
        row[`${label} P95`] = match.p95_latency_ms;
        row[`${label} P99`] = match.p99_latency_ms;
      }
    }
    return row;
  });

  // Assign colours: each group gets a hue, P95 solid, P99 dashed
  const groupLabels = [...groups.keys()];
  const BASE_COLORS = ["#0ea5e9", "#34d399", "#f59e0b", "#a78bfa", "#fb923c", "#f472b6"];

  const lines: Array<{ key: string; stroke: string; dash?: string }> = [];
  groupLabels.forEach((label, i) => {
    const color = BASE_COLORS[i % BASE_COLORS.length];
    lines.push({ key: `${label} P95`, stroke: color });
    lines.push({ key: `${label} P99`, stroke: color, dash: "5 3" });
  });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 4, right: 16, bottom: 20, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis
          dataKey="concurrency"
          tick={{ fill: "#71717a", fontSize: 10 }}
          label={{ value: "Concurrency", position: "insideBottom", offset: -10, fill: "#71717a", fontSize: 10 }}
        />
        <YAxis
          tick={{ fill: "#71717a", fontSize: 10 }}
          unit="ms"
          width={56}
        />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", fontSize: 12 }}
          formatter={(v: number) => [`${v.toFixed(1)} ms`]}
        />
        <Legend
          wrapperStyle={{ fontSize: 10, color: "#a1a1aa", paddingTop: 4 }}
          formatter={(value) => (
            <span style={{ color: "#a1a1aa" }}>
              {value}
            </span>
          )}
        />
        {lines.map(({ key, stroke, dash }) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={stroke}
            strokeWidth={2}
            strokeDasharray={dash}
            dot={{ r: 3, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
