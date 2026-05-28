from __future__ import annotations

import re
from pathlib import Path

from cyreneAI.core.errors.plugin import PluginInputError, PluginNotFoundError


class FileSystemPluginAssets:
    """
    文件系统插件只读资产目录表。
    """

    def __init__(self) -> None:
        self._asset_roots: dict[str, Path] = {}

    def register(self, plugin_id: str, assets_path: str | Path) -> None:
        self._asset_roots[_safe_plugin_id(plugin_id)] = Path(assets_path).resolve()

    def namespace(self, plugin_id: str) -> "FileSystemPluginAssetsNamespace":
        safe_plugin_id = _safe_plugin_id(plugin_id)
        root_path = self._asset_roots.get(safe_plugin_id)
        if root_path is None:
            raise PluginNotFoundError(f"插件 {plugin_id} 未注册 assets")
        return FileSystemPluginAssetsNamespace(root_path)

    async def close(self) -> None:
        self._asset_roots.clear()


class FileSystemPluginAssetsNamespace:
    """
    单个插件的只读资产命名空间。
    """

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path

    async def read_text(self, path: str) -> str:
        asset_path = self._asset_path(path)
        if not asset_path.is_file():
            raise PluginNotFoundError(f"Plugin asset {path} does not exist")
        return asset_path.read_text(encoding="utf-8")

    async def read_bytes(self, path: str) -> bytes:
        asset_path = self._asset_path(path)
        if not asset_path.is_file():
            raise PluginNotFoundError(f"Plugin asset {path} does not exist")
        return asset_path.read_bytes()

    async def exists(self, path: str) -> bool:
        return self._asset_path(path).exists()

    async def list(self, path: str = "") -> list[str]:
        asset_path = self._asset_path(path)
        if not asset_path.exists():
            return []
        if asset_path.is_file():
            return [asset_path.name]
        return sorted(
            child.relative_to(asset_path).as_posix()
            for child in asset_path.iterdir()
            if child.name != "__pycache__"
        )

    def _asset_path(self, path: str) -> Path:
        if Path(path).is_absolute():
            raise PluginInputError("Plugin asset path must be relative")
        candidate = (self._root_path / path).resolve()
        if candidate != self._root_path and not candidate.is_relative_to(
            self._root_path
        ):
            raise PluginInputError("Plugin asset path cannot escape assets root")
        return candidate


def _safe_plugin_id(plugin_id: str) -> str:
    normalized = plugin_id.strip()
    if not normalized:
        raise PluginInputError("Plugin plugin_id cannot be empty")
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", normalized)
