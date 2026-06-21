"""Tests for Hermes plugin reading bridge_url from environment."""

import json
from typing import Any

import pytest

from hermes_claude_bridge.plugin_template.tools import handle_delegate


class FakeBridgeClient:
    def __init__(self, url: str):
        self.url = url

    async def create_session(self, **kwargs: Any) -> dict[str, Any]:
        return {"session_id": "abc", "url": self.url}

    async def send_prompt(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "completed", "url": self.url}

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_plugin_uses_env_bridge_url(monkeypatch):
    monkeypatch.setenv("HERMES_CLAUDE_BRIDGE_URL", "http://bridge.example")

    import hermes_claude_bridge.plugin_template.tools as plugin_tools

    original_client = plugin_tools.BridgeClient
    plugin_tools.BridgeClient = FakeBridgeClient
    try:
        result = await handle_delegate({"prompt": "hello"})
        data = json.loads(result)
        assert data["url"] == "http://bridge.example"
    finally:
        plugin_tools.BridgeClient = original_client
