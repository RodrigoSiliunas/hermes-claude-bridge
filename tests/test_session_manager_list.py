"""Tests for SessionManager.list_events."""

import pytest

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.db.models import EventType
from hermes_claude_bridge.session_manager import SessionManager


@pytest.mark.asyncio
async def test_list_events_ordered():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    sm = SessionManager(engine)

    session = await sm.create_session("/tmp")
    await sm.add_event(session.session_id, EventType.USER_PROMPT, {"prompt": "a"})
    await sm.add_event(session.session_id, EventType.CLAUDE_RESPONSE, {"stdout": "b"})

    events = await sm.list_events(session.session_id)
    assert len(events) == 2
    assert events[0].payload["prompt"] == "a"
    assert events[1].payload["stdout"] == "b"
