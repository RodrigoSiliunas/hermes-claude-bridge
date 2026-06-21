"""Tests for MCP config generator."""

from hermes_claude_bridge.setup_manager import generate_mcp_config


def test_generate_mcp_config():
    config = generate_mcp_config()
    assert "mcp_servers" in config
    assert "hermes-claude-bridge" in config["mcp_servers"]
    server = config["mcp_servers"]["hermes-claude-bridge"]
    assert server["command"] == "hermes-claude"
    assert "mcp-server" in server["args"]
    assert server["enabled"] is True
