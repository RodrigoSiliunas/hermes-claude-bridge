# Hermes-Claude Bridge v0.4.0 — History Filter, Context Compression & MCP Server

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Tornar as sessões contextuais escaláveis e expor a bridge como tool MCP nativa para o ecossistema Hermes.

**Architecture:** Adicionar `max_history_events` ao modelo de sessão, implementar compressão de histórico via janela deslizante + resumo, e criar um servidor MCP usando `mcp.server.fastmcp` que expõe `claude_code_delegate` via stdio/SSE.

**Tech Stack:** Python 3.10+, FastMCP (`mcp>=1.27,<2`), Pydantic, SQLAlchemy, pytest.

---

## Task 1: Adicionar `max_history_events` ao modelo de sessão

**Objective:** Permitir que cada sessão limite quantos eventos são incluídos no contexto.

**Files:**
- Modify: `src/hermes_claude_bridge/db/models.py`
- Modify: `src/hermes_claude_bridge/session_manager.py`
- Modify: `src/hermes_claude_bridge/schemas.py` (se necessário)
- Modify: `src/hermes_claude_bridge/server.py`
- Test: `tests/test_session_history_limit.py`

**Step 1: Write failing test**

```python
def test_session_has_default_history_limit():
    from hermes_claude_bridge.db.models import ClaudeSession
    session = ClaudeSession(working_dir="/tmp")
    assert session.max_history_events == 10
```

**Step 2: Run test to verify failure**

Run: `pytest tests/test_session_history_limit.py -v`
Expected: FAIL — `max_history_events` does not exist

**Step 3: Write minimal implementation**

Add `max_history_events: Mapped[int] = mapped_column(default=10)` to `ClaudeSession`.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_session_history_limit.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_session_history_limit.py src/hermes_claude_bridge/db/models.py
git commit -m "feat(bridge): add max_history_events to session model with TDD"
```

---

## Task 2: Propagar `max_history_events` na criação de sessão

**Objective:** O usuário pode definir o limite ao criar uma sessão.

**Files:**
- Modify: `src/hermes_claude_bridge/session_manager.py:27`
- Modify: `src/hermes_claude_bridge/server.py`
- Test: `tests/test_server_history_limit.py`

**Step 1: Write failing test**

```python
async def test_create_session_with_history_limit():
    session = await session_manager.create_session(
        working_dir="/tmp",
        max_history_events=5,
    )
    assert session.max_history_events == 5
```

**Step 2: Run test**
Expected: FAIL — parameter not accepted

**Step 3: Implement**

Add `max_history_events: int = 10` ao `create_session`.

**Step 4: Run test**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/session_manager.py tests/test_server_history_limit.py
git commit -m "feat(bridge): allow configuring max_history_events on session creation with TDD"
```

---

## Task 3: `ContextBuilder` respeita `max_history_events`

**Objective:** Apenas os últimos N eventos relevantes entram no prompt.

**Files:**
- Modify: `src/hermes_claude_bridge/context_builder.py`
- Test: `tests/test_context_builder_limit.py`

**Step 1: Write failing test**

```python
def test_build_contextual_prompt_respects_limit():
    events = [
        SessionEvent(id=i, session_id="s1", event_type=EventType.USER_PROMPT, payload={"prompt": f"msg {i}"})
        for i in range(12)
    ]
    prompt = build_contextual_prompt("final", events, max_history_events=5)
    assert "msg 11" in prompt
    assert "msg 6" in prompt
    assert "msg 5" not in prompt
```

**Step 2: Run test**
Expected: FAIL — all messages included

**Step 3: Implement**

```python
def build_contextual_prompt(current_prompt, history, max_history_events=10):
    relevant = [...]
    limited = relevant[-max_history_events:]
    ...
```

**Step 4: Run test**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/context_builder.py tests/test_context_builder_limit.py
git commit -m "feat(bridge): respect max_history_events in context builder with TDD"
```

---

## Task 4: Compressão de histórico por janela deslizante

**Objective:** Quando o histórico excede o limite, eventos antigos são resumidos em uma única linha informativa.

**Files:**
- Create: `src/hermes_claude_bridge/context_compressor.py`
- Modify: `src/hermes_claude_bridge/context_builder.py`
- Test: `tests/test_context_compressor.py`

**Step 1: Write failing test**

```python
def test_compress_old_events():
    events = [SessionEvent(id=i, session_id="s1", event_type=EventType.USER_PROMPT, payload={"prompt": f"msg {i}"}) for i in range(15)]
    prompt = build_contextual_prompt("final", events, max_history_events=5)
    assert "5 earlier messages omitted" in prompt
    assert "msg 14" in prompt
```

**Step 2: Run test**
Expected: FAIL — no compression

**Step 3: Implement**

Create `context_compressor.py`:

```python
def compress_old_events(events, limit):
    if len(events) <= limit:
        return events
    kept = events[-limit:]
    omitted = len(events) - limit
    summary = SessionEvent(
        id=-1,
        session_id=events[0].session_id,
        event_type=EventType.SYSTEM,
        payload={"summary": f"{omitted} earlier messages omitted."},
    )
    return [summary] + kept
```

Use em `build_contextual_prompt`.

**Step 4: Run test**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/context_compressor.py src/hermes_claude_bridge/context_builder.py tests/test_context_compressor.py
git commit -m "feat(bridge): add context compression for old events with TDD"
```

---

## Task 5: Adicionar dependência do MCP SDK

