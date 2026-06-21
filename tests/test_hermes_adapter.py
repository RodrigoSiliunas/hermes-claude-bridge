"""Tests for hermes_claude_bridge.hermes_adapter."""

import pytest

from hermes_claude_bridge.hermes_adapter import ClaudeBridgeTool


def test_tool_schema():
    tool = ClaudeBridgeTool()
    schema = tool.get_schema()
    assert schema["name"] == "claude_code_delegate"
    assert "prompt" in schema["parameters"]["properties"]


@pytest.mark.asyncio
async def test_tool_invoke_echo():
    tool = ClaudeBridgeTool()
    result = await tool.invoke(
        {"prompt": "echo hello world", "timeout": 5, "permission_mode": "dontAsk"}
    )
    assert "task_id" in result
    assert "success" in result
