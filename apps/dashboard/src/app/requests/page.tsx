"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listRequests } from "@/lib/api";
import type { RequestRecord } from "@/lib/types";
import { clsx } from "clsx";
import { ChevronRight } from "lucide-react";

export default function RequestsPage() {
  const [requests, setRequests] = useState<RequestRecord[]>([]);
  const [model, setModel] = useState("");
  const [type, setType] = useState("");

  useEffect(() => {
    listRequests({ model: model || undefined, request_type: type || undefined, limit: 100 })
      .then(setRequests)
      .catch(() => {});
  }, [model, type]);

  return (
    <div className="p-6 flex flex-col gap-5 overflow-auto">
      <div className="flex items-center gap-4">
        <h1 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest">Requests</h1>
        <input
          placeholder="Filter by model…"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="bg-zinc-900 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-zinc-600 w-48"
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="bg-zinc-900 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-zinc-600"
        >
          <option value="">All types</option>
          <option value="generate">generate</option>
          <option value="stream">stream</option>
        </select>
      </div>

      {requests.length === 0 ? (
        <p className="text-sm text-zinc-600">No requests recorded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-zinc-800">
                {["Time", "Type", "Model", "Status", "Total ms", "TTFT ms", "Tokens/s", "Out tokens"].map((h) => (
                  <th key={h} className="px-3 py-2 text-zinc-500 font-medium whitespace-nowrap">{h}</th>
                ))}
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id} className="border-b border-zinc-900 hover:bg-zinc-900/50">
                  <td className="px-3 py-2 text-zinc-500 whitespace-nowrap">
                    {new Date(r.created_at).toLocaleTimeString()}
                  </td>
                  <td className="px-3 py-2">
                    <span className={clsx("px-1.5 py-0.5 rounded text-xs",
                      r.request_type === "stream" ? "bg-sky-950 text-sky-400" : "bg-zinc-800 text-zinc-400"
                    )}>
                      {r.request_type}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-zinc-300 font-mono">{r.model}</td>
                  <td className="px-3 py-2">
                    <span className={clsx("px-1.5 py-0.5 rounded text-xs",
                      r.status === "success" ? "bg-emerald-950 text-emerald-400" : "bg-red-950 text-red-400"
                    )}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-zinc-300 tabular-nums">
                    {r.metric?.total_latency_ms?.toFixed(0) ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-violet-400 tabular-nums">
                    {r.metric?.ttft_ms?.toFixed(0) ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-emerald-400 tabular-nums">
                    {r.metric?.tokens_per_sec?.toFixed(1) ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-zinc-400 tabular-nums">
                    {r.metric?.output_tokens ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <Link href={`/requests/${r.id}`} className="text-zinc-600 hover:text-zinc-300">
                      <ChevronRight className="w-4 h-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
