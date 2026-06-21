# Hermes-Claude Bridge v2 — Sessions, Events, Model Selection & Human-in-the-Loop

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Evoluir o Hermes-Claude Bridge de um executor fire-and-forget para uma ponte stateful: sessões persistentes, comunicação bidirecional com o Hermes via eventos SSE/WebSocket, seleção de modelo, e pausa quando o Claude precisa de input humano.

**Architecture:** Adicionar uma camada de **Session Manager** (SQLite/Postgres) que persiste metadados de cada sessão Claude, eventos trocados, file edits e comandos. Adicionar um pequeno **Event Server** (FastAPI + SSE/WebSocket) que o Hermes consome para receber atualizações em tempo real. O executor passa a suportar `--model` e a detectar estados de `WAITING_USER_INPUT`. O modo interativo persistente é implementado como opção alternativa ao `-p` headless.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 + Alembic, aiosqlite (SQLite async) ou asyncpg, pydantic, pytest, sse-starlette / websockets.

---

## Reflexão sobre os pontos levantados

| Ponto | Pertinente? | Por quê |
|-------|-------------|----------|
| Comunicação direta com a sessão Hermes | **Sim** | Fire-and-forget não permite ao Hermes reagir a eventos parciais, erros ou pedidos de esclarecimento do Claude. |
| Lidar com perguntas do Claude ao usuário | **Sim** | Mesmo em `-p`, `--permission-mode default` pode abortar pedindo aprovação. Em sessão interativa persistente, o Claude faz perguntas naturais. Precisamos de estado `WAITING_USER_INPUT`. |
| Escolher o modelo | **Sim** | CLI suporta `--model sonnet\|opus\|haiku`. Expor isso aumenta controle de custo/qualidade. |
| Monitorar sessão e persistir metadados | **Sim** | Contexto entre turnos, auditoria, debugging e continuidade. Omni faz isso via banco de eventos; fazemos o mesmo com SQLAlchemy + event store local. |

**Decisão arquitetural:** não replicar a infraestrutura pesada do Omni (NATS JetStream, PostgreSQL cluster). Para o escopo Hermes local, usamos **SQLite async** por padrão (zero ops) com opção de PostgreSQL via env var. Eventos são entregues por **SSE** (mais simples que WebSocket, funciona bem atravás de proxies e é stateless no transporte).

---

## Task 1: Adicionar dependências de banco e servidor

**Objective:** Atualizar `pyproject.toml` com FastAPI, SQLAlchemy, Alembic, aiosqlite, sse-starlette.

**Files:**
- Modify: `pyproject.toml`

**Step 1: Adicionar dependências**

```toml
dependencies = [
    "pydantic>=2.0",
    "aiofiles>=24.0",
    "structlog>=24.0",
    "click>=8.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.13",
    "aiosqlite>=0.20",
    "sse-starlette>=2.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.6",
    "pyyaml>=6.0",
    "httpx>=0.27",
]
postgres = ["asyncpg>=0.29"]
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "build(bridge): add db, server and async sqlite dependencies"
```

---

## Task 2: Modelos de banco (SQLAlchemy) — TDD

**Objective:** Criar tabelas para sessões, eventos e checkpoints.

**Files:**
- Create: `src/hermes_claude_bridge/db/__init__.py`
- Create: `src/hermes_claude_bridge/db/models.py`
- Create: `src/hermes_claude_bridge/db/engine.py`
- Test: `tests/test_db_models.py`

**Step 1: Write failing test**

```python
# tests/test_db_models.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.db.models import ClaudeSession, EventType, SessionEvent


@pytest.mark.asyncio
async def test_create_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    async with AsyncSession(engine) as session:
        cs = ClaudeSession(
            session_id="sess-001",
            working_dir="/tmp",
            model="sonnet",
            status="active",
        )
        session.add(cs)
        await session.commit()
        await session.refresh(cs)
        assert cs.id is not None
        assert cs.model == "sonnet"
```

**Step 2: Run test to verify failure**

Run: `pytest tests/test_db_models.py -v`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```python
# src/hermes_claude_bridge/db/models.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    WAITING_USER_INPUT = "waiting_user_input"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, enum.Enum):
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
    __tablename__ = "claude_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    working_dir: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    permissions_mode: Mapped[str] = mapped_column(String(32), default="acceptEdits")
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SessionEvent(Base):
    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
```

