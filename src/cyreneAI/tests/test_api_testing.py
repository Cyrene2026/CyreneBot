from __future__ import annotations

import asyncio

import pytest

from cyreneAI.api import CyreneBot, CyreneRouter, Depends, PluginTestClient
from cyreneAI.core.errors.plugin import PluginAuthorizationError
from cyreneAI.core.schema.plugin import PluginEventResult, PluginTaskResult


def test_plugin_test_client_executes_command_without_full_runtime() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        @plugin.command("/hello")
        async def hello(name):
            return f"Hello, {name}!"

        client = PluginTestClient(plugin)
        result = await client.command("/hello Cyrene")

        assert result.texts == ["Hello, Cyrene!"]
        assert result.handled is True

    asyncio.run(run())


def test_plugin_test_client_uses_defaults_for_untyped_arguments() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        @plugin.command("/hello")
        async def hello(name="world"):
            return f"Hello, {name}!"

        client = PluginTestClient(plugin)
        result = await client.command("/hello")

        assert result.texts == ["Hello, world!"]

    asyncio.run(run())


def test_plugin_test_client_binds_typed_arguments() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        @plugin.command("/repeat")
        async def repeat(word: str, count: int = 1, excited: bool = False):
            suffix = "!" if excited else "."
            return " ".join([word] * count) + suffix

        client = PluginTestClient(plugin)

        result = await client.command("/repeat hi 3 yes")

        assert result.texts == ["hi hi hi!"]

    asyncio.run(run())


def test_plugin_test_client_infers_argument_types_from_defaults() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        @plugin.command("/repeat")
        async def repeat(word="hi", count=1, excited=False):
            suffix = "!" if excited else "."
            return " ".join([word] * count) + suffix

        client = PluginTestClient(plugin)

        result = await client.command("/repeat yo 2 on")

        assert result.texts == ["yo yo!"]

    asyncio.run(run())


def test_plugin_test_client_collects_yielded_text_replies() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        @plugin.command("/story")
        async def story(request, ctx):
            yield "Once."
            yield "Then."

        client = PluginTestClient(plugin)
        result = await client.command("/story")

        assert result.texts == ["Once.", "Then."]

    asyncio.run(run())


def test_plugin_test_client_injects_dependency_overrides() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        class FakeLLM:
            async def chat(self, prompt: str) -> str:
                return f"fake: {prompt}"

        @plugin.command("/ask")
        async def ask(request, llm=Depends("llm")):
            return await llm.chat(request.command.args_text)

        client = PluginTestClient(plugin, dependencies={"llm": FakeLLM()})
        result = await client.command("/ask hello")

        assert result.texts == ["fake: hello"]

    asyncio.run(run())


def test_plugin_test_client_uses_longest_command_match_and_aliases() -> None:
    async def run() -> None:
        plugin = CyreneBot()
        router = CyreneRouter(prefix="/sf")

        @router.command("/ban", aliases=["b"])
        async def ban(request, ctx):
            return request.command.args_text

        plugin.include_router(router)
        client = PluginTestClient(plugin)

        direct_result = await client.command('/sf ban "user 1" PT1H')
        alias_result = await client.command("/sf b user-2")

        assert direct_result.texts == ["user 1 PT1H"]
        assert alias_result.texts == ["user-2"]

    asyncio.run(run())


def test_plugin_test_client_can_enforce_manifest_permissions() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        @plugin.command("/ask")
        async def ask(request, llm=Depends("llm")):
            return await llm.chat(request.command.args_text)

        class FakeLLM:
            async def chat(self, prompt: str) -> str:
                return prompt

        with pytest.raises(PluginAuthorizationError):
            PluginTestClient(
                plugin,
                dependencies={"llm": FakeLLM()},
                enforce_permissions=True,
            )

        client = PluginTestClient(
            plugin,
            dependencies={"llm": FakeLLM()},
            permissions=["llm"],
            enforce_permissions=True,
        )
        result = await client.command("/ask ok")

        assert result.texts == ["ok"]

    asyncio.run(run())


def test_plugin_test_client_dispatches_events_without_full_runtime() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        class Storage:
            def __init__(self) -> None:
                self.values = {}

            async def set(self, key, value):
                self.values[key] = value

        storage = Storage()

        @plugin.event("message")
        async def on_message(event, storage=Depends("storage")):
            await storage.set(event.session_id, event.text)
            return PluginEventResult(metadata={"seen": event.text})

        client = PluginTestClient(plugin, dependencies={"storage": storage})
        result = await client.event("message", text="hello", session_id="s1")

        assert storage.values == {"s1": "hello"}
        assert result.handled is True
        assert result.metadata == [{"seen": "hello"}]

    asyncio.run(run())


def test_plugin_test_client_runs_tasks_without_full_runtime() -> None:
    async def run() -> None:
        plugin = CyreneBot()

        @plugin.task("cleanup")
        async def cleanup(request):
            return PluginTaskResult(
                metadata={
                    "task": request.task.name,
                    "payload": request.payload,
                    "metadata": request.metadata,
                }
            )

        client = PluginTestClient(plugin)
        result = await client.task(
            "cleanup",
            payload={"target": "cache"},
            metadata={"source": "test"},
        )

        assert result.handled is True
        assert result.metadata == {
            "task": "cleanup",
            "payload": {"target": "cache"},
            "metadata": {"source": "test"},
        }

    asyncio.run(run())
