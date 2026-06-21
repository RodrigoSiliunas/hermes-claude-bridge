# Hermes-Claude Bridge

[![CI](https://github.com/RodrigoSiliunas/hermes-claude-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/RodrigoSiliunas/hermes-claude-bridge/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/RodrigoSiliunas/hermes-claude-bridge?logo=github)](https://github.com/RodrigoSiliunas/hermes-claude-bridge/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Delegate development tasks from [Hermes Agent](https://hermes-agent.nousresearch.com/) to [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview) — zero additional Anthropic API cost.

> **Status:** early development. API may change until v1.0.0.

## Why?

- You already pay for Claude Code (Pro / Team / Enterprise) — reuse that subscription.
- Hermes handles orchestration, memory, and multi-tool workflows.
- Claude Code handles deep, multi-file coding tasks.
- No Anthropic API tokens are consumed for delegated work.

## What problem does this solve?

**Omni** ([automagik-dev/omni](https://github.com/automagik-dev/omni)) showed that Telegram and other channels can talk to Claude Code. This bridge does the same for the **Hermes Agent** ecosystem, but focused on:

- **No extra API costs** — reuse the Claude Code CLI subscription.
- **Persistent contextual sessions** — SQLite/PostgreSQL store keeps full conversation history; every new prompt includes prior context.
- **Real-time events** — SSE stream delivers events instantly via `asyncio.Condition`, no polling.
- **Human-in-the-loop** — when Claude asks a question, the bridge pauses and asks the user.
- **Model selection** — choose `sonnet`, `opus`, `haiku`, or any full model name.
- **Headless / scriptable** — run `claude -p --bare` from Python/asyncio.
- **Structured results** — parse file edits, bash commands, and errors from Claude's output.
- **Hermes-native** — register as a tool (`claude_code_delegate`) inside Hermes skills.

## Installation

```bash
pip install hermes-claude-bridge
```

Requires `claude` CLI installed and authenticated:

```bash
claude --version
```

## Quick Start

### CLI

```bash
# Check if claude is available
hermes-claude health

# Run a single task
hermes-claude run "Refactor auth.py to use dependency injection" -f src/auth.py

# Run from a file
hermes-claude run-file prompt.md
```

### Python API

```python
import asyncio
from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.schemas import ClaudeTask

async def main():
    bridge = HermesClaudeBridge()
    result = await bridge.run_task(ClaudeTask(
        prompt="Add type hints to all functions",
        context_files=["src/main.py"],
    ))
    print(result.model_dump_json(indent=2))

asyncio.run(main())
```

### Server mode (stateful)

Start the bridge server for persistent sessions and real-time SSE events:

```bash
hermes-claude server --port 8765
```

Then use the Python client from Hermes:

```python
import asyncio
from hermes_claude_bridge.client import BridgeClient

async def main():
    client = BridgeClient("http://localhost:8765")

    # Use mode="interactive" to keep conversation context across prompts.
    session = await client.create_session(
        working_dir="/path/to/project",
        model="sonnet",
        mode="interactive",
    )
    result = await client.send_prompt(
        session["session_id"],
        "Refactor auth.py to use dependency injection",
        context_files=["src/auth.py"],
    )
    print(result)

    if result.get("status") == "waiting_user_input":
        question = result["pending_question"]
        # Ask the user, then:
        await client.answer_question(session["session_id"], "Yes, proceed.")

asyncio.run(main())
```

### Hermes Skill

Install the skill into your Hermes profile:

```bash
cp -r .skills/hermes-claude-bridge ~/.hermes/skills/
```

Then register the tool in your agent:

```python
from hermes_claude_bridge.hermes_adapter import ClaudeBridgeTool

tool = ClaudeBridgeTool()
schema = tool.get_schema()  # Register with Hermes
result = await tool.invoke({
    "prompt": "Refactor auth.py",
    "context_files": ["src/auth.py"],
    "model": "sonnet",
    "permission_mode": "acceptEdits",
    "timeout": 300,
})
```

See `.skills/hermes-claude-bridge/SKILL.md` for the full skill definition.

## Architecture

```
Hermes Agent
    |
    v
+----------------------------------+
|  BridgeClient or ClaudeBridgeTool|
|  - HTTP client / tool adapter    |
+----------------------------------+
    |
    | SSE / HTTP
    v
+----------------------------------+
|  Hermes-Claude Bridge Server     |
|  - FastAPI + SSE streaming       |
|  - Session Manager (SQLAlchemy)  |
+----------------------------------+
    |
    v
+----------------------------------+
|  HermesClaudeBridge (orchestrator)|
|  - Task execution                |
|  - Health checks                 |
+----------------------------------+
    |
    v
+----------------------------------+
|  ClaudeExecutor (subprocess)     |
|  - claude -p [--bare]            |
|  - Async subprocess + timeout    |
+----------------------------------+
    |
    v
+----------------------------------+
|  OutputParser                    |
|  - Extract file edits            |
|  - Extract bash commands         |
|  - Detect questions              |
+----------------------------------+
    |
    v
  Result (JSON)
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_EXECUTABLE` | `claude` | Path to claude CLI |
| `CLAUDE_WORKING_DIR` | `.` | Default working directory |
| `CLAUDE_TIMEOUT` | `300` | Default timeout in seconds |
| `CLAUDE_BARE` | `true` | Use `--bare` mode |
| `CLAUDE_PERMISSIONS` | `acceptEdits` | Default permission mode |
| `CLAUDE_MODEL` | `None` | Default Claude model |
| `DATABASE_URL` | `sqlite+aiosqlite:///./hermes_claude_bridge.db` | Async database URL |

## Permission Modes

| Mode | Behavior |
|------|----------|
| `acceptEdits` | Auto-approve file edits; ask for bash/other tools |
| `dontAsk` | Auto-approve everything (dangerous, use with care) |
| `default` | Ask for every tool use (not headless) |

## Development

```bash
git clone https://github.com/RodrigoSiliunas/hermes-claude-bridge.git
cd hermes-claude-bridge
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

## Releasing

To create a new release:

```bash
# Update version in pyproject.toml and src/hermes_claude_bridge/__init__.py
git add -A
git commit -m "chore(release): bump version to v0.3.0"
git tag v0.3.0
git push origin main --tags
```

The `Release` workflow will automatically build the package and create a GitHub Release with release notes.

## Testing

```bash
pytest tests/ -v
```

## License

MIT.