```python
# src/hermes_claude_bridge/db/engine.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from hermes_claude_bridge.db.models import Base


def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Create async SQLAlchemy engine."""
    url = database_url or "sqlite+aiosqlite:///./hermes_claude_bridge.db"
    return create_async_engine(url, echo=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Step 4: Run test to verify pass**

Run: `pytest tests/test_db_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/db/ tests/test_db_models.py
git commit -m "feat(bridge): add session/event database models"
```

---

## Task 3: Session Manager — TDD

**Objective:** Criar serviço que gerencia criação, eventos e recuperação de sessões.

**Files:**
- Create: `src/hermes_claude_bridge/session_manager.py`
- Test: `tests/test_session_manager.py`

**Step 1: Write failing test**

```python
# tests/test_session_manager.py
import pytest

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.session_manager import SessionManager


@pytest.mark.asyncio
async def test_create_and_get_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    manager = SessionManager(engine)
    session = await manager.create_session(
        working_dir="/tmp", model="sonnet", permissions_mode="acceptEdits"
    )
    assert session.model == "sonnet"

    fetched = await manager.get_session(session.session_id)
    assert fetched is not None
    assert fetched.session_id == session.session_id


@pytest.mark.asyncio
async def test_add_event():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    manager = SessionManager(engine)
    session = await manager.create_session(working_dir="/tmp")
    await manager.add_event(
        session.session_id, "user_prompt", {"prompt": "hello"}
    )
    events = await manager.list_events(session.session_id)
    assert len(events) == 1
    assert events[0].event_type.value == "user_prompt"
```

**Step 2: Run test to verify failure**
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/hermes_claude_bridge/session_manager.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from hermes_claude_bridge.db.models import ClaudeSession, EventType, SessionEvent, SessionStatus


class SessionManager:
    """Manage Claude sessions and their events."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    def _new_session_id(self) -> str:
        return f"sess-{uuid.uuid4().hex[:12]}"

    async def create_session(
        self,
        working_dir: str,
        model: str | None = None,
        permissions_mode: str = "acceptEdits",
        metadata: dict | None = None,
    ) -> ClaudeSession:
        session_id = self._new_session_id()
        async with AsyncSession(self.engine) as db:
            cs = ClaudeSession(
                session_id=session_id,
                working_dir=working_dir,
                model=model,
                permissions_mode=permissions_mode,
                status=SessionStatus.ACTIVE,
                metadata=metadata,
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
        self, session_id: str, status: SessionStatus, metadata: dict | None = None
    ) -> None:
        async with AsyncSession(self.engine) as db:
            result = await db.execute(
                select(ClaudeSession).where(ClaudeSession.session_id == session_id)
            )
            cs = result.scalar_one_or_none()
            if cs:
                cs.status = status
                cs.updated_at = datetime.now(timezone.utc)
                if metadata:
                    cs.metadata = {**(cs.metadata or {}), **metadata}
                await db.commit()

    async def add_event(
        self, session_id: str, event_type: str | EventType, payload: dict | None = None
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
            return ev

    async def list_events(
        self, session_id: str, event_types: list[str] | None = None
    ) -> list[SessionEvent]:
        async with AsyncSession(self.engine) as db:
            stmt = select(SessionEvent).where(
                SessionEvent.session_id == session_id
            ).order_by(SessionEvent.created_at)
            if event_types:
                stmt = stmt.where(SessionEvent.event_type.in_(event_types))
            result = await db.execute(stmt)
            return list(result.scalars().all())
```

**Step 4: Run test to verify pass**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/session_manager.py tests/test_session_manager.py
git commit -m "feat(bridge): add SessionManager for persistent sessions and events"
```

---

## Task 4: Seleção de modelo (`--model`) — TDD

**Objective:** Adicionar campo `model` ao `ClaudeTask` e ao executor.

**Files:**
- Modify: `src/hermes_claude_bridge/schemas.py`
- Modify: `src/hermes_claude_bridge/executor.py`
- Modify: `src/hermes_claude_bridge/config.py`
- Test: `tests/test_executor_model.py`

**Step 1: Write failing test**

```python
# tests/test_executor_model.py
from hermes_claude_bridge.executor import ClaudeExecutor
from hermes_claude_bridge.schemas import ClaudeTask


def test_build_args_with_model():
    executor = ClaudeExecutor()
    task = ClaudeTask(prompt="Hello", model="opus", permissions_mode="acceptEdits")
    args = executor._build_args(task)
    assert "--model" in args
    assert "opus" in args


def test_build_args_without_model():
    executor = ClaudeExecutor()
    task = ClaudeTask(prompt="Hello", permissions_mode="acceptEdits")
    args = executor._build_args(task)
    assert "--model" not in args
```

**Step 2: Run test to verify failure**
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/hermes_claude_bridge/schemas.py
class ClaudeTask(BaseModel):
    ...
    model: str | None = Field(default=None, description="Claude model alias or full name")
```

