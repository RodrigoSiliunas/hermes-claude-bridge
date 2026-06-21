"""Tests for hermes_claude_bridge.interactive_executor."""

import pytest

from hermes_claude_bridge.interactive_executor import InteractiveExecutor


@pytest.mark.asyncio
async def test_interactive_executor_echo():
    """Use cat as a stand-in for an interactive process."""
    executor = InteractiveExecutor("cat")
    await executor.start()
    try:
        response = await executor.send("hello\n")
        assert "hello" in response
    finally:
        await executor.stop()


@pytest.mark.asyncio
async def test_interactive_executor_not_started():
    executor = InteractiveExecutor("cat")
    with pytest.raises(RuntimeError):
        await executor.send("hello\n")
