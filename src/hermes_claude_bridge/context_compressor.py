"""Compress old session events into a compact summary."""

from __future__ import annotations

from hermes_claude_bridge.db.models import EventType, SessionEvent


def compress_old_events(
    events: list[SessionEvent],
    limit: int,
) -> list[SessionEvent]:
    """Return the most recent `limit` events, prepending a summary of older ones.

    The summary is represented as a synthetic SYSTEM event so callers can format
    it consistently with the rest of the event stream.
    """
    if len(events) <= limit:
        return events

    kept = events[-limit:]
    omitted = len(events) - limit
    summary = SessionEvent(
        id=-1,
        session_id=events[0].session_id if events else "",
        event_type=EventType.CHECKPOINT,
        payload={"summary": f"{omitted} earlier messages omitted."},
    )
    return [summary] + kept
