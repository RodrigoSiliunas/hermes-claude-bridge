"""Tests for the MCP server exposing claude_code_delegate."""

import pytest

from hermes_claude_bridge.mcp_server import create_mcp_server


@pytest.mark.asyncio
async def test_mcp_server_has_claude_code_delegate_tool():
    server = create_mcp_server()
    tools = await server.list_tools()
    assert any(tool.name == "claude_code_delegate" for tool in tools)
