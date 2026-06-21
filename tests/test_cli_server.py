"""Tests for hermes-claude server CLI command."""

from click.testing import CliRunner

from hermes_claude_bridge.cli import cli


def test_server_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["server", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.output
    assert "--port" in result.output