```python
# src/hermes_claude_bridge/executor.py
    def _build_args(self, task: ClaudeTask, bare_mode: bool | None = None) -> list[str]:
        ...
        if task.model:
            args.extend(["--model", task.model])
        ...
```

```python
# src/hermes_claude_bridge/config.py
class BridgeConfig(BaseModel):
    ...
    model: str | None = Field(default=None, description="Default Claude model")
```

**Step 4: Run test to verify pass**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/schemas.py src/hermes_claude_bridge/executor.py src/hermes_claude_bridge/config.py tests/test_executor_model.py
git commit -m "feat(bridge): add model selection via --model"
```

---

## Task 5: Detecção de perguntas / WAITING_USER_INPUT — TDD

**Objective:** Parser deve detectar quando o Claude precisa de input e o bridge deve pausar a sessão.

**Files:**
- Modify: `src/hermes_claude_bridge/parser.py`
- Modify: `src/hermes_claude_bridge/bridge.py`
- Modify: `src/hermes_claude_bridge/schemas.py`
- Test: `tests/test_parser_questions.py`

**Step 1: Write failing test**

```python
# tests/test_parser_questions.py
from hermes_claude_bridge.parser import OutputParser
from hermes_claude_bridge.schemas import ClaudeResult


def test_detect_question():
    output = "Before I proceed, what is the target Python version for this project?"
    parser = OutputParser()
    question = parser.detect_question(output)
    assert question is not None
    assert "target Python version" in question


def test_enrich_result_sets_waiting_status():
    result = ClaudeResult(
        task_id="abc",
        success=True,
        stdout="I need to know: should I delete the old file?",
        raw_output="I need to know: should I delete the old file?",
    )
    parser = OutputParser()
    enriched = parser.enrich_result(result)
    assert enriched.status == "waiting_user_input"
```

**Step 2: Run test to verify failure**
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/hermes_claude_bridge/parser.py
QUESTION_PATTERN = re.compile(
    r"([^.?!]*\?)",
    re.MULTILINE,
)

class OutputParser:
    ...
    def detect_question(self, raw_output: str) -> str | None:
        """Detect if Claude is asking a question to the user."""
        for match in self.QUESTION_PATTERN.finditer(raw_output):
            question = match.group(1).strip()
            if len(question) > 10:
                return question
        return None

    def enrich_result(self, result: ClaudeResult) -> ClaudeResult:
        result.file_edits = self.extract_edits(result.raw_output)
        result.bash_commands = self.extract_bash_commands(result.raw_output)
        question = self.detect_question(result.raw_output)
        if question:
            result.pending_question = question
            result.status = "waiting_user_input"
        return result
```

```python
# src/hermes_claude_bridge/schemas.py
class ClaudeResult(BaseModel):
    ...
    status: Literal[
        "active", "waiting_user_input", "completed", "failed"
    ] = "active"
    pending_question: str | None = None
```

```python
# src/hermes_claude_bridge/bridge.py
async def run_task(self, task: ClaudeTask) -> ClaudeResult:
    ...
    result = await self.executor.execute(task)
    result = self.parser.enrich_result(result)

    if result.status == "waiting_user_input":
        await self.session_manager.update_status(
            task.session_id or result.task_id,
            SessionStatus.WAITING_USER_INPUT,
            metadata={"pending_question": result.pending_question},
        )
    ...
```

**Step 4: Run test to verify pass**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/parser.py src/hermes_claude_bridge/bridge.py src/hermes_claude_bridge/schemas.py tests/test_parser_questions.py
git commit -m "feat(bridge): detect Claude questions and set WAITING_USER_INPUT status"
```

---

## Task 6: Event Server (FastAPI + SSE) — TDD

**Objective:** Criar servidor HTTP que expõe endpoints para criar sessão, enviar prompt, responder perguntas e streamar eventos SSE.

**Files:**
- Create: `src/hermes_claude_bridge/server.py`
- Test: `tests/test_server.py`

**Step 1: Write failing test**

```python
# tests/test_server.py
import pytest
from httpx import ASGITransport, AsyncClient

from hermes_claude_bridge.db.engine import get_engine, init_db
from hermes_claude_bridge.server import create_app


@pytest.mark.asyncio
async def test_health_endpoint():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_create_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/sessions", json={"working_dir": "/tmp", "model": "sonnet"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"].startswith("sess-")
        assert data["model"] == "sonnet"
