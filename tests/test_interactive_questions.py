"""Tests for question detection in interactive mode."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


class FakeInteractiveExecutor:
    def __init__(self, responses):
        self.responses = list(responses)
        self.started = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False

    async def send(self, message, timeout=30.0):
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_interactive_prompt_detects_question():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    fake = FakeInteractiveExecutor(["Should I delete the old file? (y/n)"])

    def get_fake(session_id, working_dir):
        return fake

    app = create_app(engine, get_interactive_executor=get_fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        session = await http.post("/sessions", json={"working_dir": "/tmp", "mode": "interactive"})
        session_id = session.json()["session_id"]

        result = await http.post(f"/sessions/{session_id}/prompt", json={"prompt": "clean up", "timeout": 5})
        data = result.json()

        assert data["status"] == "waiting_user_input"
        assert "Should I delete the old file?" in data["pending_question"]
