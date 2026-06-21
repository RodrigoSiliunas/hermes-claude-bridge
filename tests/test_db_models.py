"""Tests for hermes_claude_bridge.db.models."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.db.models import ClaudeSession, EventType, SessionEvent, SessionStatus


@pytest.mark.asyncio
async def test_create_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    async with AsyncSession(engine) as session:
        cs = ClaudeSession(
            session_id="sess-001",
            working_dir="/tmp",
            model="sonnet",
            status=SessionStatus.ACTIVE,
        )
        session.add(cs)
        await session.commit()
        await session.refresh(cs)
        assert cs.id is not None
        assert cs.model == "sonnet"


@pytest.mark.asyncio
async def test_create_event():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    async with AsyncSession(engine) as session:
        ev = SessionEvent(
            session_id="sess-001",
            event_type=EventType.USER_PROMPT,
            payload={"prompt": "hello"},
        )
        session.add(ev)
        await session.commit()
        await session.refresh(ev)
        assert ev.id is not None
        assert ev.event_type == EventType.USER_PROMPT
