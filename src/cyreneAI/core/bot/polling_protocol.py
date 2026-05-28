from __future__ import annotations

from typing import Protocol


class BotPollingStateStoreProtocol(Protocol):
    """
    channel polling 状态存储协议。
    """

    async def get_offset(self, channel_id: str) -> int | None:
        """
        获取 channel 当前 polling offset。
        """
        ...

    async def save_offset(self, channel_id: str, offset: int) -> None:
        """
        保存 channel 当前 polling offset。
        """
        ...

    async def is_event_processed(self, channel_id: str, event_id: str) -> bool:
        """
        判断事件是否已经处理完成。
        """
        ...

    async def mark_event_processed(self, channel_id: str, event_id: str) -> None:
        """
        标记事件已经处理完成。
        """
        ...

    async def close(self) -> None:
        """
        关闭状态存储持有的外部资源。
        """
        ...
