"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getRequest } from "@/lib/api";
import type { RequestRecord } from "@/lib/types";
import { ArrowLeft } from "lucide-react";
import { clsx } from "clsx";

function TimelineBar({
  label,
  start,
  width,
  color,
  value,
}: {
  label: string;
  start: number;
  width: number;
  color: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-32 text-right text-zinc-500 shrink-0">{label}</span>
      <div className="flex-1 relative h-5 bg-zinc-800 rounded overflow-hidden">
        <div
          className={clsx("absolute top-0 h-full rounded", color)}
          style={{ left: `${start}%`, width: `${Math.max(width, 0.5)}%` }}
        />
      </div>
      <span className="w-20 text-zinc-400 tabular-nums">{value}</span>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-4 text-xs border-b border-zinc-900 py-2">
      <span className="w-40 text-zinc-500 shrink-0">{label}</span>
      <span className="text-zinc-200 font-mono">{value}</span>
    </div>
  );
}

export default function RequestTracePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [req, setReq] = useState<RequestRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRequest(id).then(setReq).catch((e) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="p-6 text-sm text-red-400">{error}</div>
    );
  }

  if (!req) {
    return <div className="p-6 text-sm text-zinc-600">Loading…</div>;
  }

  const m = req.metric;

  // Build timeline segments (all relative to total_latency_ms = 100%)
  const total = m?.total_latency_ms ?? 1;
  const queue = m?.queue_ms ?? 0;
  const ttft = m?.ttft_ms ?? 0;
  const generation = total - ttft;

  const segments = [
    {
      label: "Queue",
      start: 0,
      width: (queue / total) * 100,
      color: "bg-zinc-600",
      value: `${queue.toFixed(1)} ms`,
    },
    {
      label: "Time to first token",
      start: (queue / total) * 100,
      width: (ttft / total) * 100,
      color: "bg-violet-600",
      value: `${ttft.toFixed(1)} ms`,
    },
    {
      label: "Token generation",
      start: ((queue + ttft) / total) * 100,
      width: (generation / total) * 100,
      color: "bg-sky-600",
      value: `${generation.toFixed(1)} ms`,
    },
  ];

  return (
    <div className="p-6 flex flex-col gap-6 max-w-3xl overflow-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/requests" className="text-zinc-500 hover:text-zinc-300">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest">
            Request Trace
          </h1>
          <p className="text-xs text-zinc-600 mt-0.5 font-mono">{id}</p>
        </div>
        <span className={clsx(
          "ml-auto px-2 py-0.5 rounded text-xs font-medium",
          req.status === "success" ? "text-emerald-400 bg-emerald-950" : "text-red-400 bg-red-950",
        )}>
          {req.status}
        </span>
      </div>

      {/* Metadata */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">Metadata</h2>
        <MetaRow label="Model" value={req.model} />
        <MetaRow label="Type" value={req.request_type} />
        <MetaRow label="Created at" value={new Date(req.created_at).toLocaleString()} />
        <MetaRow label="Prompt tokens" value={req.metric?.prompt_tokens ?? req.prompt_token_count ?? "—"} />
        <MetaRow label="Output tokens" value={m?.output_tokens ?? "—"} />
        <MetaRow label="Requested max tokens" value={req.requested_output_tokens} />
        {m?.error_message && (
          <MetaRow label="Error" value={<span className="text-red-400">{m.error_message}</span>} />
        )}
      </div>

      {/* Timeline */}
      {m && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-4">
            Request Timeline
          </h2>
          <div className="flex flex-col gap-3">
            {segments.map((s) => (
              <TimelineBar key={s.label} {...s} />
            ))}
          </div>
          <div className="mt-3 flex justify-end text-xs text-zinc-500">
            Total: <span className="ml-1 text-zinc-300 tabular-nums">{total.toFixed(1)} ms</span>
          </div>
        </div>
      )}

      {/* Latency stats */}
      {m && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">Latency</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Queue", value: `${queue.toFixed(1)} ms`, color: "text-zinc-400" },
              { label: "TTFT", value: `${ttft.toFixed(1)} ms`, color: "text-violet-400" },
              { label: "Total", value: `${total.toFixed(1)} ms`, color: "text-sky-400" },
              { label: "Tokens / sec", value: m.tokens_per_sec?.toFixed(1) ?? "—", color: "text-emerald-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-zinc-800/50 rounded p-3">
                <p className="text-xs text-zinc-500 mb-1">{label}</p>
                <p className={clsx("text-xl font-semibold tabular-nums", color)}>{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
