from __future__ import annotations

import asyncio

import pytest

from cyreneAI.core.errors.plugin import PluginInputError, PluginNotFoundError
from cyreneAI.infra.adapters.plugins.filesystem import FileSystemPluginAssets


def test_filesystem_plugin_assets_reads_registered_namespace(tmp_path) -> None:
    async def run() -> None:
        assets_path = tmp_path / "demo_hello" / "assets"
        (assets_path / "prompts").mkdir(parents=True)
        (assets_path / "prompts" / "hello.txt").write_text(
            "Hello assets.",
            encoding="utf-8",
        )

        assets = FileSystemPluginAssets()
        assets.register("demo.hello", assets_path)
        namespace = assets.namespace("demo.hello")

        assert await namespace.exists("prompts/hello.txt") is True
        assert await namespace.read_text("prompts/hello.txt") == "Hello assets."
        assert await namespace.read_bytes("prompts/hello.txt") == b"Hello assets."
        assert await namespace.list("prompts") == ["hello.txt"]

    asyncio.run(run())


def test_filesystem_plugin_assets_rejects_path_escape(tmp_path) -> None:
    async def run() -> None:
        assets = FileSystemPluginAssets()
        assets.register("demo.hello", tmp_path / "assets")

        with pytest.raises(PluginInputError):
            await assets.namespace("demo.hello").read_text("../secret.txt")

    asyncio.run(run())


def test_filesystem_plugin_assets_requires_registered_plugin(tmp_path) -> None:
    assets = FileSystemPluginAssets()
    assets.register("demo.hello", tmp_path / "assets")

    with pytest.raises(PluginNotFoundError):
        assets.namespace("demo.missing")
