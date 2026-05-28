from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from cyreneAI.core.schema.plugin import PluginScheduledTask, PluginTaskStatus
from cyreneAI.infra.adapters.plugins.sqlite import create_sqlite_plugin_task_store


def _task(
    task_id: str = "task-1",
    *,
    key: str | None = "user-1",
    status: PluginTaskStatus = PluginTaskStatus.PENDING,
) -> PluginScheduledTask:
    now = datetime.now(UTC)
    return PluginScheduledTask(
        task_id=task_id,
        plugin_id="thirdparty.tasks",
        task_name="conversation_end",
        run_at=now + timedelta(seconds=60),
        payload={"user_id": "user-1"},
        key=key,
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_sqlite_plugin_task_store_lifecycle(tmp_path) -> None:
    async def run() -> None:
        database_path = tmp_path / "plugin_tasks.db"
        store = await create_sqlite_plugin_task_store(database_path)
        await store.add_task(_task())

        pending_tasks = await store.list_pending_tasks(
            plugin_id="thirdparty.tasks",
            task_name="conversation_end",
        )
        assert len(pending_tasks) == 1
        assert pending_tasks[0].payload == {"user_id": "user-1"}

        await store.update_task_status("task-1", PluginTaskStatus.RUNNING)
        assert [task.task_id for task in await store.list_pending_tasks()] == ["task-1"]

        await store.update_task_status("task-1", PluginTaskStatus.COMPLETED)
        assert await store.list_pending_tasks() == []
        await store.close()

        next_store = await create_sqlite_plugin_task_store(database_path)
        try:
            assert await next_store.list_pending_tasks() == []
        finally:
            await next_store.close()

    asyncio.run(run())


def test_sqlite_plugin_task_store_cancels_by_key(tmp_path) -> None:
    async def run() -> None:
        store = await create_sqlite_plugin_task_store(tmp_path / "plugin_tasks.db")
        try:
            await store.add_task(_task("task-1", key="same-key"))
            await store.add_task(_task("task-2", key="same-key"))

            cancelled_count = await store.cancel_task_key(
                "thirdparty.tasks",
                "same-key",
            )

            assert cancelled_count == 2
            assert await store.list_pending_tasks() == []
        finally:
            await store.close()

    asyncio.run(run())
