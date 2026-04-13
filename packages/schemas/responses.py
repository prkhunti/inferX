from pydantic import BaseModel, Field


class UsageStats(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LatencyStats(BaseModel):
    queue_ms: float = Field(description="Time from request acceptance to processing start")
    ttft_ms: float = Field(description="Time from processing start to first token emitted")
    total_latency_ms: float = Field(description="Time from request acceptance to final token")
    tokens_per_sec: float = Field(description="Output tokens / active generation time")


class GenerateResponse(BaseModel):
    request_id: str
    model: str
    text: str
    usage: UsageStats
    latency: LatencyStats
