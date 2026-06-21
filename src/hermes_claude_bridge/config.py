"""Configuration for Hermes-Claude Bridge."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class BridgeConfig(BaseModel):
    """Configuration for Hermes-Claude Bridge."""

    claude_executable: str = Field(default="claude", description="Path to claude CLI")
    working_dir: Path = Field(default=Path.cwd(), description="Directory where claude runs")
    timeout_seconds: int = Field(default=300, description="Max seconds per claude task")
    bare_mode: bool = Field(default=True, description="Use --bare for reproducibility")
    allowed_tools: list[str] = Field(
        default_factory=lambda: ["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
        description="Tools claude is allowed to use",
    )
    permissions_mode: str = Field(
        default="acceptEdits",
        description="Permission mode: dontAsk, acceptEdits, or default",
    )

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """Load configuration from environment variables."""
        return cls(
            claude_executable=os.getenv("CLAUDE_EXECUTABLE", "claude"),
            working_dir=Path(os.getenv("CLAUDE_WORKING_DIR", str(Path.cwd()))),
            timeout_seconds=int(os.getenv("CLAUDE_TIMEOUT", "300")),
            bare_mode=os.getenv("CLAUDE_BARE", "true").lower() == "true",
            permissions_mode=os.getenv("CLAUDE_PERMISSIONS", "acceptEdits"),
        )
