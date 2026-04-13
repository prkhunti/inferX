export interface ModelProfile {
  name: string;
  provider: string;
  model_id: string;
  parameter_size: string;
  backend_type: string;
  max_context_tokens: number;
  max_output_tokens: number;
  quantization: string | null;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  cost_per_1k_output_effective: number;
  tags: string[];
  notes: string;
}

export interface UsageStats {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface LatencyStats {
  queue_ms: number;
  ttft_ms: number;
  total_latency_ms: number;
  tokens_per_sec: number;
}

export interface GenerateResponse {
  request_id: string;
  model: string;
  text: string;
  usage: UsageStats;
  latency: LatencyStats;
}

export interface GenerateRequest {
  prompt: string;
  model: string;
  temperature: number;
  max_tokens: number;
  stream: boolean;
}

// Benchmark types
export interface BenchmarkSuiteConfig {
  name: string;
  model: string;
  concurrency_levels: number[];
  prompt_lengths: number[];
  output_lengths: number[];
  streaming: boolean[];
  runs_per_case: number;
  temperature: number;
}

export interface RunSummary {
  id: string;
  suite_name: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string | null;
  completed_at: string | null;
  total_cases: number;
  error: string | null;
}

export interface CaseStats {
  case_name: string;
  model: string;
  concurrency: number;
  prompt_length: number;
  output_length: number;
  streaming: boolean;
  total_requests: number;
  successful_requests: number;
  error_rate: number;
  // Full latency distribution
  min_latency_ms: number;
  p25_latency_ms: number;
  p50_latency_ms: number;
  p75_latency_ms: number;
  p90_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  max_latency_ms: number;
  avg_latency_ms: number;
  // TTFT distribution
  avg_ttft_ms: number;
  p50_ttft_ms: number;
  p95_ttft_ms: number;
  p99_ttft_ms: number;
  // Throughput
  throughput_rps: number;
  throughput_tps: number;
  wall_time_sec: number;
  avg_cost_per_request: number;
  total_cost: number;
  cost_per_1k_output_tokens: number;
}

export interface RunResults {
  id: string;
  suite_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  cases: CaseStats[];
}

export interface CompareRunEntry {
  id: string;
  suite_name: string;
  model: string;
  started_at: string | null;
  cases: CaseStats[];
}

export interface CompareResponse {
  runs: CompareRunEntry[];
}

// Request trace types
export interface RequestMetricRecord {
  queue_ms: number | null;
  ttft_ms: number | null;
  total_latency_ms: number | null;
  prompt_tokens: number | null;
  output_tokens: number | null;
  tokens_per_sec: number | null;
  success: boolean;
  error_message: string | null;
}

export interface RequestRecord {
  id: string;
  request_type: string;
  model: string;
  prompt_token_count: number | null;
  requested_output_tokens: number;
  status: string;
  created_at: string;
  metric: RequestMetricRecord | null;
}
