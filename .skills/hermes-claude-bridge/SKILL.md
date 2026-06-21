---
name: hermes-claude-bridge
description: "Delegate complex coding tasks from Hermes to Claude Code CLI — zero Anthropic API cost."
version: 0.1.0
author: Rodrigo Siliunas
license: MIT
tags: [hermes, claude-code, bridge, delegation, coding-agent]
platforms: [linux, macos, windows]
---

# Hermes-Claude Bridge Skill

This skill lets Hermes Agent delegate deep coding tasks to **Claude Code CLI**
running locally, reusing an existing Claude Code Pro/Team subscription instead
of consuming Anthropic API tokens.

## When to use

Use `claude_code_delegate` when Hermes alone would struggle with:

- Multi-file refactoring across a codebase.
- Complex debugging requiring many tool calls.
- Writing or updating tests, docs, and configuration together.
- Any task where Claude Code's specialized coding agent loop is more efficient.

Do **not** use it for:

- Simple one-off questions that Hermes can answer directly.
- Tasks that do not require file edits or command execution.
- Environments where `claude` CLI is not installed or authenticated.

## Prerequisites

1. Install the Python package:

   ```bash
   pip install hermes-claude-bridge
   ```

2. Ensure `claude` CLI is installed and logged in:

   ```bash
   claude --version
   # If not logged in, run interactively:
   claude /login
   ```

3. (Recommended) Set environment variables for non-bare mode — this reuses the
   Claude Code subscription instead of Anthropic API tokens:

   ```bash
   export CLAUDE_BARE=false
   export CLAUDE_PERMISSIONS=acceptEdits
   ```

## Tool registration

When this skill is loaded, register the following tool in your agent:

```python
from hermes_claude_bridge.hermes_adapter import ClaudeBridgeTool

tool = ClaudeBridgeTool()
schema = tool.get_schema()
# Register schema with your Hermes agent runtime.
```

## Tool schema: `claude_code_delegate`

```json
{
  "name": "claude_code_delegate",
  "description": "Delegate a coding task to Claude Code CLI running locally. Use for complex refactoring, debugging, or multi-file changes. Requires claude CLI to be installed and authenticated.",
  "parameters": {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "The task description to send to Claude"
      },
      "context_files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of file paths to include as context"
      },
      "working_dir": {
        "type": "string",
        "description": "Working directory (defaults to current)"
      },
      "timeout": {
        "type": "integer",
        "default": 300,
        "description": "Timeout in seconds"
      },
      "permission_mode": {
        "type": "string",
        "enum": ["dontAsk", "acceptEdits", "default"],
        "default": "acceptEdits",
        "description": "Claude permission mode"
      }
    },
    "required": ["prompt"]
  }
}
```

## Invocation example

```python
result = await tool.invoke({
    "prompt": "Refactor auth.py to use dependency injection",
    "context_files": ["src/auth.py"],
    "permission_mode": "acceptEdits",
    "timeout": 300,
})
```

## Result format

The tool returns a dictionary with:

- `success` (bool): Whether Claude exited cleanly.
- `task_id` (str): Unique task identifier.
- `stdout` / `stderr` (str): Raw CLI output.
- `file_edits` (list): Structured file edits (`path`, `operation`, `diff`).
- `bash_commands` (list): Commands Claude attempted to run.
- `duration_seconds` (float): Wall-clock duration.
- `error` (str | None): Error message if the task failed.

## Safety guidelines

- Prefer `acceptEdits` mode unless you fully trust the delegated task.
- Never pass secrets or credentials in the prompt.
- Review file edits in `result["file_edits"]` before accepting them in production.
- Run E2E tests with `pytest tests/test_e2e.py` to confirm local auth works.

## References

- Repository: https://github.com/RodrigoSiliunas/hermes-claude-bridge
- Claude Code docs: https://docs.anthropic.com/en/docs/claude-code/overview
