from __future__ import annotations


class InMemoryBotPollingStateStore:
    """
    内存 channel polling 状态存储，适合测试和本地开发。
    """

    def __init__(self) -> None:
        self._offsets: dict[str, int] = {}
        self._processed_events: set[tuple[str, str]] = set()

    async def get_offset(self, channel_id: str) -> int | None:
        return self._offsets.get(channel_id)

    async def save_offset(self, channel_id: str, offset: int) -> None:
        self._offsets[channel_id] = offset

    async def is_event_processed(self, channel_id: str, event_id: str) -> bool:
        return (channel_id, event_id) in self._processed_events

    async def mark_event_processed(self, channel_id: str, event_id: str) -> None:
        self._processed_events.add((channel_id, event_id))

    async def close(self) -> None:
        pass
