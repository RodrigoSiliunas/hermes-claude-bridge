# Hermes-Claude Bridge v2.1 + v2.2 — Real-Time SSE & Interactive Persistent Sessions

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Evoluir o bridge para (1) notificar clientes SSE imediatamente quando eventos forem persistidos, e (2) suportar sessões interativas persistentes com o Claude Code CLI sem o modo headless `-p`, permitindo que o Claude faça perguntas e mantenha contexto entre turnos.

**Architecture:**

```
Hermes Agent ←—— SSE (asyncio.Condition notify) ——→ Bridge Server
                                ↓
                       Session Manager + Event Store
                                ↓
           ┌────────────────────┴────────────────────┐
           │                                     │
    HeadlessExecutor (`claude -p`)      InteractiveExecutor (PTY `claude`)
           │                                     │
           └────────────────────┬────────────────────┘
                                ↓
                         OutputParser
                                ↓
                           Result
```

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy async, asyncio.Condition, pty (POSIX), pytest, TDD.

---

## Parte 1 — Notificações SSE em tempo real (v2.1)

### Task 1: Substituir polling por `asyncio.Condition` no SessionManager

**Objective:** Quando `add_event` for chamado, listeners SSE devem acordar imediatamente.

**Files:**
- Modify: `src/hermes_claude_bridge/session_manager.py`
- Modify: `src/hermes_claude_bridge/server.py`
- Test: `tests/test_session_manager_notify.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_event_listener_notified():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    manager = SessionManager(engine)
    session = await manager.create_session("/tmp")

    received = []

    async def listener():
        async for event in manager.listen_events(session["session_id"]):
            received.append(event)
            break

    task = asyncio.create_task(listener())
    await asyncio.sleep(0.05)
    await manager.add_event(session["session_id"], "user_prompt", {"prompt": "hi"})
    await asyncio.wait_for(task, timeout=1.0)

    assert len(received) == 1
    assert received[0]["event_type"] == "user_prompt"
```

**Step 2: Run test to verify failure**

```bash
pytest tests/test_session_manager_notify.py -v
```

Expected: FAIL — `SessionManager` has no `listen_events`

**Step 3: Write minimal implementation**

Adicionar `asyncio.Condition` ao `SessionManager` e método `listen_events(session_id, last_id=0)` que yielda novos eventos conforme forem inseridos.

**Step 4: Run test to verify pass**

```bash
pytest tests/test_session_manager_notify.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_session_manager_notify.py src/hermes_claude_bridge/session_manager.py
git commit -m "feat(bridge): add real-time event listeners via asyncio.Condition"
```

---

### Task 2: Usar listener no endpoint SSE do servidor

**Objective:** O endpoint `/sessions/{id}/events` deve usar `listen_events` ao invés de polling.

**Files:**
- Modify: `src/hermes_claude_bridge/server.py`
- Test: `tests/test_server_sse_realtime.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_sse_stream_receives_event():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        session = await http.post("/sessions", json={"working_dir": "/tmp"})
        session_id = session.json()["session_id"]

        lines = []
        async with http.stream("GET", f"/sessions/{session_id}/events") as stream:
            await http.post(f"/sessions/{session_id}/prompt", json={"prompt": "hello", "timeout": 5})
            async for line in stream.aiter_lines():
                lines.append(line)
                if "user_prompt" in line:
                    break

        assert any("user_prompt" in line for line in lines)
```

**Step 2: Run test to verify failure**

Expected: FAIL — SSE ainda usa polling

**Step 3: Write minimal implementation**

Atualizar generator em `server.py` para usar `session_manager.listen_events(session_id)`.

**Step 4: Run test to verify pass**

```bash
pytest tests/test_server_sse_realtime.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/server.py tests/test_server_sse_realtime.py
git commit -m "feat(bridge): use real-time listeners in SSE endpoint"
```

---

## Parte 2 — Sessão interativa persistente (v2.2)

### Task 3: Executor interativo baseado em PTY

**Objective:** Criar `InteractiveExecutor` que mantém um processo `claude` aberto via pseudo-terminal e envia prompts/recebe respostas.

