"""Tests for interactive session mode in server."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


@pytest.mark.asyncio
async def test_create_interactive_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        resp = await http.post("/sessions", json={
            "working_dir": "/tmp",
            "mode": "interactive",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["mode"] == "interactive"
