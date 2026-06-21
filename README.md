# Hermes-Claude Bridge

Delegate development tasks from [Hermes Agent](https://hermes-agent.nousresearch.com/) to [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview) — zero additional Anthropic API cost.

> **Status:** early development. API may change until v1.0.0.

## Why?

- You already pay for Claude Code (Pro / Team / Enterprise) — reuse that subscription.
- Hermes handles orchestration, memory, and multi-tool workflows.
- Claude Code handles deep, multi-file coding tasks.
- No Anthropic API tokens are consumed for delegated work.

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
hermes-claude health
hermes-claude run "Refactor auth.py to use dependency injection" -f src/auth.py
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

## License

MIT.
