"""FastAPI event server for Hermes-Claude Bridge."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine
from sse_starlette.sse import EventSourceResponse

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.context_builder import build_contextual_prompt
from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.db.models import SessionStatus
from hermes_claude_bridge.interactive_executor import InteractiveExecutor
from hermes_claude_bridge.schemas import ClaudeTask
from hermes_claude_bridge.session_manager import SessionManager


class CreateSessionRequest(BaseModel):
    working_dir: str
    model: str | None = None
    permissions_mode: str = "acceptEdits"
    mode: str = "headless"
    max_history_events: int = 10


class PromptRequest(BaseModel):
    prompt: str
    context_files: list[str] = []
    timeout: int = 300


class AnswerRequest(BaseModel):
    answer: str


def _default_get_interactive_executor(session_id: str, working_dir: str) -> InteractiveExecutor:
    """Factory for real interactive Claude executors."""
    return InteractiveExecutor("claude")


def create_app(
    engine: AsyncEngine | None = None,
    get_interactive_executor=None,
) -> FastAPI:
    """Create the FastAPI application."""
    engine = engine or get_engine()
    session_manager = SessionManager(engine)
    bridge = HermesClaudeBridge()
    bridge.executor.bare_mode = False
    get_interactive_executor = get_interactive_executor or _default_get_interactive_executor

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db(engine)
        yield

    app = FastAPI(title="Hermes-Claude Bridge", lifespan=lifespan)
    app.state.session_manager = session_manager
    app.state.bridge = bridge
    app.state.interactive_executors: dict[str, InteractiveExecutor] = {}
    app.state.get_interactive_executor = get_interactive_executor

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/sessions", status_code=201)
    async def create_session(req: CreateSessionRequest):
        session = await session_manager.create_session(
            working_dir=req.working_dir,
            model=req.model,
            permissions_mode=req.permissions_mode,
            mode=req.mode,
            max_history_events=req.max_history_events,
        )
        return {
            "session_id": session.session_id,
            "status": session.status.value,
            "model": session.model,
            "permissions_mode": session.permissions_mode,
            "mode": session.mode,
            "max_history_events": session.max_history_events,
        }

    @app.get("/sessions")
    async def list_sessions():
        sessions = await session_manager.list_sessions()
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "status": s.status.value,
                    "model": s.model,
                    "permissions_mode": s.permissions_mode,
                    "mode": s.mode,
                    "working_dir": s.working_dir,
                    "max_history_events": s.max_history_events,
                }
                for s in sessions
            ]
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
            "mode": session.mode,
            "max_history_events": session.max_history_events,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    async def _run_headless(session, req: PromptRequest):
        task = ClaudeTask(
            prompt=req.prompt,
            context_files=req.context_files,
            working_dir=session.working_dir,
            timeout_seconds=req.timeout,
            permissions_mode=session.permissions_mode,  # type: ignore[arg-type]
            model=session.model,
        )
        return await bridge.run_task(task)

    async def _run_interactive(session_id: str, session, req: PromptRequest):
        """Run a prompt while preserving session history.

        We keep a logical interactive session by replaying prior prompts and
        answers in the prompt context, rather than trying to keep the Claude
        Code TUI process alive (which is fragile without a real terminal).
        """
        history = await session_manager.list_events(session_id)
        contextual_prompt = build_contextual_prompt(req.prompt, history)

        task = ClaudeTask(
            prompt=contextual_prompt,
            context_files=req.context_files,
            working_dir=session.working_dir,
            timeout_seconds=req.timeout,
            permissions_mode=session.permissions_mode,  # type: ignore[arg-type]
            model=session.model,
        )
        result = await bridge.run_task(task)
        return result

    @app.post("/sessions/{session_id}/prompt")
    async def send_prompt(session_id: str, req: PromptRequest):
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await session_manager.add_event(
            session_id, "user_prompt", {"prompt": req.prompt, "context_files": req.context_files}
        )

        if session.mode == "interactive":
            result = await _run_interactive(session_id, session, req)
        else:
            result = await _run_headless(session, req)

        event_type = "error" if not result.success else "claude_response"
        await session_manager.add_event(session_id, event_type, result.model_dump())

        if result.status == "waiting_user_input":
            await session_manager.update_status(
                session_id,
                SessionStatus.WAITING_USER_INPUT,
                metadata={"pending_question": result.pending_question},
            )

        response = result.model_dump()
        response["session_id"] = session_id
        return response

    @app.post("/sessions/{session_id}/answer")
    async def answer_question(session_id: str, req: AnswerRequest):
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await session_manager.add_event(session_id, "user_answer", {"answer": req.answer})
        await session_manager.update_status(session_id, SessionStatus.ACTIVE)

        if session.mode == "interactive":
            history = await session_manager.list_events(session_id)
            contextual_prompt = build_contextual_prompt(f"The user answered: {req.answer}", history)
            task = ClaudeTask(
                prompt=contextual_prompt,
                working_dir=session.working_dir,
                timeout_seconds=300,
                permissions_mode=session.permissions_mode,  # type: ignore[arg-type]
                model=session.model,
            )
            result = await bridge.run_task(task)
        else:
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
            async for ev in session_manager.listen_events(session_id):
                yield {
                    "event": ev.event_type.value,
                    "data": {
                        "id": ev.id,
                        "payload": ev.payload,
                        "created_at": ev.created_at.isoformat(),
                    },
                }

        return EventSourceResponse(event_generator())

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "hermes_claude_bridge.server:create_app",
        factory=True,
        host="0.0.0.0",
        port=8765,
    )
