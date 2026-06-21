"""Tests for answering questions in interactive sessions."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


class FakeInteractiveExecutor:
    def __init__(self, responses):
        self.responses = list(responses)
        self.started = False
        self.sent: list[str] = []

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False

    async def send(self, message, timeout=30.0):
        self.sent.append(message)
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_answer_question_in_interactive_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)

    fake = FakeInteractiveExecutor([
        "Should I delete the old file? (y/n)",
        "Done. File deleted.",
    ])

    def get_fake(session_id, working_dir):
        return fake

    app = create_app(engine, get_interactive_executor=get_fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        session = await http.post("/sessions", json={"working_dir": "/tmp", "mode": "interactive"})
        session_id = session.json()["session_id"]

        question_resp = await http.post(f"/sessions/{session_id}/prompt", json={"prompt": "clean up", "timeout": 5})
        assert question_resp.json()["status"] == "waiting_user_input"

        answer_resp = await http.post(f"/sessions/{session_id}/answer", json={"answer": "yes"})
        data = answer_resp.json()
        assert data["status"] == "active"
        assert "Done. File deleted." in data["stdout"]
        assert any("yes" in s for s in fake.sent)
