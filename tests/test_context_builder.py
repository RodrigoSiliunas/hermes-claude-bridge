"""Tests for hermes_claude_bridge.context_builder."""

import pytest

from hermes_claude_bridge.context_builder import build_contextual_prompt
from hermes_claude_bridge.db.models import EventType, SessionEvent


def test_build_contextual_prompt_empty_history():
    prompt = build_contextual_prompt("do X", [])
    assert "do X" in prompt
    assert "Previous conversation" not in prompt


def test_build_contextual_prompt_with_history():
    events = [
        SessionEvent(id=1, session_id="s1", event_type=EventType.USER_PROMPT, payload={"prompt": "hello"}),
        SessionEvent(
            id=2,
            session_id="s1",
            event_type=EventType.CLAUDE_RESPONSE,
            payload={"stdout": "Hi there"},
        ),
    ]
    prompt = build_contextual_prompt("do X", events)
    assert "hello" in prompt
    assert "Hi there" in prompt
    assert "do X" in prompt
