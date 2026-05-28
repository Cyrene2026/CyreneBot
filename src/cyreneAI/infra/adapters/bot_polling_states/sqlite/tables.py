from __future__ import annotations

from sqlalchemy import Column, DateTime, MetaData, String, Table, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncEngine

metadata = MetaData()

bot_polling_offsets = Table(
    "bot_polling_offsets",
    metadata,
    Column("channel_id", String, primary_key=True),
    Column("offset", String, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

bot_polling_processed_events = Table(
    "bot_polling_processed_events",
    metadata,
    Column("channel_id", String, nullable=False),
    Column("event_id", String, nullable=False),
    Column("processed_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("channel_id", "event_id"),
)


async def create_bot_polling_state_tables(engine: AsyncEngine) -> None:
    """
    创建 channel polling 状态表。
    """
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
