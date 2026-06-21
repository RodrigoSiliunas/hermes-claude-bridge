"""Tests for real-time event notifications in SessionManager."""

import asyncio

import pytest

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.session_manager import SessionManager


@pytest.mark.asyncio
async def test_event_listener_notified():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    manager = SessionManager(engine)
    session = await manager.create_session("/tmp")
    session_id = session.session_id

    received = []

    async def listener():
        async for event in manager.listen_events(session_id):
            received.append(event)
            break

    task = asyncio.create_task(listener())
    await asyncio.sleep(0.05)
    await manager.add_event(session_id, "user_prompt", {"prompt": "hi"})
    await asyncio.wait_for(task, timeout=1.0)

    assert len(received) == 1
    assert received[0].event_type.value == "user_prompt"
