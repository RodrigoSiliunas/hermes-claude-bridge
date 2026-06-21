"""Async executor for Claude Code CLI."""

from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path

import structlog

from hermes_claude_bridge.schemas import BashCommand, ClaudeResult, ClaudeTask

logger = structlog.get_logger(__name__)


class ClaudeExecutor:
    """Executes Claude Code CLI tasks and captures results."""

    def __init__(self, claude_executable: str = "claude", bare_mode: bool = True):
        self.claude_executable = claude_executable
        self.bare_mode = bare_mode

    async def health_check(self) -> dict:
        """Check if claude CLI is available."""
        claude_path = shutil.which(self.claude_executable)
        version: str | None = None
        if claude_path:
            try:
                proc = await asyncio.create_subprocess_exec(
                    claude_path,
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                version = stdout.decode().strip()
            except Exception:
                pass
        return {
            "claude_installed": claude_path is not None,
            "claude_version": version,
            "claude_path": claude_path,
        }

    def _build_args(self, task: ClaudeTask, bare_mode: bool | None = None) -> list[str]:
        """Build claude CLI arguments from task."""
        if bare_mode is None:
            bare_mode = self.bare_mode

        args = [self.claude_executable]

        if task.permissions_mode == "dontAsk":
            args.append("--dangerously-skip-permissions")
        elif task.permissions_mode == "acceptEdits":
            args.extend(["--permission-mode", "acceptEdits"])

        if task.allowed_tools:
            for tool in task.allowed_tools:
                args.extend(["--allowedTools", tool])

        if bare_mode:
            args.append("--bare")

        args.extend(["-p", task.prompt])

        if task.system_prompt_append:
            args.extend(["--append-system-prompt", task.system_prompt_append])

        return args

    async def run_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        timeout: int = 60,
    ) -> BashCommand:
        """Run a generic command and capture output."""
        logger.info("Running command", command=" ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            stdout_b, stderr_b = await proc.communicate()
            return BashCommand(
                command=" ".join(cmd),
                stdout=stdout_b.decode(errors="replace"),
                stderr=stderr_b.decode(errors="replace") + "\n[TIMEOUT]",
                exit_code=-1,
            )

        return BashCommand(
            command=" ".join(cmd),
            stdout=stdout_b.decode(errors="replace"),
            stderr=stderr_b.decode(errors="replace"),
            exit_code=proc.returncode or 0,
        )

    async def execute(self, task: ClaudeTask) -> ClaudeResult:
        """Execute a Claude task and return structured result."""
        start = time.monotonic()
        health = await self.health_check()

        if not health["claude_installed"]:
            return ClaudeResult(
                task_id=task.task_id,
                success=False,
                error_message=f"Claude CLI not found: {self.claude_executable}",
                duration_seconds=time.monotonic() - start,
            )

        args = self._build_args(task)
        cwd = Path(task.working_dir) if task.working_dir else Path.cwd()

        logger.info("Executing Claude task", task_id=task.task_id, cwd=str(cwd))

        cmd_result = await self.run_command(args, cwd=cwd, timeout=task.timeout_seconds)

        duration = time.monotonic() - start

        return ClaudeResult(
            task_id=task.task_id,
            success=cmd_result.exit_code == 0,
            stdout=cmd_result.stdout,
            stderr=cmd_result.stderr,
            exit_code=cmd_result.exit_code,
            raw_output=cmd_result.stdout + "\n" + cmd_result.stderr,
            duration_seconds=duration,
            error_message=cmd_result.stderr if cmd_result.exit_code != 0 else None,
        )