```

**Step 2: Run test to verify failure**
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/hermes_claude_bridge/server.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine
from sse_starlette.sse import EventSourceResponse

from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.db.engine import get_engine, init_db
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
            "created_at": session.created_at.isoformat(),
        }

    @app.post("/sessions/{session_id}/prompt")
    async def send_prompt(session_id: str, req: PromptRequest):
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await session_manager.add_event(
            session_id, "user_prompt", {"prompt": req.prompt}
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

        await session_manager.add_event(
            session_id,
            "claude_response" if result.success else "error",
            result.model_dump(),
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
                    seen = ev.id
                # In production, use asyncio.sleep or notification mechanism
                import asyncio
                await asyncio.sleep(1)

        return EventSourceResponse(event_generator())

    @app.post("/sessions/{session_id}/answer")
    async def answer_question(session_id: str, req: AnswerRequest):
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await session_manager.add_event(
            session_id, "user_answer", {"answer": req.answer}
        )
        await session_manager.update_status(session_id, "active")

        # Re-run Claude with the answer as context
        task = ClaudeTask(
            prompt=f"User answered: {req.answer}",
            working_dir=session.working_dir,
            timeout_seconds=300,
            permissions_mode=session.permissions_mode,  # type: ignore[arg-type]
            model=session.model,
        )
        result = await bridge.run_task(task)
        return result.model_dump()

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("hermes_claude_bridge.server:create_app", factory=True, host="0.0.0.0", port=8765)
```

**Step 4: Run test to verify pass**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/server.py tests/test_server.py
git commit -m "feat(bridge): add FastAPI event server with SSE streaming"
```

---

## Task 7: Integração Hermes via cliente SSE

**Objective:** Criar cliente Python que o Hermes usa para falar com o bridge server e receber eventos.

**Files:**
- Create: `src/hermes_claude_bridge/client.py`
- Test: `tests/test_client.py`

**Step 1: Write failing test**

```python
# tests/test_client.py
import pytest

from hermes_claude_bridge.client import BridgeClient


def test_client_builds_url():
    client = BridgeClient(base_url="http://localhost:8765")
    assert client.base_url == "http://localhost:8765"
```

**Step 2: Run test to verify failure**
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/hermes_claude_bridge/client.py
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Callable

import httpx
import structlog

logger = structlog.get_logger(__name__)


class BridgeClient:
    """Client for Hermes to talk to the Hermes-Claude Bridge server."""

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=60)

    async def health(self) -> dict:
        resp = await self._http.get("/health")
        resp.raise_for_status()
        return resp.json()

    async def create_session(
        self, working_dir: str, model: str | None = None, permissions_mode: str = "acceptEdits"
    ) -> dict:
        resp = await self._http.post(
            "/sessions",
            json={
                "working_dir": working_dir,
                "model": model,
                "permissions_mode": permissions_mode,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def send_prompt(
        self, session_id: str, prompt: str, context_files: list[str] | None = None
    ) -> dict:
        resp = await self._http.post(
            f"/sessions/{session_id}/prompt",
            json={
                "prompt": prompt,
                "context_files": context_files or [],
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def answer_question(self, session_id: str, answer: str) -> dict:
        resp = await self._http.post(
            f"/sessions/{session_id}/answer",
            json={"answer": answer},
        )
        resp.raise_for_status()
        return resp.json()

    async def stream_events(
        self, session_id: str
    ) -> AsyncGenerator[dict, None]:
        """Stream SSE events from a session."""
        import sseclient  # optional dependency
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET", f"{self.base_url}/sessions/{session_id}/events"
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        yield {"data": data}

    async def close(self) -> None:
        await self._http.aclose()
```

**Step 4: Run test to verify pass**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/client.py tests/test_client.py
git commit -m "feat(bridge): add Hermes client for bridge server"
```

---

## Task 8: CLI do servidor e lifecycle

**Objective:** Adicionar comando `hermes-claude server` para iniciar o bridge server.

**Files:**
- Modify: `src/hermes_claude_bridge/cli.py`
- Test: `tests/test_cli_server.py`

**Step 1: Write failing test**

```python
# tests/test_cli_server.py
from click.testing import CliRunner
from hermes_claude_bridge.cli import cli


