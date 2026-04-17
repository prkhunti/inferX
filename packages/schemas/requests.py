from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Input prompt text")
    model: str = Field(default="gpt-4o-mini", description="Model name to use for generation")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=512, gt=0, le=8192, description="Maximum output tokens")
    stream: bool = Field(default=False, description="Enable token streaming")

    model_config = {"json_schema_extra": {"example": {
        "prompt": "Explain dynamic batching in LLM serving in two sentences.",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 256,
        "stream": False,
    }}}
