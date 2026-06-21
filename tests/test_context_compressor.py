"""Tests for context compression."""

from hermes_claude_bridge.context_builder import build_contextual_prompt
from hermes_claude_bridge.db.models import EventType, SessionEvent


def test_compress_old_events():
    events = [
        SessionEvent(
            id=i,
            session_id="s1",
            event_type=EventType.USER_PROMPT,
            payload={"prompt": f"msg {i}"},
        )
        for i in range(15)
    ]
    prompt = build_contextual_prompt("final", events, max_history_events=5)
    assert "10 earlier messages omitted" in prompt
    assert "msg 14" in prompt
    assert "msg 4" not in prompt
    assert "final" in prompt
