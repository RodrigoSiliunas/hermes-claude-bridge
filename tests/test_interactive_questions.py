"""Tests for question detection in interactive (contextual) mode."""

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.schemas import ClaudeResult
from hermes_claude_bridge.server import create_app


@pytest.mark.asyncio
async def test_interactive_prompt_detects_question(monkeypatch):
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)

    async def fake_run_task(task):
        return ClaudeResult(
            task_id="t1",
            success=True,
            stdout="Should I delete the old file? (y/n)",
            status="waiting_user_input",
            pending_question="Should I delete the old file? (y/n)",
        )

    monkeypatch.setattr(app.state.bridge, "run_task", fake_run_task)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        session = await http.post("/sessions", json={"working_dir": "/tmp", "mode": "interactive"})
        session_id = session.json()["session_id"]

        result = await http.post(f"/sessions/{session_id}/prompt", json={"prompt": "clean up", "timeout": 5})
        data = result.json()

        assert data["status"] == "waiting_user_input"
        assert "Should I delete the old file?" in data["pending_question"]
