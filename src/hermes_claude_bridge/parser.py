"""Parse Claude Code CLI output into structured actions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from hermes_claude_bridge.schemas import BashCommand, FileEdit

if TYPE_CHECKING:
    from hermes_claude_bridge.schemas import ClaudeResult


class OutputParser:
    """Parse Claude Code CLI output to extract structured actions."""

    # Patterns for Claude Code output
    EDIT_PATTERN = re.compile(
        r"[\u2713\u2705]\s*Edited\s+(?P<path>\S+).*?(?P<diff>```diff\n.*?```)",
        re.DOTALL | re.IGNORECASE,
    )
    BASH_PATTERN = re.compile(
        r"\$\s+(?P<cmd>.+?)(?:\n|$)",
        re.MULTILINE,
    )
    FILE_CREATE_PATTERN = re.compile(
        r"[\u2713\u2705]\s*Created\s+(?P<path>\S+)",
        re.IGNORECASE,
    )

    QUESTION_PATTERN = re.compile(r"([^.?!]*\?)", re.MULTILINE)

    def extract_edits(self, raw_output: str) -> list[FileEdit]:
        """Extract file edits from Claude output."""
        edits: list[FileEdit] = []

        for match in self.EDIT_PATTERN.finditer(raw_output):
            path = match.group("path").strip()
            diff_block = match.group("diff")
            # Strip markdown fences
            diff_lines = diff_block.splitlines()
            diff_clean = "\n".join(line for line in diff_lines if not line.startswith("```"))
            edits.append(FileEdit(path=path, diff=diff_clean, operation="edit"))

        # Also detect creations
        for match in self.FILE_CREATE_PATTERN.finditer(raw_output):
            path = match.group("path").strip()
            # Check if not already captured
            if not any(e.path == path for e in edits):
                edits.append(FileEdit(path=path, operation="create"))

        return edits

    def extract_bash_commands(self, raw_output: str) -> list[BashCommand]:
        """Extract bash commands from Claude output."""
        cmds: list[BashCommand] = []
        for match in self.BASH_PATTERN.finditer(raw_output):
            cmd = match.group("cmd").strip()
            if cmd and not cmd.startswith("claude"):
                cmds.append(BashCommand(command=cmd))
        return cmds

    def detect_question(self, raw_output: str) -> str | None:
        """Detect if Claude is asking the user a question.

        Heuristic: find the first sentence ending in '?' that is long enough
        to be a substantive question.
        """
        for match in self.QUESTION_PATTERN.finditer(raw_output):
            question = match.group(1).strip()
            if len(question) >= 10:
                return question
        return None

    def enrich_result(self, result: ClaudeResult) -> ClaudeResult:
        """Parse raw_output and populate structured fields."""
        result.file_edits = self.extract_edits(result.raw_output)
        result.bash_commands = self.extract_bash_commands(result.raw_output)
        question = self.detect_question(result.raw_output)
        if question:
            result.pending_question = question
            result.status = "waiting_user_input"
        return result
