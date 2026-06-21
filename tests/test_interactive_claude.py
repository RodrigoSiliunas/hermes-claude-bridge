"""E2E tests for interactive Claude CLI sessions.

Run only when `claude` is authenticated. Otherwise these tests are skipped.
"""

import re
import shutil

import pytest

from hermes_claude_bridge.interactive_executor import InteractiveExecutor


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("claude"), reason="claude CLI not installed")
async def test_claude_interactive_simple():
    executor = InteractiveExecutor("claude")
    await executor.start()
    try:
        # Claude Code asks for workspace trust on first launch.
        intro = await executor.send("\n", timeout=10.0)
        if "trust" in _strip_ansi(intro).lower() or "safety" in _strip_ansi(intro).lower():
            await executor.send("yes\n", timeout=10.0)

        response = await executor.send("say exactly: hello from interactive\n", timeout=60.0)
        assert "hello" in _strip_ansi(response).lower()
    finally:
        await executor.stop()
