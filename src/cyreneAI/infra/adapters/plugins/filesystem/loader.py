from __future__ import annotations

import importlib.util
import hashlib
import json
import re
import sys
from contextlib import suppress
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from cyreneAI.core.errors.plugin import PluginConfigurationError, PluginInputError
from cyreneAI.core.schema.plugin import (
    PluginIsolationMode,
    PluginManifest,
    PluginSignatureStatus,
    PluginSourceInfo,
    PluginSourceType,
)
from cyreneAI.infra.adapters.plugins.filesystem.assets import FileSystemPluginAssets


class FileSystemPluginLoader:
    """
    文件系统插件加载器。
    """

    def __init__(
        self,
        path: str | Path,
        *,
        plugin_assets: FileSystemPluginAssets | None = None,
    ) -> None:
        self._path = Path(path)
        self._plugin_assets = plugin_assets

    def load(self) -> list[Any]:
        """
        加载插件入口对象。
        """
        if not self._path.exists():
            raise PluginConfigurationError(
                f"Plugin path {self._path} does not exist"
            )

        return [
            _load_plugin_project(path, plugin_assets=self._plugin_assets)
            for path in _plugin_project_paths(self._path)
        ]

    def reload_plugin(self, source: PluginSourceInfo) -> Any:
        """
        按已记录的文件系统来源重新加载单个插件。
        """
        if source.source_type != PluginSourceType.FILESYSTEM or source.path is None:
            raise PluginConfigurationError(
                f"Plugin {source.plugin_id} does not have a filesystem source"
            )
        return _load_plugin_project(
            Path(source.path),
            plugin_assets=self._plugin_assets,
        )


def _plugin_project_paths(path: Path) -> list[Path]:
    if path.is_file():
        if path.name != "plugin.json":
            raise PluginConfigurationError(
                f"Plugin file {path} must be named plugin.json"
            )
        return [path.parent]

    if not path.is_dir():
        raise PluginConfigurationError(
            f"Plugin path {path} must be a plugin.json file or directory"
        )

    if (path / "plugin.json").is_file():
        return [path]

    return [
        child
        for child in sorted(path.iterdir())
        if child.is_dir() and (child / "plugin.json").is_file()
    ]


def _load_plugin_project(
    project_path: Path,
    *,
    plugin_assets: FileSystemPluginAssets | None,
) -> Any:
    manifest = _load_manifest(project_path / "plugin.json")
    if plugin_assets is not None:
        plugin_assets.register(manifest.plugin_id, project_path / "assets")

    project_root = project_path.resolve()
    entrypoint = (project_path / manifest.entrypoint).resolve()
    if entrypoint != project_root and not entrypoint.is_relative_to(project_root):
        raise PluginConfigurationError(
            f"Plugin {manifest.plugin_id} entrypoint cannot escape plugin project"
        )
    if not entrypoint.is_file():
        raise PluginConfigurationError(
            f"Plugin {manifest.plugin_id} entrypoint {entrypoint} does not exist"
        )

    module = _load_entrypoint_module(
        entrypoint=entrypoint,
        plugin_id=manifest.plugin_id,
        project_path=project_path,
    )
    plugin = getattr(module, "plugin", None)
    if plugin is None:
        raise PluginConfigurationError(
            f"Plugin {manifest.plugin_id} entrypoint must define plugin"
        )

    configure = getattr(plugin, "configure", None)
    if configure is None:
        raise PluginConfigurationError(
            f"Plugin {manifest.plugin_id} object must support configure(manifest)"
        )
    configure(manifest)
    source_info = _build_source_info(project_path, manifest, entrypoint)
    setattr(plugin, "__cyreneai_plugin_source__", source_info)
    setattr(
        plugin,
        "__cyreneai_plugin_reloader__",
        FileSystemPluginLoader(project_path, plugin_assets=plugin_assets),
    )
    return plugin


def _load_manifest(path: Path) -> PluginManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise PluginInputError(
            f"Plugin manifest {path} must contain valid JSON",
            cause=exc,
        ) from exc

    try:
        return PluginManifest.model_validate(payload)
    except PydanticValidationError as exc:
        raise PluginInputError(
            f"Plugin manifest {path} contains invalid plugin metadata",
            cause=exc,
        ) from exc


