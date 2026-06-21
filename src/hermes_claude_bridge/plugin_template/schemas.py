"""Tool schemas for the Hermes plugin."""

CLAUDE_CODE_DELEGATE = {
    "name": "claude_code_delegate",
    "description": (
        "Delegate a complex coding task to Claude Code CLI running locally "
        "via the Hermes-Claude Bridge. Reuses the user's Claude Code "
        "subscription instead of consuming Anthropic API tokens."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The coding task to delegate to Claude Code.",
            },
            "context_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of file paths to include as context.",
            },
            "working_dir": {
                "type": "string",
                "description": "Working directory for the task.",
                "default": ".",
            },
            "model": {
                "type": "string",
                "description": "Model override, e.g. sonnet, opus, haiku.",
            },
            "permission_mode": {
                "type": "string",
                "description": "Claude Code permission mode.",
                "default": "acceptEdits",
                "enum": ["acceptEdits", "dontAsk", "none"],
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds.",
                "default": 300,
            },
            "bridge_url": {
                "type": "string",
                "description": (
                    "Optional bridge server URL. When provided, the tool "
                    "creates persistent sessions and keeps conversation context."
                ),
            },
            "mode": {
                "type": "string",
                "description": "Session mode when bridge_url is used.",
                "default": "headless",
                "enum": ["headless", "interactive"],
            },
            "max_history_events": {
                "type": "integer",
                "description": "Maximum prior events to include when using persistent sessions.",
                "default": 10,
            },
        },
        "required": ["prompt"],
    },
}
