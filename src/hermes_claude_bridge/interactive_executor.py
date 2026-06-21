"""Interactive executor that keeps a subprocess alive across prompts."""

from __future__ import annotations

import asyncio
import os
import pty
import shutil
import termios
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class InteractiveExecutor:
    """Run a command interactively using a pseudo-terminal (PTY).

    This is required for programs such as Claude Code that expect a TTY.
    """

    def __init__(self, command: str, *args: str):
        self.command = command
        self.args = args
        self._process: asyncio.subprocess.Process | None = None
        self._master_fd: int | None = None
        self._slave_fd: int | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the underlying subprocess attached to a PTY."""
        if self._process is not None:
            return

        if not shutil.which(self.command):
            raise RuntimeError(f"Command not found: {self.command}")

        self._master_fd, self._slave_fd = pty.openpty()
        # Disable echo so we don't read back our own input.
        attrs = termios.tcgetattr(self._slave_fd)
        attrs[3] = attrs[3] & ~termios.ECHO
        termios.tcsetattr(self._slave_fd, termios.TCSANOW, attrs)

        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=self._slave_fd,
            stdout=self._slave_fd,
            stderr=self._slave_fd,
            cwd=None,
        )
        os.close(self._slave_fd)
        self._slave_fd = None

        # Set master fd to non-blocking.
        os.set_blocking(self._master_fd, False)

        logger.info("Interactive executor started", command=self.command)

    async def stop(self) -> None:
        """Terminate the subprocess and close PTY fds."""
        if self._process is None:
            return
        try:
            self._process.terminate()
            await asyncio.wait_for(self._process.wait(), timeout=5.0)
        except TimeoutError:
            self._process.kill()
            await self._process.wait()
        finally:
            if self._master_fd is not None:
                os.close(self._master_fd)
                self._master_fd = None
            self._process = None
            logger.info("Interactive executor stopped")

    async def send(self, message: str, timeout: float = 60.0) -> str:
        """Send a message to the process and read the response.

        The response is read until no new data arrives for a short quiet
        period, which is a heuristic for command completion.
        """
        if self._process is None or self._master_fd is None:
            raise RuntimeError("Executor not started. Call start() first.")

        async with self._lock:
            assert self._master_fd is not None
            os.write(self._master_fd, message.encode())

            output_chunks: list[bytes] = []
            quiet_timeout = 0.5
            total_deadline = asyncio.get_event_loop().time() + timeout

            while asyncio.get_event_loop().time() < total_deadline:
                try:
                    chunk = os.read(self._master_fd, 4096)
                    if chunk:
                        output_chunks.append(chunk)
                        continue
                except BlockingIOError:
                    pass
                except OSError:
                    break

                # Wait a bit for more output.
                wait_time = min(quiet_timeout, total_deadline - asyncio.get_event_loop().time())
                if wait_time <= 0:
                    break
                await asyncio.sleep(wait_time)

                try:
                    chunk = os.read(self._master_fd, 4096)
                    if chunk:
                        output_chunks.append(chunk)
                        continue
                except BlockingIOError:
                    pass
                except OSError:
                    break

                # No new data after quiet period; assume response is complete.
                break

            return b"".join(output_chunks).decode(errors="replace")

    async def health_check(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "args": list(self.args),
            "running": self._process is not None and self._process.returncode is None,
        }
