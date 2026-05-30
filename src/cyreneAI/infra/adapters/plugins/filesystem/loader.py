from __future__ import annotations

import importlib.util
import re
import sys
from contextlib import suppress
from pathlib import Path
from types import ModuleType
from typing import Any

from cyreneAI.core.errors.plugin import PluginConfigurationError, PluginInputError
from cyreneAI.core.plugin.project import (
    build_filesystem_plugin_source_info,
    load_plugin_manifest,
    resolve_plugin_entrypoint,
)
from cyreneAI.core.schema.plugin import (
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

    entrypoint = _resolve_entrypoint(project_path, manifest)

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
        return load_plugin_manifest(path)
    except PluginInputError as exc:
        raise PluginInputError(str(exc), cause=exc.cause) from exc


def _resolve_entrypoint(project_path: Path, manifest: PluginManifest) -> Path:
    try:
        return resolve_plugin_entrypoint(project_path, manifest)
    except PluginInputError as exc:
        raise PluginConfigurationError(str(exc), cause=exc) from exc


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
    source_info = build_filesystem_plugin_source_info(
        project_path,
        manifest,
        entrypoint,
    )
    if source_info.signature_status in {
        PluginSignatureStatus.INVALID,
        PluginSignatureStatus.UNSUPPORTED,
    }:
        raise PluginInputError(
            f"Plugin {manifest.plugin_id} signature validation failed: "
            f"{source_info.signature_error}"
        )
    return source_info
