"""CLI entry point for Hermes-Claude Bridge."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.schemas import ClaudeTask


def _json_dumps(obj: Any) -> str:
    """Dump object to JSON, handling Path and other non-serializable types."""
    return json.dumps(obj, indent=2, default=str)


@click.group()
@click.option("--working-dir", "-d", default=".", help="Working directory for Claude")
@click.option("--claude-exe", default="claude", help="Path to claude executable")
@click.pass_context
def cli(ctx: click.Context, working_dir: str, claude_exe: str) -> None:
    """Hermes-Claude Bridge — delegate tasks to Claude Code CLI."""
    ctx.ensure_object(dict)
    ctx.obj["bridge"] = HermesClaudeBridge()
    ctx.obj["working_dir"] = working_dir
    ctx.obj["claude_exe"] = claude_exe


@cli.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Check bridge and Claude CLI health."""
    bridge = ctx.obj["bridge"]
    result = asyncio.run(bridge.health())
    click.echo(_json_dumps(result))


@cli.command()
@click.argument("prompt")
@click.option("--file", "-f", multiple=True, help="Context files to include")
@click.option("--timeout", "-t", default=300, help="Timeout in seconds")
@click.option("--mode", default="acceptEdits", help="Permission mode")
@click.pass_context
def run(ctx: click.Context, prompt: str, file: tuple[str, ...], timeout: int, mode: str) -> None:
    """Run a single prompt through Claude Code."""
    bridge = ctx.obj["bridge"]
    task = ClaudeTask(
        prompt=prompt,
        context_files=list(file),
        working_dir=ctx.obj["working_dir"],
        timeout_seconds=timeout,
        permissions_mode=mode,  # type: ignore[arg-type]
    )
    result = asyncio.run(bridge.run_task(task))
    click.echo(_json_dumps(result.model_dump()))


@cli.command()
@click.argument("prompt_file", type=click.File("r"))
@click.pass_context
def run_file(ctx: click.Context, prompt_file) -> None:
    """Run a prompt from a file."""
    bridge = ctx.obj["bridge"]
    prompt = prompt_file.read()
    task = ClaudeTask(
        prompt=prompt,
        working_dir=ctx.obj["working_dir"],
    )
    result = asyncio.run(bridge.run_task(task))
    click.echo(_json_dumps(result.model_dump()))


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8765, help="Server port")
@click.option("--database-url", default=None, help="Database URL")
def server(host: str, port: int, database_url: str | None) -> None:
    """Start the Hermes-Claude Bridge event server."""
    import os

    import uvicorn

    if database_url:
        os.environ["DATABASE_URL"] = database_url
    uvicorn.run(
        "hermes_claude_bridge.server:create_app",
        factory=True,
        host=host,
        port=port,
    )


@cli.command(name="mcp-server")
@click.option("--transport", default="stdio", help="MCP transport: stdio or sse")
def mcp_server(transport: str) -> None:
    """Start the Hermes-Claude Bridge as an MCP server."""
    from hermes_claude_bridge.mcp_server import mcp

    mcp.run(transport=transport)


if __name__ == "__main__":
    cli()
