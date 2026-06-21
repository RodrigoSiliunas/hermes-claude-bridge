"""Tests for question detection in output parser."""

from hermes_claude_bridge.parser import OutputParser
from hermes_claude_bridge.schemas import ClaudeResult


def test_detect_question():
    output = "Before I proceed, what is the target Python version for this project?"
    parser = OutputParser()
    question = parser.detect_question(output)
    assert question is not None
    assert "target Python version" in question


def test_no_question():
    output = "I will now create the file as requested. Done."
    parser = OutputParser()
    question = parser.detect_question(output)
    assert question is None


def test_enrich_result_sets_waiting_status():
    result = ClaudeResult(
        task_id="abc",
        success=True,
        stdout="I need to know: should I delete the old file?",
        raw_output="I need to know: should I delete the old file?",
    )
    parser = OutputParser()
    enriched = parser.enrich_result(result)
    assert enriched.status == "waiting_user_input"
    assert enriched.pending_question is not None
