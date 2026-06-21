"""End-to-end tests requiring a logged-in Claude Code CLI.

Run only when `claude` is authenticated. Otherwise these tests are skipped.
"""

import os
from pathlib import Path

import pytest

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.executor import ClaudeExecutor
from hermes_claude_bridge.schemas import ClaudeTask


@pytest.fixture
async def claude_available() -> bool:
    """Check if claude CLI is installed."""
    executor = ClaudeExecutor(bare_mode=False)
    health = await executor.health_check()
    return bool(health["claude_installed"])


@pytest.mark.asyncio
async def test_e2e_run_simple_task():
    """Run a real task through Claude Code CLI."""
    if os.getenv("SKIP_E2E"):
        pytest.skip("SKIP_E2E is set")

    bridge = HermesClaudeBridge(config=None)
    bridge.executor.bare_mode = False  # Non-bare mode uses Claude Code subscription

    result = await bridge.run_task(
        ClaudeTask(
            prompt="Return exactly the text 'pong'",
            permissions_mode="dontAsk",
            timeout_seconds=60,
        )
    )

    if "Not logged in" in result.stdout or "Please run /login" in result.stdout:
        pytest.skip("Claude Code CLI is not logged in")

    assert result.success is True
    assert "pong" in result.stdout.lower()


@pytest.mark.asyncio
async def test_e2e_file_creation(tmp_path: Path) -> None:
    """Ask Claude to create a file and verify it exists."""
    if os.getenv("SKIP_E2E"):
        pytest.skip("SKIP_E2E is set")

    bridge = HermesClaudeBridge(config=None)
    bridge.executor.bare_mode = False

    test_file = tmp_path / "claude_e2e.txt"
    result = await bridge.run_task(
        ClaudeTask(
            prompt=f"Create a file at {test_file} with the content 'E2E OK'",
            permissions_mode="acceptEdits",
            timeout_seconds=60,
            working_dir=str(tmp_path),
        )
    )

    if "Not logged in" in result.stdout or "Please run /login" in result.stdout:
        pytest.skip("Claude Code CLI is not logged in")

    assert result.success is True
    assert test_file.read_text().strip() == "E2E OK"
