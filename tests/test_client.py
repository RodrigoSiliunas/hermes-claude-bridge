"""Tests for hermes_claude_bridge.client."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.client import BridgeClient
from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


@pytest.fixture
async def client():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield BridgeClient(base_url="http://test", http_client=http)


@pytest.mark.asyncio
async def test_client_health(client):
    health = await client.health()
    assert health["ok"] is True


@pytest.mark.asyncio
async def test_client_create_session(client):
    session = await client.create_session(working_dir="/tmp", model="sonnet")
    assert session["session_id"].startswith("sess-")
    assert session["model"] == "sonnet"


@pytest.mark.asyncio
async def test_client_get_session(client):
    created = await client.create_session(working_dir="/tmp")
    session_id = created["session_id"]
    fetched = await client.get_session(session_id)
    assert fetched["session_id"] == session_id
