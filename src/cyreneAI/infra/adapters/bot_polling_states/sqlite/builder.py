from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from cyreneAI.infra.adapters.bot_polling_states.sqlite.store import (
    SQLiteBotPollingStateStore,
)
from cyreneAI.infra.adapters.bot_polling_states.sqlite.tables import (
    create_bot_polling_state_tables,
)


def create_sqlite_bot_polling_state_engine(
    path: str | Path,
    *,
    echo: bool = False,
) -> AsyncEngine:
    """
    创建 SQLite channel polling 状态 AsyncEngine。
    """
    return create_async_engine(
        _build_sqlite_url(path),
        echo=echo,
    )


async def create_sqlite_bot_polling_state_store(
    path: str | Path,
    *,
    echo: bool = False,
) -> SQLiteBotPollingStateStore:
    """
    创建 SQLite channel polling 状态存储。
    """
    engine = create_sqlite_bot_polling_state_engine(path, echo=echo)
    await create_bot_polling_state_tables(engine)
    return SQLiteBotPollingStateStore(engine)


def _build_sqlite_url(path: str | Path) -> str:
    if str(path) == ":memory:":
        return "sqlite+aiosqlite:///:memory:"

    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{database_path.as_posix()}"
