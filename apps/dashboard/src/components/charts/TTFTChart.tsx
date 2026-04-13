"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CaseStats } from "@/lib/types";

function shortName(name: string) {
  return name.split("__").slice(1).map((s) => s.replace(/^[a-z]/, "")).join(" ");
}

export function TTFTChart({ cases }: { cases: CaseStats[] }) {
  const data = cases.map((c) => ({
    name: shortName(c.case_name),
    "Avg TTFT": c.avg_ttft_ms,
    "P95 TTFT": c.p95_ttft_ms,
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
        <Bar dataKey="Avg TTFT" fill="#a78bfa" radius={[2, 2, 0, 0]} />
        <Bar dataKey="P95 TTFT" fill="#f472b6" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
