"""E2E tests for interactive Claude CLI sessions.

Interactive control of the Claude Code TUI via PTY is not robust in headless
environments. The bridge therefore implements "interactive" mode as persistent
headless sessions with conversation history. This module is kept as a skipped
experiment for future PTU-based integrations.
"""

import shutil

import pytest

from hermes_claude_bridge.interactive_executor import InteractiveExecutor


@pytest.mark.skip(
    reason=("Claude Code TUI is not reliably controllable via PTY without a real terminal")
)
@pytest.mark.asyncio
async def test_claude_interactive_simple():
    if not shutil.which("claude"):
        pytest.skip("claude CLI not installed")

    executor = InteractiveExecutor("claude")
    await executor.start()
    try:
        response = await executor.send("hi\n", timeout=60.0)
        assert response
    finally:
        await executor.stop()
