from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from cyreneAI.core.errors.base import ConflictError
from cyreneAI.core.errors.plugin import PluginInputError
from cyreneAI.core.schema.plugin import (
    PluginDefinition,
    PluginIsolationMode,
    PluginManifest,
    PluginSignatureStatus,
    PluginSourceInfo,
    PluginSourceType,
)


class PluginInstallPolicy:
    """
    Central policy for production plugin install and reload decisions.
    """

    def __init__(
        self,
        *,
        allow_unsigned: bool = True,
        supported_isolation_modes: set[PluginIsolationMode] | None = None,
    ) -> None:
        self._allow_unsigned = allow_unsigned
        self._supported_isolation_modes = supported_isolation_modes or {
            PluginIsolationMode.IN_PROCESS
        }

    def validate_install(
        self,
        *,
        manifest: PluginManifest,
        source: PluginSourceInfo,
        installed_definitions: list[PluginDefinition],
        installed_sources: list[PluginSourceInfo] | None = None,
    ) -> tuple[str, ...]:
        warnings = list(self._validate_source_allowed(source))
        installed = _definition_by_plugin_id(installed_definitions, manifest.plugin_id)
        if installed is None:
            return tuple(warnings)

        installed_source = _source_by_plugin_id(
            installed_sources or [],
            manifest.plugin_id,
        )
        relation = compare_plugin_versions(manifest.version, installed.version)
        if relation < 0:
            raise ConflictError(
                f"plugin {manifest.plugin_id} downgrade rejected: "
                f"installed {installed.version}, candidate {manifest.version}"
            )
        if relation > 0:
            raise ConflictError(
                f"plugin {manifest.plugin_id} version {manifest.version} cannot be "
                f"installed over existing version {installed.version}; use reload"
            )

        if (
            installed_source is not None
            and installed_source.content_hash is not None
            and source.content_hash is not None
            and installed_source.content_hash != source.content_hash
        ):
            raise ConflictError(
                f"plugin {manifest.plugin_id} version {manifest.version} already "
                "exists with different content_hash"
            )
        raise ConflictError(
            f"plugin {manifest.plugin_id} version {manifest.version} is already installed"
        )

    def validate_reload(
        self,
        *,
        plugin_id: str,
        old_definition: PluginDefinition,
        old_source: PluginSourceInfo,
        new_manifest: PluginManifest,
        new_source: PluginSourceInfo,
    ) -> dict[str, Any]:
        self._validate_source_allowed(new_source)
        if new_manifest.plugin_id != plugin_id or new_source.plugin_id != plugin_id:
            raise ConflictError(
                f"plugin reload identity mismatch: expected {plugin_id}, "
                f"got {new_manifest.plugin_id}"
            )
        if old_source.source_type != new_source.source_type:
            raise ConflictError(
                f"plugin {plugin_id} reload source_type changed from "
                f"{old_source.source_type.value} to {new_source.source_type.value}"
            )
        if old_source.path is not None and new_source.path != old_source.path:
            raise ConflictError(
                f"plugin {plugin_id} reload path changed from "
                f"{old_source.path} to {new_source.path}"
            )

        relation = compare_plugin_versions(new_manifest.version, old_definition.version)
        if relation < 0:
            raise ConflictError(
                f"plugin {plugin_id} reload downgrade rejected: "
                f"installed {old_definition.version}, candidate {new_manifest.version}"
            )
        if (
            relation == 0
            and old_source.content_hash is not None
            and new_source.content_hash is not None
            and old_source.content_hash != new_source.content_hash
        ):
            raise ConflictError(
                f"plugin {plugin_id} version {new_manifest.version} content changed "
                "without a version bump"
            )

        return _reload_audit(
            old_definition=old_definition,
            old_source=old_source,
            new_manifest=new_manifest,
            new_source=new_source,
        )

    def _validate_source_allowed(
        self,
        source: PluginSourceInfo,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if source.source_type != PluginSourceType.FILESYSTEM:
            return tuple(warnings)
        if source.isolation_mode not in self._supported_isolation_modes:
            supported = ", ".join(
                sorted(mode.value for mode in self._supported_isolation_modes)
            )
            raise PluginInputError(
                f"plugin {source.plugin_id} isolation mode "
                f"{source.isolation_mode.value} is not supported; supported: {supported}"
            )
        if source.signature_status in {
            PluginSignatureStatus.INVALID,
            PluginSignatureStatus.UNSUPPORTED,
        }:
            raise PluginInputError(
                f"plugin {source.plugin_id} signature validation failed: "
                f"{source.signature_error or source.signature_status.value}"
            )
        if (
            source.signature_status == PluginSignatureStatus.UNSIGNED
            and not self._allow_unsigned
        ):
            raise PluginInputError(f"plugin {source.plugin_id} must be signed")
        if source.signature_status == PluginSignatureStatus.UNSIGNED:
            warnings.append(f"plugin {source.plugin_id} is unsigned")
        return tuple(warnings)


def compare_plugin_versions(left: str, right: str) -> int:
    left_key = _version_key(left)
    right_key = _version_key(right)
    if left_key < right_key:
        return -1
    if left_key > right_key:
        return 1
    return 0


def _version_key(value: str) -> tuple[tuple[int, int | str], ...]:
    parts: list[tuple[int, int | str]] = []
    for part in re.split(r"[.\-+_]", value.strip().lower()):
        if not part:
            continue
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    while parts and parts[-1] == (0, 0):
        parts.pop()
    return tuple(parts)


def _definition_by_plugin_id(
    definitions: list[PluginDefinition],
    plugin_id: str,
) -> PluginDefinition | None:
    for definition in definitions:
        if definition.plugin_id == plugin_id:
            return definition
    return None


def _source_by_plugin_id(
    sources: list[PluginSourceInfo],
    plugin_id: str,
) -> PluginSourceInfo | None:
    for source in sources:
        if source.plugin_id == plugin_id:
            return source
    return None


def _reload_audit(
    *,
    old_definition: PluginDefinition,
    old_source: PluginSourceInfo,
    new_manifest: PluginManifest,
    new_source: PluginSourceInfo,
) -> dict[str, Any]:
    return {
        "reloaded_at": datetime.now(UTC).isoformat(),
        "previous_version": old_definition.version,
        "version": new_manifest.version,
        "version_changed": old_definition.version != new_manifest.version,
        "previous_content_hash": old_source.content_hash,
        "content_hash": new_source.content_hash,
        "content_hash_changed": old_source.content_hash != new_source.content_hash,
        "previous_source_type": old_source.source_type.value,
        "source_type": new_source.source_type.value,
        "previous_path": old_source.path,
        "path": new_source.path,
        "path_changed": old_source.path != new_source.path,
        "previous_signature_status": old_source.signature_status.value,
        "signature_status": new_source.signature_status.value,
        "signature_status_changed": (
            old_source.signature_status != new_source.signature_status
        ),
    }


__all__ = ["PluginInstallPolicy", "compare_plugin_versions"]
