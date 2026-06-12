from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends

from cyreneAI.application.runtime import CyreneAIRuntime
from cyreneAI.core.errors.base import CyreneAIError
from cyreneAI.core.schema.provider import (
    ProviderAdminStatus,
    ProviderConfig,
    ProviderConfigSummary,
    ProviderConnectionCheckResult,
    ProviderInfo,
    ProviderModel,
    ProviderOperationResult,
)
from cyreneAI.server.dependencies import get_runtime, require_admin
from cyreneAI.server.errors import raise_http_error
from cyreneAI.server.provider_admin import ProviderAdminService

router = APIRouter(
    prefix="/providers",
    tags=["providers"],
    dependencies=[Depends(require_admin)],
)


def get_provider_admin_service(
    runtime: CyreneAIRuntime = Depends(get_runtime),
) -> ProviderAdminService:
    return ProviderAdminService(runtime)


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


@router.get("/catalog", response_model=dict[str, list[ProviderInfo]])
async def list_provider_catalog(
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> dict[str, list[ProviderInfo]]:
    try:
        return {"providers": service.list_catalog()}
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.get("/configs", response_model=dict[str, list[ProviderConfigSummary]])
async def list_provider_configs(
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> dict[str, list[ProviderConfigSummary]]:
    try:
        return {"configs": await service.list_configs()}
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.get("/statuses", response_model=dict[str, list[ProviderAdminStatus]])
async def list_provider_statuses(
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> dict[str, list[ProviderAdminStatus]]:
    try:
        return {"providers": await service.list_statuses()}
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.get("/{provider_id}", response_model=ProviderAdminStatus)
async def inspect_provider(
    provider_id: str,
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> ProviderAdminStatus:
    try:
        return await service.inspect(provider_id)
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.put("/{provider_id}/config", response_model=ProviderAdminStatus)
async def upsert_provider_config(
    provider_id: str,
    body: ProviderConfig,
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> ProviderAdminStatus:
    try:
        return await service.upsert_config(provider_id, body)
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.delete("/{provider_id}/config", response_model=ProviderOperationResult)
async def delete_provider_config(
    provider_id: str,
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> ProviderOperationResult:
    try:
        return await service.delete_config(provider_id)
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.post("/{provider_id}/start", response_model=ProviderOperationResult)
async def start_provider(
    provider_id: str,
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> ProviderOperationResult:
    try:
        return await service.start(provider_id)
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.post("/{provider_id}/stop", response_model=ProviderOperationResult)
async def stop_provider(
    provider_id: str,
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> ProviderOperationResult:
    try:
        return await service.stop(provider_id)
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.post("/{provider_id}/reload", response_model=ProviderOperationResult)
async def reload_provider(
    provider_id: str,
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> ProviderOperationResult:
    try:
        return await service.reload(provider_id)
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.post("/{provider_id}/check", response_model=ProviderConnectionCheckResult)
async def check_provider(
    provider_id: str,
    service: ProviderAdminService = Depends(get_provider_admin_service),
) -> ProviderConnectionCheckResult:
    try:
        return await service.check(provider_id)
    except CyreneAIError as exc:
        raise_http_error(exc)


@router.get("/{provider_id}/models", response_model=dict[str, list[ProviderModel]])
async def list_provider_models(
    provider_id: str,
    runtime: CyreneAIRuntime = Depends(get_runtime),
) -> dict[str, list[ProviderModel]]:
    try:
        models = await runtime.provider_manager.list_models(provider_id)
    except CyreneAIError as exc:
        raise_http_error(exc)
    return {"models": models}
