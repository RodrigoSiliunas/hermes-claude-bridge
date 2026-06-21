"""Hermes-compatible tool adapter for Claude Code delegation.

This adapter lets Hermes Agent register `claude_code_delegate` as a tool
and delegate complex coding tasks to Claude Code CLI without consuming
Anthropic API tokens.
"""

from __future__ import annotations

import os
from typing import Any

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.schemas import ClaudeTask


class ClaudeBridgeTool:
    """Hermes-compatible tool adapter for Claude Code delegation.

    Usage in a Hermes skill or agent:

        tool = ClaudeBridgeTool()
        schema = tool.get_schema()  # Register with Hermes
        result = await tool.invoke({
            "prompt": "Refactor the auth module",
            "context_files": ["src/auth.py"],
        })
    """

    def __init__(self, bridge: HermesClaudeBridge | None = None):
        self.bridge = bridge or HermesClaudeBridge()

    def get_schema(self) -> dict[str, Any]:
        """Return JSON Schema for Hermes tool registration."""
        return {
            "name": "claude_code_delegate",
            "description": (
                "Delegate a coding task to Claude Code CLI running locally. "
                "Use for complex refactoring, debugging, or multi-file changes. "
                "Requires claude CLI to be installed and authenticated."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task description to send to Claude",
                    },
                    "context_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to include as context",
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory (defaults to current)",
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 300,
                        "description": "Timeout in seconds",
                    },
                    "permission_mode": {
                        "type": "string",
                        "enum": ["dontAsk", "acceptEdits", "default"],
                        "default": "acceptEdits",
                        "description": "Claude permission mode",
                    },
                },
                "required": ["prompt"],
            },
        }

    async def invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        """Invoke the bridge with given parameters."""
        task = ClaudeTask(
            prompt=params["prompt"],
            context_files=params.get("context_files", []),
            working_dir=params.get("working_dir") or os.getcwd(),
            timeout_seconds=params.get("timeout", 300),
            permissions_mode=params.get("permission_mode", "acceptEdits"),
        )
        result = await self.bridge.run_task(task)
        return {
            "success": result.success,
            "task_id": result.task_id,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "file_edits": [
                {"path": e.path, "operation": e.operation, "diff": e.diff}
                for e in result.file_edits
            ],
            "bash_commands": [
                {"command": c.command, "exit_code": c.exit_code} for c in result.bash_commands
            ],
            "duration_seconds": result.duration_seconds,
            "error": result.error_message,
        }
