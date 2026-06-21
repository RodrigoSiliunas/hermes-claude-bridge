"""Tests for real-time SSE endpoint."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


@pytest.mark.asyncio
async def test_sse_generator_uses_listen_events():
    """Verify events added to SessionManager appear through listen_events."""
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        session = await http.post("/sessions", json={"working_dir": "/tmp"})
        session_id = session.json()["session_id"]

        # Get the SessionManager instance attached to the app.
        session_manager = app.state.session_manager

        received = []

        async def listener():
            async for ev in session_manager.listen_events(session_id):
                received.append(ev)
                break

        task = asyncio.create_task(listener())
        await asyncio.sleep(0.05)
        await session_manager.add_event(session_id, "user_prompt", {"prompt": "hello"})
        await asyncio.wait_for(task, timeout=1.0)

        assert len(received) == 1
        assert received[0].event_type.value == "user_prompt"