def _load_entrypoint_module(
    *,
    entrypoint: Path,
    plugin_id: str,
    project_path: Path,
) -> ModuleType:
    module_name = _module_name(plugin_id, entrypoint)
    spec = importlib.util.spec_from_file_location(module_name, entrypoint)
    if spec is None or spec.loader is None:
        raise PluginConfigurationError(
            f"Plugin {plugin_id} entrypoint {entrypoint} cannot be loaded"
        )

    module = importlib.util.module_from_spec(spec)
    project_path_text = str(project_path.resolve())
    sys.path.insert(0, project_path_text)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise PluginConfigurationError(
            f"Plugin {plugin_id} entrypoint {entrypoint} import failed",
            cause=exc,
        ) from exc
    finally:
        sys.modules.pop(module_name, None)
        with suppress(ValueError):
            sys.path.remove(project_path_text)
    return module


def _module_name(plugin_id: str, entrypoint: Path) -> str:
    safe_plugin_id = re.sub(r"[^a-zA-Z0-9_]", "_", plugin_id)
    return f"_cyreneai_plugin_{safe_plugin_id}_{abs(hash(str(entrypoint)))}"


def _build_source_info(
    project_path: Path,
    manifest: PluginManifest,
    entrypoint: Path,
) -> PluginSourceInfo:
    project_root = project_path.resolve()
    content_hash = _project_content_hash(project_root)
    signature = _validate_signature(project_root, content_hash)
    if signature["status"] in {
        PluginSignatureStatus.INVALID,
        PluginSignatureStatus.UNSUPPORTED,
    }:
        raise PluginInputError(
            f"Plugin {manifest.plugin_id} signature validation failed: "
            f"{signature.get('error')}"
        )
    return PluginSourceInfo(
        plugin_id=manifest.plugin_id,
        source_type=PluginSourceType.FILESYSTEM,
        path=str(project_root),
        manifest_path=str((project_path / "plugin.json").resolve()),
        entrypoint=str(entrypoint),
        version=manifest.version,
        content_hash=content_hash,
        loaded_at=datetime.now(UTC),
        isolation_mode=_manifest_isolation_mode(manifest),
        signature_status=signature["status"],
        signature_path=signature.get("path"),
        signed_by=signature.get("signed_by"),
        signature_error=signature.get("error"),
    )


def _project_content_hash(project_path: Path) -> str:
    digest = hashlib.sha256()
    for path in _hashable_project_files(project_path):
        relative_path = path.relative_to(project_path).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _hashable_project_files(project_path: Path) -> list[Path]:
    ignored_names = {
        ".cyreneai-plugin-signature.json",
    }
    ignored_suffixes = {
        ".pyc",
        ".pyo",
    }
    files: list[Path] = []
    for path in project_path.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.name in ignored_names or path.suffix in ignored_suffixes:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(project_path).as_posix())


def _validate_signature(
    project_path: Path,
    content_hash: str,
) -> dict[str, Any]:
    signature_path = project_path / ".cyreneai-plugin-signature.json"
    if not signature_path.is_file():
        return {"status": PluginSignatureStatus.UNSIGNED}

    try:
        payload = json.loads(signature_path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise PluginInputError(
            f"Plugin signature {signature_path} must contain valid JSON",
            cause=exc,
        ) from exc

    algorithm = str(payload.get("algorithm", "")).lower()
    expected_hash = payload.get("content_hash")
    signed_by = payload.get("signed_by")
    if algorithm != "sha256":
        return {
            "status": PluginSignatureStatus.UNSUPPORTED,
            "path": str(signature_path.resolve()),
            "signed_by": signed_by if isinstance(signed_by, str) else None,
            "error": f"unsupported signature algorithm: {algorithm or '(missing)'}",
        }
    if expected_hash != content_hash:
        return {
            "status": PluginSignatureStatus.INVALID,
            "path": str(signature_path.resolve()),
            "signed_by": signed_by if isinstance(signed_by, str) else None,
            "error": "signature content_hash does not match plugin content",
        }
    return {
        "status": PluginSignatureStatus.VALID,
        "path": str(signature_path.resolve()),
        "signed_by": signed_by if isinstance(signed_by, str) else None,
    }


def _manifest_isolation_mode(manifest: PluginManifest) -> PluginIsolationMode:
    value = manifest.metadata.get("isolation")
    if isinstance(value, dict):
        value = value.get("mode")
    if isinstance(value, str):
        with suppress(ValueError):
            return PluginIsolationMode(value)
    return PluginIsolationMode.IN_PROCESS
