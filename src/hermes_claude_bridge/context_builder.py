"""Build prompts that include session history for persistent context."""

from __future__ import annotations

from hermes_claude_bridge.context_compressor import compress_old_events
from hermes_claude_bridge.db.models import EventType, SessionEvent


def _format_event(event: SessionEvent) -> str:
    if event.event_type == EventType.CHECKPOINT:
        summary = (event.payload or {}).get("summary", "")
        return f"[Context] {summary}"
    if event.event_type == EventType.USER_PROMPT:
        prompt = (event.payload or {}).get("prompt", "")
        return f"User: {prompt}"
    if event.event_type == EventType.CLAUDE_RESPONSE:
        payload = event.payload or {}
        stdout = payload.get("stdout", "")
        return f"Claude: {stdout}"
    if event.event_type == EventType.USER_ANSWER:
        answer = (event.payload or {}).get("answer", "")
        return f"User: {answer}"
    return ""


def build_contextual_prompt(
    current_prompt: str,
    history: list[SessionEvent],
    max_history_events: int = 10,
) -> str:
    """Append relevant session history to the current prompt.

    This gives Claude Code a persistent conversation context without keeping
    a real interactive TUI process alive.
    """
    relevant = [
        ev
        for ev in history
        if ev.event_type
        in {
            EventType.USER_PROMPT,
            EventType.USER_ANSWER,
            EventType.CLAUDE_RESPONSE,
            EventType.CHECKPOINT,
        }
    ]
    if not relevant:
        return current_prompt

    compressed = compress_old_events(relevant, max_history_events)
    history_block = "\n".join(_format_event(ev) for ev in compressed)
    return f"Previous conversation for context:\n{history_block}\n\nNew request:\n{current_prompt}"