def test_server_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["server", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.output
```

**Step 2: Run test to verify failure**
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/hermes_claude_bridge/cli.py
# add subcommand
import uvicorn

@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8765, help="Server port")
@click.option("--database-url", default=None, help="Database URL")
def server(host: str, port: int, database_url: str | None) -> None:
    """Start the Hermes-Claude Bridge event server."""
    import os
    if database_url:
        os.environ["DATABASE_URL"] = database_url
    uvicorn.run(
        "hermes_claude_bridge.server:create_app",
        factory=True,
        host=host,
        port=port,
    )
```

**Step 4: Run test to verify pass**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/cli.py tests/test_cli_server.py
git commit -m "feat(bridge): add hermes-claude server CLI command"
```

---

## Task 9: Atualizar skill Hermes e README

**Objective:** Documentar o novo modo stateful/server e como o Hermes deve consumir eventos.

**Files:**
- Modify: `.skills/hermes-claude-bridge/SKILL.md`
- Modify: `README.md`
- Test: `tests/test_skill.py` (já existe, verificar)

**Step 1: Atualizar SKILL.md**

Adicionar seções:
- "Stateful mode with Bridge Server"
- "Handling Claude questions"
- "Model selection"
- Exemplo de loop de eventos SSE

**Step 2: Atualizar README**

Adicionar:
- Arquitetura v2 (sessões + eventos)
- Comando `hermes-claude server`
- Exemplo de cliente Python

**Step 3: Commit**

```bash
git add .skills/hermes-claude-bridge/SKILL.md README.md
git commit -m "docs(bridge): document v2 sessions, events, model selection and server mode"
```

---

## Task 10: Lint, testes E2E e release v0.2.0

**Objective:** Garantir qualidade e lançar v0.2.0.

**Step 1: Rodar lint e testes**

```bash
ruff check src/ tests/ examples/
ruff format src/ tests/ examples/
pytest tests/ -v --ignore=tests/test_e2e.py
```

Expected: all pass

**Step 2: Rodar E2E server**

```bash
hermes-claude server &
pytest tests/test_e2e_server.py -v  # novo teste opcional
```

**Step 3: Bump version**

- Update `pyproject.toml` version to `0.2.0`
- Update `src/hermes_claude_bridge/__init__.py` version

**Step 4: Commit e tag**

```bash
git add -A
git commit -m "chore(release): bump version to v0.2.0"
git tag v0.2.0
git push origin main --tags
```

Expected: GitHub Actions roda CI e cria Release v0.2.0.

---

## Risks, Tradeoffs e Open Questions

| Risk | Severity | Mitigation |
|------|----------|------------|
| SSE polling a cada 1s não escala | Medium | Trocar por notificação via asyncio.Condition ou PostgreSQL LISTEN/NOTIFY no futuro. |
| Detecção de pergunta por regex é frágil | Medium | Refinar heurísticas; no futuro usar LLM judge ou structured output do Claude. |
| Modo interativo persistente não é trivial com subprocess | High | Fase 2: usar PTY + thread de leitura contínua, ou integrar com Agent SDK Python/TS. |
| SQLite não escala para muitas sessões concorrentes | Low | Configuração já prevê PostgreSQL via `DATABASE_URL`. |

**Tradeoffs:**
- SSE vs WebSocket: SSE é mais simples e funciona atravás de proxies; Hermes precisa apenas consumir.
- SQLite vs Postgres: SQLite é zero-config para usuários individuais; Postgres para produção/escala.
- Headless `-p` vs sessão interativa persistente: `-p` é mais simples e seguro; sessão interativa permite diálogo natural com perguntas, mas é mais complexa.

**Open Questions:**
1. Devemos usar `claude agents` (subagentes do próprio Claude) como backend para sessões persistentes?
2. O Hermes deve receber eventos via SSE diretamente ou via webhook callback?
3. Precisamos de compactação de histórico para sessões longas?

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Modify | Novas dependências |
| `src/hermes_claude_bridge/db/models.py` | Create | Tabelas sessions/events |
| `src/hermes_claude_bridge/db/engine.py` | Create | Engine SQLAlchemy async |
| `src/hermes_claude_bridge/session_manager.py` | Create | CRUD de sessões e eventos |
| `src/hermes_claude_bridge/executor.py` | Modify | Suporte a `--model` |
| `src/hermes_claude_bridge/schemas.py` | Modify | `model`, `status`, `pending_question` |
| `src/hermes_claude_bridge/parser.py` | Modify | Detecção de perguntas |
| `src/hermes_claude_bridge/bridge.py` | Modify | Integração com session_manager e status |
| `src/hermes_claude_bridge/server.py` | Create | FastAPI + SSE |
| `src/hermes_claude_bridge/client.py` | Create | Cliente Hermes |
| `src/hermes_claude_bridge/cli.py` | Modify | Comando `server` |
| `.skills/hermes-claude-bridge/SKILL.md` | Modify | Documentação v2 |
| `README.md` | Modify | Documentação v2 |
| `tests/test_*.py` | Create | TDD para cada módulo |

---

*Plan created: 2026-06-21. Ready for execution via subagent-driven-development.*
