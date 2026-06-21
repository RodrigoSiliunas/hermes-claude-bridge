"""Manage Hermes Agent integration setup."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def generate_mcp_config(
    command: str = "hermes-claude",
    args: list[str] | None = None,
) -> dict[str, Any]:
    """Return an MCP server config snippet for Hermes Agent.

    The result can be merged into ``~/.hermes/config.yaml`` under the
    ``mcp_servers`` key.
    """
    return {
        "mcp_servers": {
            "hermes-claude-bridge": {
                "command": command,
                "args": args or ["mcp-server"],
                "env": {},
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
