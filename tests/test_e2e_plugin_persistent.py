"""E2E test for Hermes plugin using a persistent bridge server session.

This test spins up the bridge app in-process via ASGI transport, then calls
the plugin handler twice for the same working directory. The second call must
reuse the existing session and remember context from the first call.
"""

import json
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.plugin_template.tools import handle_delegate
from hermes_claude_bridge.server import create_app


@pytest.mark.asyncio
async def test_plugin_persistent_session_on_bridge_server(tmp_path):
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)

    http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=120,
    )

    class BoundBridgeClient:
        def __init__(self, base_url: str):
            self.base_url = base_url
            self._http = http_client

        async def list_sessions(self) -> list[dict[str, Any]]:
            resp = await self._http.get("/sessions")
            resp.raise_for_status()
            return resp.json().get("sessions", [])

        async def create_session(self, **kwargs: Any) -> dict[str, Any]:
            resp = await self._http.post("/sessions", json=kwargs)
            resp.raise_for_status()
            return resp.json()

        async def send_prompt(self, session_id: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
            resp = await self._http.post(
                f"/sessions/{session_id}/prompt",
                json={"prompt": prompt, **kwargs},
            )
            resp.raise_for_status()
            return resp.json()

        async def close(self) -> None:
            pass

    import hermes_claude_bridge.plugin_template.tools as plugin_tools

    original_client = plugin_tools.BridgeClient
    plugin_tools.BridgeClient = BoundBridgeClient
    try:
        working_dir = str(tmp_path)

        result1 = await handle_delegate({
            "prompt": (
                "Write the number 42 into a file named secret.txt in the "
                "current directory and return done"
            ),
            "working_dir": working_dir,
            "mode": "headless",
            "bridge_url": "http://test",
        })
        data1 = json.loads(result1)

        if "Not logged in" in data1.get("stdout", "") or "Please run /login" in data1.get("stdout", ""):
            pytest.skip("Claude Code CLI is not logged in")

        assert data1.get("success") is True
        assert "session_id" in data1
        session_id_1 = data1["session_id"]

        result2 = await handle_delegate({
            "prompt": "Read secret.txt and tell me the number inside it",
            "working_dir": working_dir,
            "mode": "headless",
            "bridge_url": "http://test",
        })
        data2 = json.loads(result2)
        assert data2.get("success") is True
        assert data2["session_id"] == session_id_1
        output = data2.get("stdout", "")
        assert "42" in output
    finally:
        plugin_tools.BridgeClient = original_client
        await http_client.aclose()
