from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from cyreneAI.infra.adapters.bot_polling_states.sqlite.tables import (
    bot_polling_offsets,
    bot_polling_processed_events,
)


class SQLiteBotPollingStateStore:
    """
    SQLite channel polling 状态存储。
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_offset(self, channel_id: str) -> int | None:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(bot_polling_offsets.c.offset).where(
                    bot_polling_offsets.c.channel_id == channel_id
                )
            )
            raw_offset = result.scalar_one_or_none()
        if raw_offset is None:
            return None
        return int(raw_offset)

    async def save_offset(self, channel_id: str, offset: int) -> None:
        now = datetime.now(UTC)
        async with self._engine.begin() as connection:
            result = await connection.execute(
                update(bot_polling_offsets)
                .where(bot_polling_offsets.c.channel_id == channel_id)
                .values(
                    offset=str(offset),
                    updated_at=now,
                )
            )
            if result.rowcount:
                return
            await connection.execute(
                insert(bot_polling_offsets).values(
                    channel_id=channel_id,
                    offset=str(offset),
                    updated_at=now,
                )
            )

    async def is_event_processed(self, channel_id: str, event_id: str) -> bool:
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(bot_polling_processed_events.c.event_id).where(
                    bot_polling_processed_events.c.channel_id == channel_id,
                    bot_polling_processed_events.c.event_id == event_id,
                )
            )
            return result.scalar_one_or_none() is not None

    async def mark_event_processed(self, channel_id: str, event_id: str) -> None:
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    insert(bot_polling_processed_events).values(
                        channel_id=channel_id,
                        event_id=event_id,
                        processed_at=datetime.now(UTC),
                    )
                )
        except IntegrityError:
            return

    async def close(self) -> None:
        await self._engine.dispose()
