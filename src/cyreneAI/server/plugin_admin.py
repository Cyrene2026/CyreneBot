from __future__ import annotations

from typing import Any

from cyreneAI.application.runtime import CyreneAIRuntime
from cyreneAI.bootstrap import load_filesystem_plugins
from cyreneAI.core.errors.plugin import PluginInputError, PluginStateError
from cyreneAI.core.plugin.project import (
    PLUGIN_SIGNATURE_FILENAME,
    load_plugin_manifest,
    plugin_manifest_isolation_mode,
    resolve_plugin_entrypoint,
    resolve_plugin_project_path,
    validate_plugin_project_signature,
)
from cyreneAI.core.plugin.runtime_capabilities import (
    list_plugin_runtime_dependencies,
    list_plugin_runtime_permissions,
)
from cyreneAI.core.schema.plugin import (
    PluginCommandDefinition,
    PluginDefinition,
    PluginEventDefinition,
    PluginIsolationMode,
    PluginMiddlewareDefinition,
    PluginRuntimeDependencyInfo,
    PluginRuntimePermissionInfo,
    PluginSourceInfo,
    PluginSignatureStatus,
    PluginStatusReport,
    PluginTaskDefinition,
    PluginTaskStatus,
)
from cyreneAI.core.schema.server import (
    PluginInstallReport,
    PluginInspectionReport,
    PluginOperationResult,
    PluginPathRequestBody,
    PluginPermissionAuditReport,
    PluginStorageKeysReport,
    PluginStorageValueReport,
    PluginTaskInstancesReport,
    PluginValidationReport,
)


class PluginAdminService:
    """
    Server 层插件管理用例编排。
    """

    def __init__(self, runtime: CyreneAIRuntime) -> None:
        self._runtime = runtime

    def list_plugins(self) -> list[PluginDefinition]:
        return self._plugin_manager().list_plugins()

    def list_commands(self) -> list[PluginCommandDefinition]:
        return self._plugin_manager().list_commands()

    def list_events(self) -> list[PluginEventDefinition]:
        return self._plugin_manager().list_events()

    def list_tasks(self) -> list[PluginTaskDefinition]:
        return self._plugin_manager().list_tasks()

    def list_middlewares(self) -> list[PluginMiddlewareDefinition]:
        return self._plugin_manager().list_middlewares()

    def list_statuses(self) -> list[PluginStatusReport]:
        return self._plugin_manager().list_statuses()

    def list_sources(self) -> list[PluginSourceInfo]:
        return self._plugin_manager().list_plugin_sources()

    def runtime_capabilities(
        self,
    ) -> dict[
        str,
        list[PluginRuntimePermissionInfo] | list[PluginRuntimeDependencyInfo],
    ]:
        return {
            "permissions": list_plugin_runtime_permissions(),
            "dependencies": list_plugin_runtime_dependencies(),
        }

    def validate_path(self, body: PluginPathRequestBody) -> PluginValidationReport:
        return _validate_plugin_project_path(body.path)

    def install_path(self, body: PluginPathRequestBody) -> PluginInstallReport:
        report = _validate_plugin_project_path(body.path)
        if not report.valid:
            detail = "; ".join(report.errors) or "Plugin path is invalid"
            raise PluginInputError(detail)

        definitions = load_filesystem_plugins(self._runtime, [body.path])
        manager = self._plugin_manager()
        return PluginInstallReport(
            installed=definitions,
            sources=[
                manager.get_plugin_source(definition.plugin_id)
                for definition in definitions
            ],
        )

    async def list_task_instances(
        self,
        *,
        plugin_id: str | None = None,
        task_name: str | None = None,
        status: list[str] | None = None,
    ) -> PluginTaskInstancesReport:
        scheduler = self._plugin_task_scheduler()
        return PluginTaskInstancesReport(
            tasks=await scheduler.list_tasks(
                plugin_id=plugin_id,
                task_name=task_name,
                statuses=_parse_task_statuses(status),
            )
        )

    async def cancel_task(self, task_id: str) -> PluginOperationResult:
        scheduler = self._plugin_task_scheduler()
        await scheduler.cancel_task(task_id)
        return PluginOperationResult(
            action="cancel_task",
            detail=f"Task {task_id} canceled",
            metadata={"task_id": task_id},
        )

    async def retry_task(self, task_id: str) -> PluginOperationResult:
        scheduler = self._plugin_task_scheduler()
        new_task_id = await scheduler.retry_task(task_id)
        return PluginOperationResult(
            action="retry_task",
            detail=f"Task {task_id} retried",
            metadata={"task_id": task_id, "new_task_id": new_task_id},
        )

    def get_plugin(self, plugin_id: str) -> PluginDefinition:
        return self._plugin_manager().get_plugin(plugin_id)

    def inspect_plugin(self, plugin_id: str) -> PluginInspectionReport:
        manager = self._plugin_manager()
        return PluginInspectionReport(
            definition=manager.get_plugin(plugin_id),
            status=manager.get_plugin_status(plugin_id),
            source=_get_plugin_source_or_none(manager, plugin_id),
            commands=manager.list_plugin_commands(plugin_id),
            events=manager.list_plugin_events(plugin_id),
            tasks=manager.list_plugin_tasks(plugin_id),
            middlewares=manager.list_plugin_middlewares(plugin_id),
        )

    def disable_plugin(self, plugin_id: str) -> PluginDefinition:
        return self._plugin_manager().disable_plugin(plugin_id)

    def enable_plugin(self, plugin_id: str) -> PluginDefinition:
        return self._plugin_manager().enable_plugin(plugin_id)

    def reload_plugin(self, plugin_id: str) -> PluginOperationResult:
        if self._runtime.plugin_host is None:
            raise PluginStateError("Plugin host is not configured")
        definition = self._runtime.plugin_host.reload(plugin_id)
        source = self._plugin_manager().get_plugin_source(plugin_id)
        return PluginOperationResult(
            action="reload",
            plugin_id=plugin_id,
            detail=f"Plugin {plugin_id} reloaded",
            metadata={
                "version": definition.version,
                "content_hash": source.content_hash,
                "signature_status": source.signature_status.value,
                "isolation_mode": source.isolation_mode.value,
            },
        )

    def list_plugin_commands(
        self,
        plugin_id: str,
    ) -> list[PluginCommandDefinition]:
        return self._plugin_manager().list_plugin_commands(plugin_id)

    def list_plugin_events(
        self,
        plugin_id: str,
    ) -> list[PluginEventDefinition]:
        return self._plugin_manager().list_plugin_events(plugin_id)

    def list_plugin_tasks(
        self,
        plugin_id: str,
    ) -> list[PluginTaskDefinition]:
        return self._plugin_manager().list_plugin_tasks(plugin_id)

    def list_plugin_middlewares(
        self,
        plugin_id: str,
    ) -> list[PluginMiddlewareDefinition]:
        return self._plugin_manager().list_plugin_middlewares(plugin_id)

    def get_plugin_status(self, plugin_id: str) -> PluginStatusReport:
        return self._plugin_manager().get_plugin_status(plugin_id)

    def list_permission_audit(self, plugin_id: str) -> PluginPermissionAuditReport:
        return PluginPermissionAuditReport(
            records=self._plugin_manager().list_permission_audit(plugin_id)
        )

    async def list_storage_keys(self, plugin_id: str) -> PluginStorageKeysReport:
        namespace = self._plugin_storage_namespace(plugin_id)
        return PluginStorageKeysReport(
            plugin_id=plugin_id,
            keys=await namespace.list_keys(),
        )

    async def get_storage_value(
        self,
        plugin_id: str,
        key: str,
    ) -> PluginStorageValueReport:
        namespace = self._plugin_storage_namespace(plugin_id)
        return PluginStorageValueReport(
            plugin_id=plugin_id,
            key=key,
            value=await namespace.get(key),
        )

    async def delete_storage_value(
        self,
        plugin_id: str,
        key: str,
    ) -> PluginOperationResult:
        namespace = self._plugin_storage_namespace(plugin_id)
        await namespace.delete(key)
        return PluginOperationResult(
            action="delete_storage_key",
            plugin_id=plugin_id,
            metadata={"key": key},
        )

    async def clear_storage(self, plugin_id: str) -> PluginOperationResult:
        namespace = self._plugin_storage_namespace(plugin_id)
        keys = await namespace.list_keys()
        for key in keys:
            await namespace.delete(key)
        return PluginOperationResult(
            action="clear_storage",
            plugin_id=plugin_id,
            metadata={"deleted_keys": keys},
        )

    def _plugin_manager(self):
        if self._runtime.plugin_manager is None:
            raise PluginStateError("Plugin manager is not configured")
        return self._runtime.plugin_manager

    def _plugin_task_scheduler(self) -> Any:
        if self._runtime.plugin_task_scheduler is None:
            raise PluginStateError("Plugin task scheduler is not configured")
        return self._runtime.plugin_task_scheduler

    def _plugin_storage_namespace(self, plugin_id: str) -> Any:
        if self._runtime.plugin_storage is None:
            raise PluginStateError("Plugin storage is not configured")
        if self._runtime.plugin_manager is not None:
            self._runtime.plugin_manager.get_plugin(plugin_id)
        return self._runtime.plugin_storage.namespace(plugin_id)


