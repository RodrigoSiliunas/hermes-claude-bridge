"""Tests for bare mode configuration in executor."""

from hermes_claude_bridge.executor import ClaudeExecutor
from hermes_claude_bridge.schemas import ClaudeTask


def test_build_args_with_bare_mode_enabled():
    executor = ClaudeExecutor()
    task = ClaudeTask(prompt="Hello", permissions_mode="acceptEdits")
    args = executor._build_args(task, bare_mode=True)
    assert "--bare" in args


def test_build_args_with_bare_mode_disabled():
    executor = ClaudeExecutor()
    task = ClaudeTask(prompt="Hello", permissions_mode="acceptEdits")
    args = executor._build_args(task, bare_mode=False)
    assert "--bare" not in args
