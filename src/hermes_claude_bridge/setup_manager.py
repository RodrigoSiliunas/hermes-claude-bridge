"""Manage Hermes Agent integration setup."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

MODEL_PRESETS = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
    "haiku": "claude-haiku-3-20240307",
}


def generate_mcp_config(
    command: str = "hermes-claude",
    args: list[str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Return an MCP server config snippet for Hermes Agent.

    The result can be merged into ``~/.hermes/config.yaml`` under the
    ``mcp_servers`` key.
    """
    env: dict[str, str] = {}
    if model:
        env["CLAUDE_MODEL"] = MODEL_PRESETS.get(model, model)
    return {
        "mcp_servers": {
            "hermes-claude-bridge": {
                "command": command,
                "args": args or ["mcp-server"],
                "env": env,
                "enabled": True,
            }
        }
    }


def install_hermes_plugin(plugins_dir: str) -> str:
    """Install the Hermes plugin template into ``plugins_dir``.

    Returns the path to the installed plugin directory.
    """
    src = Path(__file__).parent / "plugin_template"
    dst = Path(plugins_dir) / "hermes-claude-bridge"
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return str(dst)
