"""Tests for MCP tool using persistent bridge sessions."""

import pytest

from hermes_claude_bridge.mcp_server import create_mcp_server


@pytest.mark.asyncio
async def test_mcp_tool_supports_bridge_url(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, base_url):
            self.base_url = base_url

        async def create_session(self, **kwargs):
            calls.append(("create_session", kwargs))
            return {"session_id": "sess-123", "mode": "interactive"}

        async def send_prompt(self, session_id, prompt, **kwargs):
            calls.append(("send_prompt", session_id, prompt, kwargs))
            return {"status": "completed", "stdout": "ok"}

    monkeypatch.setattr("hermes_claude_bridge.mcp_server.BridgeClient", FakeClient)

    server = create_mcp_server()
    result = await server.call_tool(
        "claude_code_delegate",
        {
            "prompt": "hello",
            "bridge_url": "http://localhost:8765",
            "mode": "interactive",
        },
    )

    assert '"status": "completed"' in result[0].text
    assert any(c[0] == "create_session" for c in calls)
    assert any(c[0] == "send_prompt" for c in calls)
