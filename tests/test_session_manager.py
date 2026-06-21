"""Tests for hermes_claude_bridge.session_manager."""

import pytest

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.db.models import SessionStatus
from hermes_claude_bridge.session_manager import SessionManager


@pytest.mark.asyncio
async def test_create_and_get_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    manager = SessionManager(engine)
    session = await manager.create_session(
        working_dir="/tmp", model="sonnet", permissions_mode="acceptEdits"
    )
    assert session.model == "sonnet"

    fetched = await manager.get_session(session.session_id)
    assert fetched is not None
    assert fetched.session_id == session.session_id


@pytest.mark.asyncio
async def test_add_event_and_list():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    manager = SessionManager(engine)
    session = await manager.create_session(working_dir="/tmp")
    await manager.add_event(session.session_id, "user_prompt", {"prompt": "hello"})
    events = await manager.list_events(session.session_id)
    assert len(events) == 1
    assert events[0].event_type.value == "user_prompt"


@pytest.mark.asyncio
async def test_update_status():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    manager = SessionManager(engine)
    session = await manager.create_session(working_dir="/tmp")
    await manager.update_status(session.session_id, SessionStatus.WAITING_USER_INPUT)
    fetched = await manager.get_session(session.session_id)
    assert fetched is not None
    assert fetched.status == SessionStatus.WAITING_USER_INPUT
