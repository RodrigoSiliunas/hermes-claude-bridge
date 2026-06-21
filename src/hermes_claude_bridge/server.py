"""FastAPI event server for Hermes-Claude Bridge."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine
from sse_starlette.sse import EventSourceResponse

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.db.models import SessionStatus
from hermes_claude_bridge.schemas import ClaudeTask
from hermes_claude_bridge.session_manager import SessionManager


class CreateSessionRequest(BaseModel):
    working_dir: str
    model: str | None = None
    permissions_mode: str = "acceptEdits"


class PromptRequest(BaseModel):
    prompt: str
    context_files: list[str] = []
    timeout: int = 300


class AnswerRequest(BaseModel):
    answer: str


def create_app(engine: AsyncEngine | None = None) -> FastAPI:
    """Create the FastAPI application."""
    engine = engine or get_engine()
    session_manager = SessionManager(engine)
    bridge = HermesClaudeBridge()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db(engine)
        yield

    app = FastAPI(title="Hermes-Claude Bridge", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/sessions", status_code=201)
    async def create_session(req: CreateSessionRequest):
        session = await session_manager.create_session(
            working_dir=req.working_dir,
            model=req.model,
            permissions_mode=req.permissions_mode,
        )
        return {
            "session_id": session.session_id,
            "status": session.status.value,
            "model": session.model,
            "permissions_mode": session.permissions_mode,
        }

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": session.session_id,
            "status": session.status.value,
            "model": session.model,
            "permissions_mode": session.permissions_mode,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    @app.post("/sessions/{session_id}/prompt")
    async def send_prompt(session_id: str, req: PromptRequest):
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await session_manager.add_event(
            session_id, "user_prompt", {"prompt": req.prompt, "context_files": req.context_files}
        )

        task = ClaudeTask(
            prompt=req.prompt,
            context_files=req.context_files,
            working_dir=session.working_dir,
            timeout_seconds=req.timeout,
            permissions_mode=session.permissions_mode,  # type: ignore[arg-type]
            model=session.model,
        )
        result = await bridge.run_task(task)

        event_type = "error" if not result.success else "claude_response"
        await session_manager.add_event(session_id, event_type, result.model_dump())

        if result.status == "waiting_user_input":
            await session_manager.update_status(
                session_id,
                SessionStatus.WAITING_USER_INPUT,
                metadata={"pending_question": result.pending_question},
            )

        return result.model_dump()

    @app.post("/sessions/{session_id}/answer")
    async def answer_question(session_id: str, req: AnswerRequest):
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await session_manager.add_event(session_id, "user_answer", {"answer": req.answer})
        await session_manager.update_status(session_id, SessionStatus.ACTIVE)

        task = ClaudeTask(
            prompt=f"The user answered: {req.answer}",
            working_dir=session.working_dir,
            timeout_seconds=300,
            permissions_mode=session.permissions_mode,  # type: ignore[arg-type]
            model=session.model,
        )
        result = await bridge.run_task(task)

        event_type = "error" if not result.success else "claude_response"
        await session_manager.add_event(session_id, event_type, result.model_dump())

        if result.status == "waiting_user_input":
            await session_manager.update_status(
                session_id,
                SessionStatus.WAITING_USER_INPUT,
                metadata={"pending_question": result.pending_question},
            )

        return result.model_dump()

    @app.get("/sessions/{session_id}/events")
    async def stream_events(session_id: str):
        async def event_generator() -> AsyncGenerator[dict, None]:
            seen = 0
            while True:
                events = await session_manager.list_events(session_id)
                for ev in events[seen:]:
                    yield {
                        "event": ev.event_type.value,
                        "data": {
                            "id": ev.id,
                            "payload": ev.payload,
                            "created_at": ev.created_at.isoformat(),
                        },
                    }
                    seen = max(seen, ev.id)
                await asyncio.sleep(1)

        return EventSourceResponse(event_generator())

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "hermes_claude_bridge.server:create_app",
        factory=True,
        host="0.0.0.0",
        port=8765,
    )
