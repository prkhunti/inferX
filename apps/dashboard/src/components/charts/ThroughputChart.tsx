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

export function ThroughputChart({ cases }: Props) {
  // One point per concurrency level; average RPS / TPS across prompt/output combos
  const byConc = new Map<number, { rps: number[]; tps: number[] }>();
  for (const c of cases) {
    if (!byConc.has(c.concurrency)) byConc.set(c.concurrency, { rps: [], tps: [] });
    byConc.get(c.concurrency)!.rps.push(c.throughput_rps);
    byConc.get(c.concurrency)!.tps.push(c.throughput_tps);
  }

  const data = Array.from(byConc.entries())
    .sort(([a], [b]) => a - b)
    .map(([conc, { rps, tps }]) => ({
      concurrency: conc,
      "RPS": parseFloat((rps.reduce((s, v) => s + v, 0) / rps.length).toFixed(2)),
      "TPS": parseFloat((tps.reduce((s, v) => s + v, 0) / tps.length).toFixed(1)),
    }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 16, bottom: 16, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis
          dataKey="concurrency"
          tick={{ fill: "#71717a", fontSize: 10 }}
          label={{ value: "Concurrency", position: "insideBottom", offset: -8, fill: "#71717a", fontSize: 10 }}
        />
        <YAxis yAxisId="rps" tick={{ fill: "#71717a", fontSize: 10 }} width={40} />
        <YAxis yAxisId="tps" orientation="right" tick={{ fill: "#71717a", fontSize: 10 }} width={48} />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: "#a1a1aa" }} />
        <Line yAxisId="rps" type="monotone" dataKey="RPS" stroke="#34d399" strokeWidth={2} dot={{ r: 4 }} />
        <Line yAxisId="tps" type="monotone" dataKey="TPS" stroke="#818cf8" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