def _get_plugin_source_or_none(manager: Any, plugin_id: str) -> PluginSourceInfo | None:
    try:
        return manager.get_plugin_source(plugin_id)
    except PluginStateError:
        return None


def _validate_plugin_project_path(path: str) -> PluginValidationReport:
    try:
        project_path = resolve_plugin_project_path(path)
        manifest = load_plugin_manifest(project_path / "plugin.json")
        resolve_plugin_entrypoint(project_path, manifest)
        signature = validate_plugin_project_signature(project_path)
    except PluginInputError as exc:
        return PluginValidationReport(
            path=path,
            valid=False,
            errors=[str(exc)],
        )

    errors: list[str] = []
    warnings: list[str] = []
    signature_status = signature["status"]
    if signature_status in {
        PluginSignatureStatus.INVALID,
        PluginSignatureStatus.UNSUPPORTED,
    }:
        errors.append(
            "plugin signature validation failed: "
            f"{signature.get('error', 'unknown signature error')}"
        )
    elif signature_status == PluginSignatureStatus.UNSIGNED:
        warnings.append(f"plugin has no {PLUGIN_SIGNATURE_FILENAME} signature file")

    isolation_mode = plugin_manifest_isolation_mode(manifest)
    if isolation_mode != PluginIsolationMode.IN_PROCESS:
        warnings.append(
            f"plugin requests isolation mode {isolation_mode.value}, "
            "but the current runtime only supports in_process"
        )

    return PluginValidationReport(
        path=path,
        valid=not errors,
        plugin_id=manifest.plugin_id,
        warnings=warnings,
        errors=errors,
    )


def _parse_task_statuses(statuses: list[str] | None) -> list[PluginTaskStatus] | None:
    if not statuses:
        return None
    try:
        return [PluginTaskStatus(status) for status in statuses]
    except ValueError as exc:
        raise PluginInputError("Invalid plugin task status") from exc


__all__ = ["PluginAdminService"]
