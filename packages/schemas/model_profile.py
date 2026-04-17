"""Model profile — static metadata and pricing for a model.

Loaded from configs/model_profiles/*.yaml and held in a module-level registry
so all parts of the application can look up a model by name.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path("configs/model_profiles")


class ModelProfile(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(description="Canonical short name used in benchmark configs")
    provider: str = Field(description="API provider, e.g. openai, together, groq")
    model_id: str = Field(description="Exact model ID passed to the backend")
    parameter_size: str = Field(default="unknown", description="Human-readable size, e.g. ~8B")
    backend_type: str = Field(default="openai", description="Backend adapter to use")
    max_context_tokens: int = Field(default=8192)
    max_output_tokens: int = Field(default=4096)
    quantization: str | None = Field(default=None, description="e.g. int8, fp16, null")
    cost_per_1k_input_tokens: float = Field(default=0.0, description="USD per 1 000 input tokens")
    cost_per_1k_output_tokens: float = Field(default=0.0, description="USD per 1 000 output tokens")
    tags: list[str] = Field(default_factory=list)
    notes: str = Field(default="")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Return estimated USD cost for a single request."""
        input_cost = (prompt_tokens / 1000) * self.cost_per_1k_input_tokens
        output_cost = (completion_tokens / 1000) * self.cost_per_1k_output_tokens
        return round(input_cost + output_cost, 8)

    def estimate_cost_per_1k_output(self) -> float:
        """Effective cost per 1 000 output tokens (input assumed ~200 tokens)."""
        return round(
            (200 / 1000) * self.cost_per_1k_input_tokens
            + self.cost_per_1k_output_tokens,
            6,
        )


class ModelRegistry:
    """In-process registry of loaded model profiles."""

    def __init__(self) -> None:
        self._profiles: dict[str, ModelProfile] = {}

    def load_directory(self, directory: str | Path = _PROFILES_DIR) -> None:
        """Load all *.yaml files from a directory into the registry."""
        path = Path(directory)
        if not path.exists():
            logger.warning("model_profiles directory not found: %s", path)
            return

        for yaml_file in sorted(path.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                profile = ModelProfile(**data)
                self._profiles[profile.name] = profile
                logger.debug("model_registry.loaded name=%s", profile.name)
            except Exception as exc:
                logger.warning("model_registry.skip file=%s error=%s", yaml_file.name, exc)

        logger.info("model_registry.ready count=%d", len(self._profiles))

    def get(self, name: str) -> ModelProfile | None:
        return self._profiles.get(name)

    def all(self) -> list[ModelProfile]:
        return list(self._profiles.values())

    def names(self) -> list[str]:
        return list(self._profiles.keys())


# Module-level singleton — populated at app startup
model_registry = ModelRegistry()
