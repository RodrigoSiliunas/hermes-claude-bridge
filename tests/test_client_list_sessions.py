"""Tests for BridgeClient.list_sessions."""

import json
from typing import Any

import pytest

from hermes_claude_bridge.client import BridgeClient


class FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        pass


@pytest.mark.asyncio
async def test_client_list_sessions(monkeypatch):
    client = BridgeClient("http://localhost:8765")

    async def fake_get(url: str):
        return FakeResponse(
            {
                "sessions": [
                    {"session_id": "abc", "working_dir": "/tmp/foo"},
                    {"session_id": "def", "working_dir": "/tmp/bar"},
                ]
            }
        )

    monkeypatch.setattr(client._http, "get", fake_get)
    sessions = await client.list_sessions()
    assert len(sessions) == 2
    assert sessions[0]["session_id"] == "abc"
    await client.close()