**Files:**
- Create: `src/hermes_claude_bridge/interactive_executor.py`
- Test: `tests/test_interactive_executor.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_interactive_executor_runs_cat():
    """Use cat as a stand-in for interactive process."""
    executor = InteractiveExecutor("cat")
    await executor.start()
    response = await executor.send("hello\n")
    await executor.stop()
    assert "hello" in response
```

**Step 2: Run test to verify failure**

Expected: FAIL — `InteractiveExecutor` não existe

**Step 3: Write minimal implementation**

Usar `asyncio.create_subprocess_exec` com `stdin=PIPE`, `stdout=PIPE`, `stderr=PIPE`. Para POSIX, usar `preexec_fn=os.setsid` e pseudo-terminal. Inicialmente implementar modo pipe para testes cross-platform; PTY como upgrade.

**Step 4: Run test to verify pass**

```bash
pytest tests/test_interactive_executor.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/interactive_executor.py tests/test_interactive_executor.py
git commit -m "feat(bridge): add InteractiveExecutor for persistent CLI sessions"
```

---

### Task 4: Integrar executor interativo ao Bridge Server

**Objective:** Permitir que sessões optem por modo `interactive`; o server usa `InteractiveExecutor` para essas sessões.

**Files:**
- Modify: `src/hermes_claude_bridge/session_manager.py`
- Modify: `src/hermes_claude_bridge/server.py`
- Modify: `src/hermes_claude_bridge/schemas.py`
- Test: `tests/test_server_interactive.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_create_interactive_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        resp = await http.post("/sessions", json={
            "working_dir": "/tmp",
            "mode": "interactive",
        })
        assert resp.status_code == 201
        assert resp.json()["mode"] == "interactive"
```

**Step 2: Run test to verify failure**

Expected: FAIL — `mode` não suportado

**Step 3: Write minimal implementation**

- Adicionar `mode: Literal["headless", "interactive"]` ao `ClaudeSession`.
- Atualizar `CreateSessionRequest` e `SessionManager.create_session`.
- No server, escolher executor com base no `mode`.

**Step 4: Run test to verify pass**

```bash
pytest tests/test_server_interactive.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/session_manager.py src/hermes_claude_bridge/server.py src/hermes_claude_bridge/schemas.py tests/test_server_interactive.py
git commit -m "feat(bridge): support interactive session mode in server"
```

---

### Task 5: Detectar perguntas no modo interativo

**Objective:** Quando o executor interativo detectar que o Claude está esperando input, sinalizar `WAITING_USER_INPUT`.

**Files:**
- Modify: `src/hermes_claude_bridge/interactive_executor.py`
- Modify: `src/hermes_claude_bridge/parser.py`
- Test: `tests/test_interactive_questions.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_detect_interactive_question():
    executor = InteractiveExecutorMock(responses=["Should I proceed? (y/n)"])
    result = await executor.run_task(ClaudeTask(prompt="refactor"))
    assert result.status == "waiting_user_input"
    assert "Should I proceed?" in result.pending_question
```

**Step 2: Run test to verify failure**

Expected: FAIL — status ainda não é detectado

**Step 3: Write minimal implementation**

- `InteractiveExecutor.send()` retorna tupla `(response, waiting_input)`.
- Parser detecta perguntas e o bridge/server constroem `ClaudeResult` com status apropriado.

**Step 4: Run test to verify pass**

```bash
pytest tests/test_interactive_questions.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/interactive_executor.py src/hermes_claude_bridge/parser.py tests/test_interactive_questions.py
git commit -m "feat(bridge): detect interactive questions and pause session"
```

---

### Task 6: Responder perguntas no modo interativo

**Objective:** Endpoint `/sessions/{id}/answer` deve enviar a resposta do usuário de volta ao processo interativo e continuar.

**Files:**
- Modify: `src/hermes_claude_bridge/server.py`
- Modify: `src/hermes_claude_bridge/session_manager.py`
- Test: `tests/test_server_interactive_answer.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_answer_question_in_interactive_session():
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    app = create_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        session = await http.post("/sessions", json={"working_dir": "/tmp", "mode": "interactive"})
        session_id = session.json()["session_id"]

        # mock executor returns question
        ...

        resp = await http.post(f"/sessions/{session_id}/answer", json={"answer": "yes"})
        assert resp.status_code == 200
```

**Step 2: Run test to verify failure**

Expected: FAIL — answer não sabe retomar sessão interativa

**Step 3: Write minimal implementation**

