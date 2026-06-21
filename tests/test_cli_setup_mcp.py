"""Tests for the setup --mcp-config CLI command."""

from click.testing import CliRunner

from hermes_claude_bridge.cli import cli


def test_setup_mcp_config():
    runner = CliRunner()
    result = runner.invoke(cli, ["setup", "--mcp-config"])
    assert result.exit_code == 0
    assert "mcp_servers" in result.output
    assert "hermes-claude-bridge" in result.output
    assert "mcp-server" in result.output
