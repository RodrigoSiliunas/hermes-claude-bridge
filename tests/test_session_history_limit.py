"""Tests for max_history_events on ClaudeSession."""

import pytest

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.session_manager import SessionManager


@pytest.fixture
async def session_manager():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    manager = SessionManager(engine)
    yield manager
    await engine.dispose()


@pytest.mark.asyncio
async def test_session_has_default_history_limit(session_manager):
    session = await session_manager.create_session(working_dir="/tmp")
    assert session.max_history_events == 10


@pytest.mark.asyncio
async def test_session_accepts_custom_history_limit(session_manager):
    session = await session_manager.create_session(working_dir="/tmp", max_history_events=5)
    assert session.max_history_events == 5
