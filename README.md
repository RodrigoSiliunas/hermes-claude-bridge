# Hermes-Claude Bridge

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
|  ClaudeBridgeTool (adapter)      |
|  - JSON schema for Hermes        |
|  - Parameter validation          |
+----------------------------------+
    |
    v
+----------------------------------+
|  HermesClaudeBridge (orchestrator)|
|  - Task queue / batching         |
|  - Health checks                 |
+----------------------------------+
    |
    v
+----------------------------------+
|  ClaudeExecutor (subprocess)     |
|  - claude -p --bare              |
|  - Async subprocess + timeout    |
+----------------------------------+
    |
    v
+----------------------------------+
|  OutputParser                    |
|  - Extract file edits            |
|  - Extract bash commands         |
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

## Testing

```bash
pytest tests/ -v
```

## License

MIT.