- `SessionManager` mantém cache de executores ativos por session_id.
- `/answer` responde ao executor e continua.

**Step 4: Run test to verify pass**

```bash
pytest tests/test_server_interactive_answer.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/server.py src/hermes_claude_bridge/session_manager.py tests/test_server_interactive_answer.py
git commit -m "feat(bridge): allow answering Claude questions in interactive sessions"
```

---

### Task 7: Integração real com `claude` CLI interativo

**Objective:** Substituir mock/processos de teste por execução real do `claude` CLI em modo interativo.

**Files:**
- Modify: `src/hermes_claude_bridge/interactive_executor.py`
- Test: `tests/test_interactive_claude.py` (optional/E2E)

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_claude_interactive_hello():
    executor = InteractiveExecutor("claude")
    await executor.start()
    response = await executor.send("say hello\n")
    await executor.stop()
    assert "hello" in response.lower()
```

**Step 2: Run test to verify failure**

Expected: FAIL — precisa de implementação PTY

**Step 3: Write minimal implementation**

Implementar PTY com `pty.openpty()`, `os.ttyname`, e gerenciamento de processo assíncrono. Ler até delimiter de prompt do Claude Code.

**Step 4: Run test to verify pass**

```bash
pytest tests/test_interactive_claude.py -v
```

Expected: PASS (requer `claude` logado)

**Step 5: Commit**

```bash
git add src/hermes_claude_bridge/interactive_executor.py tests/test_interactive_claude.py
git commit -m "feat(bridge): real PTY-based interactive Claude executor"
```

---

### Task 8: Documentação e skill update

**Objective:** Atualizar README, SKILL.md e CLI para refletir modo interativo e SSE em tempo real.

**Files:**
- Modify: `README.md`
- Modify: `.skills/hermes-claude-bridge/SKILL.md`
- Modify: `src/hermes_claude_bridge/cli.py` (adicionar `--mode interactive`)
- Test: `tests/test_cli_interactive_mode.py`

**Step 1: Write failing test**

```python
def test_cli_run_interactive_mode():
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "hello", "--mode", "interactive"])
    assert result.exit_code == 0
```

**Step 2: Run test to verify failure**

Expected: FAIL — `--mode` ainda não existe no comando run

**Step 3: Write minimal implementation**

Adicionar `--mode` ao comando `run` e documentar.

**Step 4: Run test to verify pass**

```bash
pytest tests/test_cli_interactive_mode.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add README.md .skills/hermes-claude-bridge/SKILL.md src/hermes_claude_bridge/cli.py tests/test_cli_interactive_mode.py
git commit -m "docs(bridge): document interactive mode and real-time SSE"
```

---

## Finalização

### Task 9: Lint, testes E2E e release v0.3.0

**Objective:** Garantir qualidade e publicar v0.3.0.

**Step 1: Lint e format**

```bash
ruff check src/ tests/ examples/
ruff format src/ tests/ examples/
```

**Step 2: Run full test suite**

```bash
pytest tests/ -v
```

Expected: todos passam

**Step 3: Run E2E tests**

```bash
pytest tests/test_e2e.py tests/test_interactive_claude.py -v
```

Expected: passam (requer `claude` logado)

**Step 4: Bump version e release**

```bash
# Atualizar __version__ e pyproject.toml para 0.3.0
git add -A
git commit -m "chore(release): bump version to v0.3.0"
git tag v0.3.0
git push origin main --tags
```

**Step 5: Verify GitHub Actions**

```bash
gh run list --limit 5
gh release list --limit 5
```

Expected: CI e Release v0.3.0 success

---

## Risks, Tradeoffs, and Open Questions

- **PTY é POSIX-only**: Windows pode não suportar `pty.openpty()`. Documentar limitação ou fornecer fallback para headless.
- **Detecção de prompt do Claude**: heurística baseada em delimitadores pode quebrar entre versões do CLI. Manter testes E2E.
- **Segurança em modo interativo**: `dontAsk` é ainda mais perigoso quando persistente. Recomendar `acceptEdits` ou `default`.
- **Banco de dados**: sessões interativas mantêm processos abertos; garantir cleanup no shutdown (`executor.stop()`).
- **Open question**: Devemos expor timeout por inatividade para matar sessões interativas ociosas?
