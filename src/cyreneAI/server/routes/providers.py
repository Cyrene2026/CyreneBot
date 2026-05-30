from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException

from cyreneAI.application.runtime import CyreneAIRuntime
from cyreneAI.core.errors.base import CyreneAIError
from cyreneAI.server.dependencies import get_runtime, require_admin

router = APIRouter(
    prefix="/providers",
    tags=["providers"],
    dependencies=[Depends(require_admin)],
)


@router.get("")
async def list_providers(
    runtime: CyreneAIRuntime = Depends(get_runtime),
) -> dict[str, list[dict[str, Any]]]:
    return {
        "providers": [
            cast(dict[str, Any], info.model_dump(mode="json"))
            for info in runtime.provider_manager.list_running()
        ]
    }


@router.get("/{provider_id}/models")
async def list_provider_models(
    provider_id: str,
    runtime: CyreneAIRuntime = Depends(get_runtime),
) -> dict[str, list[dict[str, Any]]]:
    try:
        models = await runtime.provider_manager.list_models(provider_id)
    except CyreneAIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "models": [
            cast(dict[str, Any], model.model_dump(mode="json"))
            for model in models
        ]
    }
