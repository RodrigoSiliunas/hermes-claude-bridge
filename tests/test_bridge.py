"""Tests for hermes_claude_bridge.bridge."""

import pytest

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.schemas import ClaudeTask


@pytest.mark.asyncio
async def test_bridge_health():
    bridge = HermesClaudeBridge()
    health = await bridge.health()
    assert "claude_installed" in health
    assert "working_dir" in health


@pytest.mark.asyncio
async def test_bridge_run_task_returns_result():
    bridge = HermesClaudeBridge()
    result = await bridge.run_task(
        ClaudeTask(prompt="echo hello", permissions_mode="dontAsk", timeout_seconds=5)
    )
    assert result.task_id is not None
    assert result.duration_seconds >= 0
