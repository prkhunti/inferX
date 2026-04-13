import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.schemas.model_profile import model_registry

logger = logging.getLogger(__name__)

router = APIRouter()


class ModelProfileResponse(BaseModel):
    name: str
    provider: str
    model_id: str
    parameter_size: str
    backend_type: str
    max_context_tokens: int
    max_output_tokens: int
    quantization: Optional[str]
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    cost_per_1k_output_effective: float  # blended: includes typical input cost
    tags: list[str]
    notes: str


def _to_response(profile) -> ModelProfileResponse:
    return ModelProfileResponse(
        name=profile.name,
        provider=profile.provider,
        model_id=profile.model_id,
        parameter_size=profile.parameter_size,
        backend_type=profile.backend_type,
        max_context_tokens=profile.max_context_tokens,
        max_output_tokens=profile.max_output_tokens,
        quantization=profile.quantization,
        cost_per_1k_input_tokens=profile.cost_per_1k_input_tokens,
        cost_per_1k_output_tokens=profile.cost_per_1k_output_tokens,
        cost_per_1k_output_effective=profile.estimate_cost_per_1k_output(),
        tags=profile.tags,
        notes=profile.notes,
    )


@router.get("", response_model=list[ModelProfileResponse], summary="List all registered models")
async def list_models() -> list[ModelProfileResponse]:
    """Return all model profiles loaded from configs/model_profiles/."""
    return [_to_response(p) for p in model_registry.all()]


@router.get("/{name}", response_model=ModelProfileResponse, summary="Get a model profile by name")
async def get_model(name: str) -> ModelProfileResponse:
    profile = model_registry.get(name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Model {name!r} not found in registry")
    return _to_response(profile)
