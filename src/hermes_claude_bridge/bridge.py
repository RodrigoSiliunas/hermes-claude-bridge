"""Main bridge service between Hermes and Claude Code CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

from hermes_claude_bridge.config import BridgeConfig
from hermes_claude_bridge.executor import ClaudeExecutor
from hermes_claude_bridge.parser import OutputParser
from hermes_claude_bridge.schemas import ClaudeResult, ClaudeTask

logger = structlog.get_logger(__name__)


class HermesClaudeBridge:
    """Main bridge service between Hermes and Claude Code CLI."""

    def __init__(self, config: BridgeConfig | None = None):
        self.config = config or BridgeConfig.from_env()
        self.executor = ClaudeExecutor(self.config.claude_executable)
        self.parser = OutputParser()

    async def health(self) -> dict:
        """Return health status of the bridge."""
        claude_health = await self.executor.health_check()
        wd = self.config.working_dir
        return {
            **claude_health,
            "working_dir": str(wd),
            "working_dir_readable": wd.exists() and wd.is_dir(),
            "working_dir_writable": self._is_writable(wd),
        }

    def _is_writable(self, path: Path) -> bool:
        try:
            test_file = path / ".bridge_write_test"
            test_file.write_text("")
            test_file.unlink()
            return True
        except OSError:
            return False

    async def run_task(self, task: ClaudeTask) -> ClaudeResult:
        """Execute a task through Claude Code CLI."""
        logger.info("Bridge received task", task_id=task.task_id)

        # Merge config defaults
        if task.working_dir is None:
            task.working_dir = str(self.config.working_dir)
        if not task.timeout_seconds:
            task.timeout_seconds = self.config.timeout_seconds

        result = await self.executor.execute(task)
        result = self.parser.enrich_result(result)

        logger.info(
            "Bridge completed task",
            task_id=task.task_id,
            success=result.success,
            duration=result.duration_seconds,
            edits=len(result.file_edits),
        )
        return result

    async def run_batch(self, tasks: list[ClaudeTask]) -> list[ClaudeResult]:
        """Run multiple tasks concurrently."""
        return await asyncio.gather(*[self.run_task(t) for t in tasks])
