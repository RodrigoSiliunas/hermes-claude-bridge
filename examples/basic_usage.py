"""Basic usage example of Hermes-Claude Bridge."""

import asyncio

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.schemas import ClaudeTask


async def main() -> None:
    """Run a simple task through the bridge."""
    bridge = HermesClaudeBridge()

    # Check health
    health = await bridge.health()
    print("Health:", health)

    # Run a task
    task = ClaudeTask(
        prompt="List all Python files in the current directory",
        permissions_mode="acceptEdits",
    )
    result = await bridge.run_task(task)
    print("Result:", result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
