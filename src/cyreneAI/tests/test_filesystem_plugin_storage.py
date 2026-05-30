from __future__ import annotations

import asyncio

import pytest

from cyreneAI.core.errors.plugin import PluginInputError
from cyreneAI.infra.adapters.plugins.filesystem import FileSystemPluginStorage


def test_filesystem_plugin_storage_persists_namespaced_values(tmp_path) -> None:
    async def run() -> None:
        storage = FileSystemPluginStorage(tmp_path)
        namespace = storage.namespace("demo.hello")

        await namespace.set("ban_list", {"users": ["user-1"]})
        await namespace.set("state", {"ready": True})

        next_storage = FileSystemPluginStorage(tmp_path)
        next_namespace = next_storage.namespace("demo.hello")
        assert await next_namespace.get("ban_list") == {"users": ["user-1"]}
        assert await next_namespace.list_keys() == ["ban_list", "state"]
        assert await next_storage.namespace("demo.other").get("ban_list", {}) == {}

    asyncio.run(run())


def test_filesystem_plugin_storage_updates_under_host_lock(tmp_path) -> None:
    async def run() -> None:
        storage = FileSystemPluginStorage(tmp_path)
        namespace = storage.namespace("demo.counter")

        async def increment(value):
            return {"count": value["count"] + 1}

        await namespace.update("state", increment, default={"count": 0})
        updated = await namespace.update("state", increment, default={"count": 0})

        assert updated == {"count": 2}
        assert await namespace.get("state") == {"count": 2}

    asyncio.run(run())


def test_filesystem_plugin_storage_rejects_non_json_values(tmp_path) -> None:
    async def run() -> None:
        storage = FileSystemPluginStorage(tmp_path)
        namespace = storage.namespace("demo.bad")

        with pytest.raises(PluginInputError):
            await namespace.set("bad", object())

    asyncio.run(run())
