"""Async database engine and helpers."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from hermes_claude_bridge.db.models import Base


def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Create async SQLAlchemy engine.

    Defaults to an async SQLite database in the current working directory.
    Set DATABASE_URL env var to use PostgreSQL:
        postgresql+asyncpg://user:pass@localhost/hermes_claude_bridge
    """
    url = (
        database_url or os.getenv("DATABASE_URL") or "sqlite+aiosqlite:///./hermes_claude_bridge.db"
    )
    return create_async_engine(url, echo=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
