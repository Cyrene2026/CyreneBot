from __future__ import annotations

import asyncio
from pathlib import Path

from cyreneAI.bootstrap import build_cyrene_ai_runtime
from cyreneAI.core.bot.registry import BotChannelRegistry
from cyreneAI.core.bot.session_manager import BotSessionManager
from cyreneAI.core.schema.bot import (
    BotChannelDefinition,
    BotCommand,
    BotEvent,
    BotEventType,
    BotMessage,
)
from cyreneAI.core.schema.message import ContentPart, ContentPartType
from cyreneAI.core.schema.plugin import (
    PluginCommandRequest,
    PluginEvent,
    PluginEventType,
)
from cyreneAI.infra.adapters.bot_sessions.memory import InMemoryBotSessionStore
from cyreneAI.infra.adapters.channels.memory import InMemoryBotChannel
from cyreneAI.infra.adapters.plugins.filesystem import (
    FileSystemPluginAssets,
    FileSystemPluginLoader,
    FileSystemPluginStorage,
)


PROJECT_ROOT = Path(__file__).parents[3]
DEMO_PLUGIN_PATH = PROJECT_ROOT / "examples" / "plugins" / "proactive_reply_demo"


def test_proactive_reply_demo_schedules_and_sends_follow_up(tmp_path) -> None:
    async def run() -> None:
        channel = InMemoryBotChannel()
        channel_registry = BotChannelRegistry()
        channel_registry.register(
            BotChannelDefinition(
                channel_id="memory",
                name="Memory",
            ),
            channel,
        )
        session_manager = BotSessionManager(InMemoryBotSessionStore())
        bot_event = BotEvent(
            event_id="event-1",
            event_type=BotEventType.MESSAGE,
            channel_id="memory",
            session_id="memory:user-1",
            user_id="user-1",
            thread_id="thread-1",
            message=BotMessage(
                content=[
                    ContentPart(
                        type=ContentPartType.TEXT,
                        text="我去吃饭了",
                    )
                ]
            ),
        )
        await session_manager.get_or_create(bot_event)

        plugin_assets = FileSystemPluginAssets()
        runtime = await build_cyrene_ai_runtime(
            plugin_assets=plugin_assets,
            plugin_storage=FileSystemPluginStorage(tmp_path / "plugin_storage"),
            plugin_loaders=[
                FileSystemPluginLoader(
                    DEMO_PLUGIN_PATH,
                    plugin_assets=plugin_assets,
                )
            ],
            bot_channel_registry=channel_registry,
            bot_session_manager=session_manager,
            register_builtin_plugins=False,
        )
        try:
            assert runtime.plugin_manager is not None
            plugins = runtime.plugin_manager.list_plugins()
            assert [plugin.plugin_id for plugin in plugins] == [
                "demo.proactive_reply"
            ]
            assert [command.name for command in runtime.plugin_manager.list_commands()] == [
                "proactive status"
            ]
            assert plugins[0].events[0].event_type == PluginEventType.MESSAGE
            assert plugins[0].tasks[0].name == "follow_up"

            await runtime.plugin_manager.dispatch_event(
                PluginEvent(
                    event_id="event-1",
                    event_type=PluginEventType.MESSAGE,
                    session_id="memory:user-1",
                    user_id="user-1",
                    thread_id="thread-1",
                    text="我去吃饭了",
                ),
                metadata={
                    "follow_up_delay_seconds": 0.05,
                    "follow_up_cooldown_seconds": 0.2,
                },
            )

            for _ in range(20):
                if channel.actions:
                    break
                await asyncio.sleep(0.02)

            assert len(channel.actions) == 1
            action = channel.actions[0]
            assert action.channel_id == "memory"
            assert action.session_id == "memory:user-1"
            assert action.recipient_id == "user-1"
            assert action.thread_id == "thread-1"
            assert action.message is not None
            assert (
                action.message.content[0].text
                == "刚刚你说「我去吃饭了」，我先记着。等你回来我们接着聊。"
            )
            assert action.metadata["plugin_id"] == "demo.proactive_reply"
            assert action.metadata["kind"] == "proactive_follow_up"

            await runtime.plugin_manager.dispatch_event(
                PluginEvent(
                    event_id="event-2",
                    event_type=PluginEventType.MESSAGE,
                    session_id="memory:user-1",
                    user_id="user-1",
                    thread_id="thread-1",
                    text="/proactive status",
                ),
                metadata={
                    "follow_up_delay_seconds": 0.05,
                    "follow_up_cooldown_seconds": 0.2,
                },
            )
            await asyncio.sleep(0.08)
            assert len(channel.actions) == 1

            await runtime.plugin_manager.dispatch_event(
                PluginEvent(
                    event_id="event-3",
                    event_type=PluginEventType.MESSAGE,
                    session_id="memory:user-1",
                    user_id="user-1",
                    thread_id="thread-1",
                    text="ok",
                ),
                metadata={
                    "follow_up_delay_seconds": 0.05,
                    "follow_up_cooldown_seconds": 0.2,
                },
            )
            await asyncio.sleep(0.08)
            assert len(channel.actions) == 1

            status_result = await runtime.plugin_manager.execute_command(
                PluginCommandRequest(
                    command=BotCommand(
                        raw_text="/proactive status",
                        name="proactive status",
                    ),
                    event=bot_event,
                )
            )
            assert status_result.actions[0].message is not None
            assert (
                status_result.actions[0].message.content[0].text
                == "Proactive reply demo is running. Last message: 我去吃饭了"
            )
        finally:
            await runtime.close()

    asyncio.run(run())
