"""Example of using the bridge inside a Hermes skill or agent.

This shows how a Hermes agent can delegate complex tasks to Claude Code
without paying additional Anthropic API costs.
"""

from hermes_claude_bridge.hermes_adapter import ClaudeBridgeTool


async def handle_complex_refactoring(file_path: str, instructions: str) -> dict:
    """Hermes skill handler that delegates to Claude Code.

    Args:
        file_path: Path to the file to refactor.
        instructions: Natural language instructions for the refactor.

    Returns:
        Structured result from Claude Code CLI.
    """
    tool = ClaudeBridgeTool()

    result = await tool.invoke(
        {
            "prompt": f"Refactor {file_path}: {instructions}",
            "context_files": [file_path],
            "permission_mode": "acceptEdits",
            "timeout": 300,
        }
    )

    if result["success"]:
        print(f"Claude completed task {result['task_id']} in {result['duration_seconds']:.1f}s")
        for edit in result["file_edits"]:
            print(f"  - {edit['operation']}: {edit['path']}")
    else:
        print(f"Task failed: {result['error']}")

    return result
