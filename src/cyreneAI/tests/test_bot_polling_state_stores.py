from __future__ import annotations

import asyncio

from cyreneAI.infra.adapters.bot_polling_states.memory import (
    InMemoryBotPollingStateStore,
)
from cyreneAI.infra.adapters.bot_polling_states.sqlite import (
    create_sqlite_bot_polling_state_store,
)


async def _assert_store_lifecycle(store) -> None:
    assert await store.get_offset("telegram") is None
    assert await store.is_event_processed("telegram", "1000") is False

    await store.save_offset("telegram", 1001)
    await store.mark_event_processed("telegram", "1000")

    assert await store.get_offset("telegram") == 1001
    assert await store.is_event_processed("telegram", "1000") is True
    assert await store.is_event_processed("telegram", "1001") is False

    await store.close()


def test_in_memory_bot_polling_state_store_lifecycle() -> None:
    asyncio.run(_assert_store_lifecycle(InMemoryBotPollingStateStore()))


def test_sqlite_bot_polling_state_store_lifecycle(tmp_path) -> None:
    async def run() -> None:
        database_path = tmp_path / "polling.db"
        store = await create_sqlite_bot_polling_state_store(database_path)
        await _assert_store_lifecycle(store)

        next_store = await create_sqlite_bot_polling_state_store(database_path)
        try:
            assert await next_store.get_offset("telegram") == 1001
            assert await next_store.is_event_processed("telegram", "1000") is True
        finally:
            await next_store.close()

    asyncio.run(run())
