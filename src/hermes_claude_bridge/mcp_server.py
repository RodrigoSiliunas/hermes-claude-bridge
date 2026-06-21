"""MCP server exposing the Hermes-Claude Bridge as a tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.schemas import ClaudeTask


def create_mcp_server() -> FastMCP:
    """Create an MCP server with the claude_code_delegate tool."""
    mcp = FastMCP("hermes-claude-bridge", json_response=True)

    @mcp.tool()
    async def claude_code_delegate(
        prompt: str,
        context_files: list[str] | None = None,
        working_dir: str = ".",
        model: str | None = None,
        permission_mode: str = "acceptEdits",
        timeout: int = 300,
    ) -> dict:
        """Delegate a coding task to Claude Code CLI running locally.

        Use this for complex refactoring, debugging, or multi-file changes.
        Requires the `claude` CLI to be installed and authenticated.
        """
        bridge = HermesClaudeBridge()
        result = await bridge.run_task(
            ClaudeTask(
                prompt=prompt,
                context_files=context_files or [],
                working_dir=working_dir,
                model=model,
                permissions_mode=permission_mode,  # type: ignore[arg-type]
                timeout_seconds=timeout,
            )
        )
        return result.model_dump()

    return mcp


mcp = create_mcp_server()
