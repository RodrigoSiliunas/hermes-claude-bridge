"""Manage persistent Claude sessions and their events."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from hermes_claude_bridge.db.models import ClaudeSession, EventType, SessionEvent, SessionStatus


class SessionManager:
    """CRUD and event logging for Claude sessions."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._conditions: dict[str, asyncio.Condition] = {}

    def _condition(self, session_id: str) -> asyncio.Condition:
        return self._conditions.setdefault(session_id, asyncio.Condition())

    def _new_session_id(self) -> str:
        return f"sess-{uuid.uuid4().hex[:12]}"

    async def create_session(
        self,
        working_dir: str,
        model: str | None = None,
        permissions_mode: str = "acceptEdits",
        mode: str = "headless",
        metadata: dict | None = None,
    ) -> ClaudeSession:
        session_id = self._new_session_id()
        async with AsyncSession(self.engine) as db:
            cs = ClaudeSession(
                session_id=session_id,
                working_dir=working_dir,
                model=model,
                permissions_mode=permissions_mode,
                mode=mode,
                status=SessionStatus.ACTIVE,
                metadata_json=metadata,
            )
            db.add(cs)
            await db.commit()
            await db.refresh(cs)
            return cs

    async def get_session(self, session_id: str) -> ClaudeSession | None:
        async with AsyncSession(self.engine) as db:
            result = await db.execute(
                select(ClaudeSession).where(ClaudeSession.session_id == session_id)
            )
            return result.scalar_one_or_none()

    async def update_status(
        self,
        session_id: str,
        status: SessionStatus,
        metadata: dict | None = None,
    ) -> None:
        async with AsyncSession(self.engine) as db:
            result = await db.execute(
                select(ClaudeSession).where(ClaudeSession.session_id == session_id)
            )
            cs = result.scalar_one_or_none()
            if cs:
                cs.status = status
                cs.updated_at = datetime.now(UTC)
                if metadata:
                    cs.metadata_json = {**(cs.metadata_json or {}), **metadata}
                await db.commit()

    async def add_event(
        self,
        session_id: str,
        event_type: str | EventType,
        payload: dict | None = None,
    ) -> SessionEvent:
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        async with AsyncSession(self.engine) as db:
            ev = SessionEvent(
                session_id=session_id,
                event_type=event_type,
                payload=payload or {},
            )
            db.add(ev)
            await db.commit()
            await db.refresh(ev)

        cond = self._condition(session_id)
        async with cond:
            cond.notify_all()
        return ev

    async def list_events(
        self,
        session_id: str,
        event_types: list[str] | None = None,
    ) -> list[SessionEvent]:
        async with AsyncSession(self.engine) as db:
            stmt = (
                select(SessionEvent)
                .where(SessionEvent.session_id == session_id)
                .order_by(SessionEvent.created_at)
            )
            if event_types:
                stmt = stmt.where(SessionEvent.event_type.in_(event_types))
            result = await db.execute(stmt)
            return list(result.scalars().all())

    async def listen_events(
        self,
        session_id: str,
        last_id: int = 0,
    ):
        """Async generator that yields new SessionEvents as they are added."""
        cond = self._condition(session_id)
        while True:
            events = await self.list_events(session_id)
            for ev in events:
                if ev.id > last_id:
                    yield ev
                    last_id = ev.id
            async with cond:
                try:
                    await asyncio.wait_for(cond.wait(), timeout=5.0)
                except TimeoutError:
                    continue
