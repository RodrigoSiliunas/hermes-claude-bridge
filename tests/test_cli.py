"""Tests for hermes_claude_bridge.cli."""

from click.testing import CliRunner

from hermes_claude_bridge.cli import cli


def test_cli_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "health" in result.output
    assert "run" in result.output


def test_cli_health():
    runner = CliRunner()
    result = runner.invoke(cli, ["health"])
    assert result.exit_code == 0
    assert "claude_installed" in result.output


def test_cli_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "echo hello"])
    assert result.exit_code == 0
    assert "task_id" in result.output
