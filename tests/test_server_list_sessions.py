"""Tests for GET /sessions endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


@pytest.mark.asyncio
async def test_list_sessions():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post(
            "/sessions",
            json={"working_dir": "/tmp/foo"},
        )
        assert r1.status_code == 201

        r2 = await client.get("/sessions")
        assert r2.status_code == 200
        data = r2.json()
        assert "sessions" in data
        assert any(s["working_dir"] == "/tmp/foo" for s in data["sessions"])
