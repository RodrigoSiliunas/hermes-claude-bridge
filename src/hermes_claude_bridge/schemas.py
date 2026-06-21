"""Data schemas for Hermes-Claude Bridge."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class FileEdit(BaseModel):
    """Represents a file edit performed by Claude."""

    path: str
    diff: str | None = None
    full_content: str | None = None
    operation: Literal["edit", "create", "delete"] = "edit"


class BashCommand(BaseModel):
    """Represents a bash command executed by Claude."""

    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


class ClaudeTask(BaseModel):
    """Task sent from Hermes to Claude Bridge."""

    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    prompt: str
    context_files: list[str] = Field(default_factory=list)
    system_prompt_append: str | None = None
    working_dir: str | None = None
    timeout_seconds: int = 300
    permissions_mode: Literal["dontAsk", "acceptEdits", "default"] = "acceptEdits"
    allowed_tools: list[str] = Field(
        default_factory=lambda: ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
    )


class ClaudeResult(BaseModel):
    """Result returned from Claude Bridge to Hermes."""

    task_id: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    file_edits: list[FileEdit] = Field(default_factory=list)
    bash_commands: list[BashCommand] = Field(default_factory=list)
    raw_output: str = ""
    duration_seconds: float = 0.0
    error_message: str | None = None


class BridgeHealth(BaseModel):
    """Health check response."""

    claude_installed: bool
    claude_version: str | None = None
    working_dir_readable: bool
    working_dir_writable: bool
