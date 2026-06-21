"""Tests for model selection in executor."""

from hermes_claude_bridge.executor import ClaudeExecutor
from hermes_claude_bridge.schemas import ClaudeTask


def test_build_args_with_model():
    executor = ClaudeExecutor()
    task = ClaudeTask(prompt="Hello", model="opus", permissions_mode="acceptEdits")
    args = executor._build_args(task)
    assert "--model" in args
    assert "opus" in args


def test_build_args_without_model():
    executor = ClaudeExecutor()
    task = ClaudeTask(prompt="Hello", permissions_mode="acceptEdits")
    args = executor._build_args(task)
    assert "--model" not in args
