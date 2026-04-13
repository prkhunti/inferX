import type {
  BenchmarkSuiteConfig,
  CompareResponse,
  GenerateRequest,
  GenerateResponse,
  ModelProfile,
  RequestRecord,
  RunResults,
  RunSummary,
} from "./types";

const BASE = "/api";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

// ── Inference ──────────────────────────────────────────────────────────────

export function generate(req: GenerateRequest): Promise<GenerateResponse> {
  return post("/generate", req);
}

/** Returns a ReadableStream of SSE chunks for manual consumption. */
export async function streamGenerate(
  req: GenerateRequest,
  onToken: (token: string) => void,
  onDone: (usage: GenerateResponse["usage"], latency: GenerateResponse["latency"]) => void,
  onError: (msg: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    onError(err.detail ?? "Stream failed");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (raw === "[DONE]") return;

      try {
        const event = JSON.parse(raw);
        if (event.token) onToken(event.token);
        if (event.done) onDone(event.usage, event.latency);
        if (event.error) onError(event.error);
      } catch {
        // skip malformed chunk
      }
    }
  }
}

// ── Models ─────────────────────────────────────────────────────────────────

export function listModels(): Promise<ModelProfile[]> {
  return get("/models");
}

// ── Benchmarks ─────────────────────────────────────────────────────────────

export function startBenchmark(suite: BenchmarkSuiteConfig): Promise<RunSummary> {
  return post("/benchmarks/run", { suite });
}

export function listBenchmarks(): Promise<RunSummary[]> {
  return get("/benchmarks");
}

export function getBenchmark(id: string): Promise<RunSummary> {
  return get(`/benchmarks/${id}`);
}

export function getBenchmarkResults(id: string): Promise<RunResults> {
  return get(`/benchmarks/${id}/results`);
}

export function compareRuns(ids: string[]): Promise<CompareResponse> {
  return get(`/benchmarks/compare?ids=${ids.join(",")}`);
}

// ── Requests ───────────────────────────────────────────────────────────────

export function getRequest(id: string): Promise<RequestRecord> {
  return get(`/requests/${id}`);
}

export function listRequests(params?: {
  model?: string;
  request_type?: string;
  limit?: number;
}): Promise<RequestRecord[]> {
  const q = new URLSearchParams();
  if (params?.model) q.set("model", params.model);
  if (params?.request_type) q.set("request_type", params.request_type);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return get(`/requests${qs ? `?${qs}` : ""}`);
}
