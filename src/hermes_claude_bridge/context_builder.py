"""Build prompts that include session history for persistent context."""

from __future__ import annotations

from hermes_claude_bridge.db.models import EventType, SessionEvent


def _format_event(event: SessionEvent) -> str:
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


def build_contextual_prompt(current_prompt: str, history: list[SessionEvent]) -> str:
    """Append relevant session history to the current prompt.

    This gives Claude Code a persistent conversation context without keeping
    a real interactive TUI process alive.
    """
    relevant = [
        _format_event(ev)
        for ev in history
        if ev.event_type in {EventType.USER_PROMPT, EventType.USER_ANSWER, EventType.CLAUDE_RESPONSE}
    ]
    if not relevant:
        return current_prompt

    history_block = "\n".join(relevant)
    return (
        "Previous conversation for context:\n"
        f"{history_block}\n\n"
        f"New request:\n{current_prompt}"
    )
