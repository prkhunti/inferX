"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CaseStats } from "@/lib/types";

interface Props {
  cases: CaseStats[];
  /** Max number of series to draw before it gets unreadable. Default 6. */
  maxSeries?: number;
}

// Fixed percentile axis — every case maps onto the same X positions
const PERCENTILE_KEYS: Array<{ key: keyof CaseStats; label: string }> = [
  { key: "min_latency_ms",  label: "min"  },
  { key: "p25_latency_ms",  label: "P25"  },
  { key: "p50_latency_ms",  label: "P50"  },
  { key: "p75_latency_ms",  label: "P75"  },
  { key: "p90_latency_ms",  label: "P90"  },
  { key: "p95_latency_ms",  label: "P95"  },
  { key: "p99_latency_ms",  label: "P99"  },
  { key: "max_latency_ms",  label: "max"  },
];

// Distinct colours for up to 6 series
const PALETTE = [
  "#0ea5e9", "#34d399", "#f59e0b", "#f472b6", "#a78bfa", "#fb923c",
];

function shortName(name: string) {
  return name.split("__").slice(1).join(" ");
}

export function PercentileDistributionChart({ cases, maxSeries = 6 }: Props) {
  const series = cases.slice(0, maxSeries);

  // Build one row per percentile label, one column per case
  const data = PERCENTILE_KEYS.map(({ key, label }) => {
    const row: Record<string, string | number> = { pct: label };
    for (const c of series) {
      row[shortName(c.case_name)] = c[key] as number;
    }
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 4, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis
          dataKey="pct"
          tick={{ fill: "#71717a", fontSize: 11 }}
        />
        <YAxis
          tick={{ fill: "#71717a", fontSize: 10 }}
          unit="ms"
          width={56}
        />
        {/* Highlight the P95 / P99 tail region */}
        <ReferenceLine x="P95" stroke="#f59e0b" strokeDasharray="4 3" strokeOpacity={0.4} />
        <ReferenceLine x="P99" stroke="#ef4444" strokeDasharray="4 3" strokeOpacity={0.4} />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", fontSize: 12 }}
          formatter={(v: number) => [`${v.toFixed(1)} ms`]}
        />
        <Legend
          wrapperStyle={{ fontSize: 10, color: "#a1a1aa", paddingTop: 6 }}
          formatter={(value) => (
            <span style={{ color: "#a1a1aa" }} title={value}>
              {value.length > 24 ? value.slice(0, 22) + "…" : value}
            </span>
          )}
        />
        {series.map((c, i) => (
          <Line
            key={c.case_name}
            type="monotone"
            dataKey={shortName(c.case_name)}
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={{ r: 3, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
