"""Tests for hermes_claude_bridge.executor."""

import pytest

from hermes_claude_bridge.executor import ClaudeExecutor
from hermes_claude_bridge.schemas import ClaudeTask


@pytest.mark.asyncio
async def test_run_command_echo():
    executor = ClaudeExecutor()
    result = await executor.run_command(["echo", "hello"])
    assert result.stdout.strip() == "hello"
    assert result.exit_code == 0
    assert "echo hello" in result.command


@pytest.mark.asyncio
async def test_run_command_timeout():
    executor = ClaudeExecutor()
    result = await executor.run_command(["sleep", "10"], timeout=1)
    assert result.exit_code == -1
    assert "TIMEOUT" in result.stderr


def test_build_claude_args():
    executor = ClaudeExecutor()
    task = ClaudeTask(prompt="Hello", permissions_mode="acceptEdits")
    args = executor._build_args(task)
    assert "-p" in args
    assert "--bare" in args
    assert "Hello" in args
    assert args[0] == "claude"


def test_build_claude_args_dont_ask():
    executor = ClaudeExecutor()
    task = ClaudeTask(prompt="Run", permissions_mode="dontAsk")
    args = executor._build_args(task)
    assert "--dangerously-skip-permissions" in args
