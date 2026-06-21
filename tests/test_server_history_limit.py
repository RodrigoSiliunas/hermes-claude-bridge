"""Tests for max_history_events propagation via server API."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


@pytest.fixture
async def app():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    return create_app(engine=engine)


@pytest.mark.asyncio
async def test_create_session_with_history_limit(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as http:
        response = await http.post(
            "/sessions",
            json={
                "working_dir": "/tmp",
                "max_history_events": 3,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["max_history_events"] == 3
