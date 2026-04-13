"""Benchmark suite definition — loaded from YAML config files."""

from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Iterator

import yaml
from pydantic import BaseModel, Field


class BenchmarkSuiteConfig(BaseModel):
    """Mirrors the YAML benchmark suite schema."""

    name: str
    model: str = "gpt-4o-mini"
    concurrency_levels: list[int] = Field(default=[1, 5, 10])
    prompt_lengths: list[int] = Field(default=[100, 500])  # approx tokens
    output_lengths: list[int] = Field(default=[100, 256])  # max_tokens
    streaming: list[bool] = Field(default=[False])
    runs_per_case: int = Field(default=5, ge=1, le=100)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "BenchmarkSuiteConfig":
        with open(path) as f:
            return cls(**yaml.safe_load(f))


class BenchmarkCase(BaseModel):
    """A single cell in the experiment grid."""

    suite_name: str
    model: str
    concurrency: int
    prompt_length: int   # target token count → drives synthetic prompt length
    output_length: int   # passed as max_tokens
    streaming: bool
    runs_per_case: int
    temperature: float

    @property
    def name(self) -> str:
        mode = "stream" if self.streaming else "sync"
        return (
            f"{self.suite_name}"
            f"__c{self.concurrency}"
            f"__p{self.prompt_length}"
            f"__o{self.output_length}"
            f"__{mode}"
        )


def expand_suite(cfg: BenchmarkSuiteConfig) -> list[BenchmarkCase]:
    """Cross-product expansion: every combination of concurrency × prompt × output × streaming."""
    cases = []
    for concurrency, prompt_len, output_len, use_stream in product(
        cfg.concurrency_levels,
        cfg.prompt_lengths,
        cfg.output_lengths,
        cfg.streaming,
    ):
        cases.append(BenchmarkCase(
            suite_name=cfg.name,
            model=cfg.model,
            concurrency=concurrency,
            prompt_length=prompt_len,
            output_length=output_len,
            streaming=use_stream,
            runs_per_case=cfg.runs_per_case,
            temperature=cfg.temperature,
        ))
    return cases


def synthetic_prompt(target_tokens: int) -> str:
    """Generate a synthetic prompt of approximately `target_tokens` tokens.

    Approximation: 1 token ≈ 4 characters (GPT tokenizer average).
    The prompt instructs the model to produce a specific length of output so
    benchmarks exercise the output side, not just the prompt side.
    """
    filler = (
        "The quick brown fox jumps over the lazy dog. "
        "In machine learning systems, latency and throughput are critical metrics. "
    )
    target_chars = target_tokens * 4
    repetitions = max(1, target_chars // len(filler) + 1)
    body = (filler * repetitions)[:target_chars]
    return f"Please summarize the following text concisely:\n\n{body}"
