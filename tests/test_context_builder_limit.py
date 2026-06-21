"""Tests for history limit in context builder."""

from hermes_claude_bridge.context_builder import build_contextual_prompt
from hermes_claude_bridge.db.models import EventType, SessionEvent


def test_build_contextual_prompt_respects_limit():
    events = [
        SessionEvent(
            id=i,
            session_id="s1",
            event_type=EventType.USER_PROMPT,
            payload={"prompt": f"msg {i}"},
        )
        for i in range(12)
    ]
    prompt = build_contextual_prompt("final", events, max_history_events=5)
    assert "msg 11" in prompt
    assert "msg 7" in prompt
    assert "msg 6" not in prompt
    assert "final" in prompt
