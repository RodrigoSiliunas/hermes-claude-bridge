"""Tests for hermes_claude_bridge.server."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


@pytest.mark.asyncio
async def test_health_endpoint():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_create_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/sessions", json={"working_dir": "/tmp", "model": "sonnet"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"].startswith("sess-")
        assert data["model"] == "sonnet"


@pytest.mark.asyncio
async def test_get_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/sessions", json={"working_dir": "/tmp"})
        session_id = created.json()["session_id"]
        resp = await client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_session_not_found():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/sessions/invalid")
        assert resp.status_code == 404
