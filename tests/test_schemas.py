"""Tests for hermes_claude_bridge.schemas."""

from hermes_claude_bridge.schemas import BashCommand, ClaudeResult, ClaudeTask, FileEdit


def test_claude_task_creation():
    task = ClaudeTask(prompt="Refactor this function", context_files=["src/main.py"])
    assert task.prompt == "Refactor this function"
    assert task.context_files == ["src/main.py"]
    assert len(task.task_id) > 0


def test_claude_result_success():
    result = ClaudeResult(
        task_id="abc123",
        success=True,
        stdout="Done",
        file_edits=[FileEdit(path="src/main.py", diff="-old\n+new")],
    )
    assert result.success is True
    assert len(result.file_edits) == 1
    assert result.file_edits[0].path == "src/main.py"


def test_bash_command_defaults():
    cmd = BashCommand(command="echo hello")
    assert cmd.command == "echo hello"
    assert cmd.exit_code == 0
    assert cmd.stdout == ""
