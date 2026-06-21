"""Tests for the setup --hermes-plugin CLI command."""

import os
import tempfile

from click.testing import CliRunner

from hermes_claude_bridge.cli import cli


def test_setup_hermes_plugin():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        result = runner.invoke(cli, ["setup", "--hermes-plugin", "--plugins-dir", tmp])
        assert result.exit_code == 0
        assert os.path.isdir(os.path.join(tmp, "hermes-claude-bridge"))
        assert "Hermes plugin installed" in result.output
