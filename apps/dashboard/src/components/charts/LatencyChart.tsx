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
import type { CaseStats } from "@/lib/types";

interface Props {
  cases: CaseStats[];
}

function shortName(name: string) {
  // e.g. "suite__c5__p200__o150__sync" → "c5 p200 sync"
  return name
    .split("__")
    .slice(1)
    .map((s) => s.replace(/^[a-z]/, ""))
    .join(" ");
}

export function LatencyChart({ cases }: Props) {
  const data = cases.map((c) => ({
    name: shortName(c.case_name),
    P50: c.p50_latency_ms,
    P95: c.p95_latency_ms,
    P99: c.p99_latency_ms,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 16, bottom: 40, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis
          dataKey="name"
          tick={{ fill: "#71717a", fontSize: 10 }}
          angle={-35}
          textAnchor="end"
          interval={0}
        />
        <YAxis tick={{ fill: "#71717a", fontSize: 10 }} unit="ms" width={56} />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", fontSize: 12 }}
          formatter={(v: number) => [`${v.toFixed(1)} ms`]}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: "#a1a1aa", paddingTop: 8 }} />
        <Bar dataKey="P50" fill="#0ea5e9" radius={[2, 2, 0, 0]} />
        <Bar dataKey="P95" fill="#f59e0b" radius={[2, 2, 0, 0]} />
        <Bar dataKey="P99" fill="#ef4444" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
