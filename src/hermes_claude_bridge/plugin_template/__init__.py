"""Hermes plugin registration for hermes-claude-bridge."""

from __future__ import annotations

from typing import Any

from . import schemas, tools


def register(ctx: Any) -> None:
    """Wire the claude_code_delegate tool into Hermes."""
    ctx.register_tool(
        name="claude_code_delegate",
        toolset="hermes-claude-bridge",
        schema=schemas.CLAUDE_CODE_DELEGATE,
        handler=tools.handle_delegate,
        description="Delegate coding tasks to Claude Code CLI via the bridge.",
        is_async=True,
    )
