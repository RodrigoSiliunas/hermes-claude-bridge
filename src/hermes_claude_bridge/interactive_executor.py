"""Interactive executor that keeps a subprocess alive across prompts."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class InteractiveExecutor:
    """Run a command interactively: keep stdin/stdout open and send messages."""

    def __init__(self, command: str, *args: str):
        self.command = command
        self.args = args
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the underlying subprocess."""
        if self._process is not None:
            return
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info("Interactive executor started", command=self.command)

    async def stop(self) -> None:
        """Terminate the subprocess."""
        if self._process is None:
            return
        try:
            self._process.terminate()
            await asyncio.wait_for(self._process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self._process.kill()
            await self._process.wait()
        finally:
            self._process = None
            logger.info("Interactive executor stopped")

    async def send(self, message: str, timeout: float = 30.0) -> str:
        """Send a message to the process and read the response.

        The response is read until no new data arrives for `read_timeout`
        seconds, which is a simple heuristic for command completion.
        """
        if self._process is None:
            raise RuntimeError("Executor not started. Call start() first.")

        async with self._lock:
            assert self._process.stdin is not None
            assert self._process.stdout is not None

            self._process.stdin.write(message.encode())
            await self._process.stdin.drain()

            output_chunks: list[bytes] = []
            read_timeout = 0.5

            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self._process.stdout.read(4096),
                        timeout=read_timeout,
                    )
                    if not chunk:
                        break
                    output_chunks.append(chunk)
                except asyncio.TimeoutError:
                    break

            return b"".join(output_chunks).decode(errors="replace")

    async def health_check(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "args": list(self.args),
            "running": self._process is not None and self._process.returncode is None,
        }