**Objective:** Ter o pacote `mcp` instalado.

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dependency**

```toml
dependencies = [
    ...,
    "mcp>=1.27,<2",
]
```

**Step 2: Install**

Run: `pip install -e ".[dev]"`

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(bridge): add mcp sdk dependency"
```

---

## Task 6: Criar servidor MCP com tool `claude_code_delegate`

**Objective:** Expor a bridge como um servidor MCP.

**Files:**
- Create: `src/hermes_claude_bridge/mcp_server.py`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_mcp_server_has_claude_code_delegate_tool():
    from hermes_claude_bridge.mcp_server import create_mcp_server
    server = create_mcp_server()
    tools = await server.get_tools()
    assert any(t.name == "claude_code_delegate" for t in tools)
```

**Step 2: Run test**
Expected: FAIL — module/tool missing

**Step 3: Implement**

```python
from mcp.server.fastmcp import FastMCP
from hermes_claude_bridge.bridge import HermesClaudeBridge
from hermes_claude_bridge.schemas import ClaudeTask

mcp = FastMCP("hermes-claude-bridge", json_response=True)

@mcp.tool()
async def claude_code_delegate(
    prompt: str,
    context_files: list[str] | None = None,
    working_dir: str = ".",
    model: str | None = None,
    permission_mode: str = "acceptEdits",
    timeout: int = 300,
) -> dict:
    """Delegate a coding task to Claude Code CLI."""
    bridge = HermesClaudeBridge()
    result = await bridge.run_task(ClaudeTask(...))
    return result.model_dump()
```

**Step 4: Run test**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/mcp_server.py tests/test_mcp_server.py
git commit -m "feat(bridge): add MCP server exposing claude_code_delegate with TDD"
```

---

## Task 7: CLI para iniciar servidor MCP

**Objective:** Permitir `hermes-claude mcp-server`.

**Files:**
- Modify: `src/hermes_claude_bridge/cli.py`
- Test: `tests/test_cli_mcp_server.py`

**Step 1: Write failing test**

```python
def test_mcp_server_cli_exists():
    from click.testing import CliRunner
    from hermes_claude_bridge.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["mcp-server", "--help"])
    assert result.exit_code == 0
```

**Step 2: Run test**
Expected: FAIL — command missing

**Step 3: Implement**

```python
@cli.command()
@click.option("--transport", default="stdio")
def mcp_server(transport):
    from hermes_claude_bridge.mcp_server import mcp
    mcp.run(transport=transport)
```

**Step 4: Run test**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/cli.py tests/test_cli_mcp_server.py
git commit -m "feat(bridge): add hermes-claude mcp-server CLI command with TDD"
```

---

## Task 8: Integrar MCP com sessões persistentes

**Objective:** O tool MCP pode criar sessões interativas no bridge server.

**Files:**
- Modify: `src/hermes_claude_bridge/mcp_server.py`
- Modify: `src/hermes_claude_bridge/client.py` (se necessário)
- Test: `tests/test_mcp_sessions.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_mcp_tool_creates_persistent_session():
    server = create_mcp_server(bridge_url="http://localhost:8765")
    result = await server.call_tool("claude_code_delegate", {"prompt": "hi", "mode": "interactive"})
    assert result["session_id"]
```

**Step 2: Run test**
Expected: FAIL — no session support

**Step 3: Implement**

Adicionar parâmetro `mode` e `bridge_url` ao tool. Quando `mode="interactive"`, usar `BridgeClient` para criar sessão e enviar prompt.

**Step 4: Run test**
Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/mcp_server.py tests/test_mcp_sessions.py
git commit -m "feat(bridge): MCP tool supports persistent interactive sessions with TDD"
```

---

## Task 9: Atualizar documentação e skill

**Files:**
- Modify: `.skills/hermes-claude-bridge/SKILL.md`
- Modify: `README.md`
- Modify: `src/hermes_claude_bridge/__init__.py`
- Modify: `pyproject.toml`

**Changes:**
- Bump version to 0.4.0
- Documentar `max_history_events`
- Documentar compressão de histórico
- Adicionar seção "MCP Server" com exemplo de uso via stdio e configuração no Hermes

**Commit:**

```bash
git add -A
git commit -m "docs(bridge): update skill and README for v0.4.0 history filter, compression and MCP"
```

---

## Task 10: Lint, testes E2E e release v0.4.0

**Commands:**

```bash
ruff check src/ tests/ examples/
ruff format src/ tests/ examples/
pytest tests/ -v
pytest tests/test_e2e.py -v
```

**Release:**

```bash
git tag v0.4.0
git push origin main --tags
```

---

## Risks & tradeoffs

1. **MCP SDK v1 vs v2:** Usar `mcp>=1.27,<2` para evitar breaking changes da v2 alpha.
2. **Compressão simples:** Não usa LLM para resumir, apenas conta eventos omitidos. Isso economiza tokens e tempo, mas perde detalhes.
3. **MCP tool stateless:** Por padrão o tool MCP pode ser stateless (`mode=headless`). Para sessões persistentes, exige `bridge_url` apontando para um bridge server rodando.
4. **stdio vs SSE:** O CLI `mcp-server` usará stdio por padrão, compatível com a maioria dos hosts MCP. SSE pode ser adicionado depois.

## Open questions

- O Hermes Agent já suporta clientes MCP nativamente? Se sim, qual transporte é preferido (stdio/SSE)?
- A compressão deveria ser opcional por sessão?
