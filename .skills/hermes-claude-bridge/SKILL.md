---
name: hermes-claude-bridge
description: "Delegate complex coding tasks from Hermes to Claude Code CLI — persistent contextual sessions, real-time SSE events, model selection, human-in-the-loop, MCP server, native Hermes plugin and one-command setup."
version: 0.6.0
author: Rodrigo Siliunas
license: MIT
tags: [hermes, claude-code, bridge, delegation, coding-agent, sse, sessions, human-in-the-loop, mcp, plugin, setup]
platforms: [linux, macos, windows]
---

# Hermes-Claude Bridge Skill

This skill lets Hermes Agent delegate deep coding tasks to **Claude Code CLI**
running locally, reusing an existing Claude Code Pro/Team subscription instead
of consuming Anthropic API tokens.

Version 0.5 adds **plug-and-play Hermes integration**: generate an MCP config
snippet or install a native Hermes plugin with one command.

Version 0.4 added an **MCP server** so Hermes can consume the bridge as a native
MCP tool, plus **history filtering** and **context compression** for long-running
sessions.

Version 0.3 added **persistent contextual sessions**. The bridge keeps session
history in a database and replays prior prompts/answers into each new Claude
request, so Claude does not lose context across turns.

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

3. Start the bridge event server:

   ```bash
   hermes-claude server --port 8765
   ```

4. (Recommended) Set environment variables for non-bare mode — this reuses the
   Claude Code subscription instead of Anthropic API tokens:

   ```bash
   export CLAUDE_BARE=false
   export CLAUDE_PERMISSIONS=acceptEdits
   ```

## Architecture

```
Hermes Agent ←—— SSE ——→ Hermes-Claude Bridge Server
                              ↓
                   Session Manager (SQLite/Postgres)
                              ↓
                   Claude Code CLI (`claude -p`)
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
      "model": {
        "type": "string",
        "default": null,
        "description": "Claude model alias: sonnet, opus, haiku, or full name"
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

## Setup in Hermes Agent

Choose one of the two integration paths.

### Option A: MCP server

Generate the MCP config snippet and append it to `~/.hermes/config.yaml`:

```bash
hermes-claude setup --mcp-config >> ~/.hermes/config.yaml
```

With a default model preset:

```bash
hermes-claude setup --mcp-config --model sonnet >> ~/.hermes/config.yaml
```

On next startup, Hermes discovers the `claude_code_delegate` tool from the
`hermes-claude-bridge` MCP server.

### Option B: Native Hermes plugin

Install the plugin:

```bash
hermes-claude setup --hermes-plugin
```

Then enable it in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - hermes-claude-bridge
```

Set a default bridge URL via environment variable so the plugin reuses
persistent sessions automatically:

```bash
export HERMES_CLAUDE_BRIDGE_URL=http://localhost:8765
```

Restart Hermes.

## Invocation example

```python
result = await tool.invoke({
    "prompt": "Refactor auth.py to use dependency injection",
    "context_files": ["src/auth.py"],
    "model": "sonnet",
    "permission_mode": "acceptEdits",
})
```

Or, for persistent sessions via the bridge server:
## Persistent contextual sessions

When using the bridge server, create a session with `mode="interactive"` to keep
context across multiple prompts:

```python
from hermes_claude_bridge.client import BridgeClient

client = BridgeClient("http://localhost:8765")

session = await client.create_session(
    working_dir="/path/to/project",
    mode="interactive",
    model="sonnet",
)
session_id = session["session_id"]

result = await client.send_prompt(
    session_id,
    "Refactor auth.py to use dependency injection",
    context_files=["src/auth.py"],
)

if result["status"] == "waiting_user_input":
    answer = input(result["pending_question"] + " ")
    result = await client.answer_question(session_id, answer)
```

The bridge stores every prompt, answer and Claude response in the database and
automatically includes the conversation history in subsequent requests.

## History filtering and compression

Long sessions can exceed the context window. Set `max_history_events` when
creating a session to keep only the most recent N relevant events:

```python
session = await client.create_session(
    working_dir="/path/to/project",
    mode="interactive",
    max_history_events=5,
)
```

When the history exceeds the limit, older events are replaced by a summary line
(`X earlier messages omitted.`) so Claude still knows the conversation is
ongoing without receiving every old message.

## MCP server

Expose the bridge as a native MCP tool:

```bash
hermes-claude mcp-server
```

The tool `claude_code_delegate` is then available to any MCP client (including
Hermes Agent when configured with MCP support). For stateless single tasks:

```json
{
  "prompt": "Refactor auth.py",
  "context_files": ["src/auth.py"],
  "model": "sonnet"
}
```

For persistent sessions, point the tool at a running bridge server:

```json
{
  "prompt": "Refactor auth.py",
  "bridge_url": "http://localhost:8765",
  "mode": "interactive"
}
```

## Handling Claude questions (human-in-the-loop)

When Claude asks a question, the result will have:

```json
{
  "success": true,
  "status": "waiting_user_input",
  "pending_question": "Should I delete the old implementation?"
}
```

Your Hermes agent should:

1. Pause the task.
2. Ask the user the `pending_question`.
3. Send the answer back with:

```python
from hermes_claude_bridge.client import BridgeClient

client = BridgeClient()
await client.answer_question(session_id, "Yes, delete it.")
```

## Result format

The tool returns a dictionary with:

- `success` (bool): Whether Claude exited cleanly.
- `task_id` (str): Unique task identifier.
- `status` (str): `active`, `waiting_user_input`, `completed`, or `failed`.
- `pending_question` (str | None): Question Claude asked, if any.
- `stdout` / `stderr` (str): Raw CLI output.
- `file_edits` (list): Structured file edits (`path`, `operation`, `diff`).
- `bash_commands` (list): Commands Claude attempted to run.
- `duration_seconds` (float): Wall-clock duration.
- `error` (str | None): Error message if the task failed.

## Model selection

Set a default model via environment variable:

```bash
export CLAUDE_MODEL=sonnet
```

Or pass per-task in the tool invocation:

```python
"model": "opus"
```

## Safety guidelines

- Prefer `acceptEdits` mode unless you fully trust the delegated task.
- Never pass secrets or credentials in the prompt.
- Review file edits in `result["file_edits"]` before accepting them in production.
- Run E2E tests with `pytest tests/test_e2e.py` to confirm local auth works.

## References

- Repository: https://github.com/RodrigoSiliunas/hermes-claude-bridge
- Claude Code docs: https://docs.anthropic.com/en/docs/claude-code/overview
