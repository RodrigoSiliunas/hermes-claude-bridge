"""Tests for the MCP server CLI command."""

from click.testing import CliRunner

from hermes_claude_bridge.cli import cli


def test_mcp_server_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["mcp-server", "--help"])
    assert result.exit_code == 0
    assert "mcp-server" in result.output
