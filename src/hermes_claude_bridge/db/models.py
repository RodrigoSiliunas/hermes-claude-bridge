"""SQLAlchemy models for session persistence and event store."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SessionStatus(enum.StrEnum):
    ACTIVE = "active"
    WAITING_USER_INPUT = "waiting_user_input"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(enum.StrEnum):
    USER_PROMPT = "user_prompt"
    CLAUDE_RESPONSE = "claude_response"
    TOOL_CALL = "tool_call"
    FILE_EDIT = "file_edit"
    BASH_COMMAND = "bash_command"
    QUESTION = "question"
    USER_ANSWER = "user_answer"
    ERROR = "error"
    CHECKPOINT = "checkpoint"


class ClaudeSession(Base):
    """A persistent Claude Code session."""

    __tablename__ = "claude_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    working_dir: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    permissions_mode: Mapped[str] = mapped_column(String(32), default="acceptEdits")
    mode: Mapped[str] = mapped_column(String(16), default="headless")
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SessionEvent(Base):
    """An event within a Claude session."""

    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
