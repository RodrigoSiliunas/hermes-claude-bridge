"""Tests for Hermes skill packaging."""

from pathlib import Path

import yaml


def test_skill_metadata():
    """Verify SKILL.md has valid YAML frontmatter."""
    skill_path = Path(".skills/hermes-claude-bridge/SKILL.md")
    assert skill_path.exists(), "SKILL.md not found"

    content = skill_path.read_text()
    assert content.startswith("---")

    # Extract frontmatter
    _, frontmatter, body = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)

    assert metadata["name"] == "hermes-claude-bridge"
    assert "claude_code_delegate" in body
    assert "Hermes-Claude Bridge" in body
