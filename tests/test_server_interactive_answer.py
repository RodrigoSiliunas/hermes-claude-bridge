"""Tests for answering questions in interactive (contextual) sessions."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.schemas import ClaudeResult
from hermes_claude_bridge.server import create_app


@pytest.mark.asyncio
async def test_answer_question_in_interactive_session(monkeypatch):
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)

    responses = [
        ClaudeResult(
            task_id="t1",
            success=True,
            stdout="Should I delete the old file? (y/n)",
            status="waiting_user_input",
            pending_question="Should I delete the old file? (y/n)",
        ),
        ClaudeResult(
            task_id="t2",
            success=True,
            stdout="Done. File deleted.",
            status="active",
        ),
    ]

    async def fake_run_task(task):
        return responses.pop(0)

    monkeypatch.setattr(app.state.bridge, "run_task", fake_run_task)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        session = await http.post("/sessions", json={"working_dir": "/tmp", "mode": "interactive"})
        session_id = session.json()["session_id"]

        question_resp = await http.post(
            f"/sessions/{session_id}/prompt",
            json={"prompt": "clean up", "timeout": 5},
        )
        assert question_resp.json()["status"] == "waiting_user_input"

        answer_resp = await http.post(f"/sessions/{session_id}/answer", json={"answer": "yes"})
        data = answer_resp.json()
        assert data["status"] == "active"
        assert "Done. File deleted." in data["stdout"]
