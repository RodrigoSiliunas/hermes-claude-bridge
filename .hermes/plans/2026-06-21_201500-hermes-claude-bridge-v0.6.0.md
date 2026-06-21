# Hermes-Claude Bridge v0.6.0 — Model Presets, Hermes Plugin bridge_url Env, E2E Plugin Server

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Tornar o plugin Hermes ainda mais plug-and-play com presets de modelo no setup, permitir configurar o bridge URL padrão via variável de ambiente, e adicionar um teste E2E que valida o plugin usando uma sessão persistente no bridge server.

**Architecture:**
- `setup_manager.py` ganha `MODEL_PRESETS` e `generate_mcp_config(model=None)` para usar preset padrão ou customizado.
- CLI `setup` ganha `--model` opcional para gerar config com `env.CLAUDE_MODEL`.
- Plugin `tools.py` lê `HERMES_CLAUDE_BRIDGE_URL` env var como fallback para `bridge_url`.
- Teste E2E sobe o bridge server localmente, cria sessão interativa via plugin handler e envia dois prompts consecutivos provando persistência de contexto.

**Tech Stack:** Python 3.11+, Click, PyYAML, Hermes plugin API, FastAPI test client for server startup.

---

### Task 1: Model presets in MCP config generator

**Objective:** Permitir gerar config MCP com modelo default/preset.

**Files:**
- Modify: `src/hermes_claude_bridge/setup_manager.py`
- Test: `tests/test_setup_manager_mcp.py`

**Step 1: Write failing test**

```python
def test_generate_mcp_config_with_model_preset():
    from hermes_claude_bridge.setup_manager import generate_mcp_config
    config = generate_mcp_config(model="sonnet")
    assert config["mcp_servers"]["hermes-claude-bridge"]["env"]["CLAUDE_MODEL"] == "sonnet"


def test_generate_mcp_config_without_model():
    from hermes_claude_bridge.setup_manager import generate_mcp_config
    config = generate_mcp_config()
    assert "CLAUDE_MODEL" not in config["mcp_servers"]["hermes-claude-bridge"]["env"]
```

**Step 2: Run test**

```bash
pytest tests/test_setup_manager_mcp.py -v
# Expected: FAIL
```

**Step 3: Implement**

```python
MODEL_PRESETS = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
    "haiku": "claude-haiku-3-20240307",
}


def generate_mcp_config(model: str | None = None) -> dict[str, Any]:
    env = {}
    if model:
        env["CLAUDE_MODEL"] = MODEL_PRESETS.get(model, model)
    return {
        "mcp_servers": {
            "hermes-claude-bridge": {
                "command": "hermes-claude",
                "args": ["mcp-server"],
                "env": env,
                "enabled": True,
            }
        }
    }
```

**Step 4: Verify**

```bash
pytest tests/test_setup_manager_mcp.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(bridge): add model presets to MCP config generator with TDD"
```

---

### Task 2: CLI setup --model flag

**Objective:** Adicionar `--model` ao `setup --mcp-config`.

**Files:**
- Modify: `src/hermes_claude_bridge/cli.py`
- Test: `tests/test_cli_setup_mcp.py`

**Step 1: Write failing test**

```python
def test_setup_mcp_config_with_model():
    runner = CliRunner()
    result = runner.invoke(cli, ["setup", "--mcp-config", "--model", "sonnet"])
    assert result.exit_code == 0
    assert "CLAUDE_MODEL" in result.output
    assert "claude-sonnet" in result.output
```

**Step 2: Run test**

```bash
pytest tests/test_cli_setup_mcp.py -v
# Expected: FAIL
```

**Step 3: Implement**

```python
@cli.command()
@click.option("--mcp-config", is_flag=True)
@click.option("--hermes-plugin", is_flag=True)
@click.option("--plugins-dir", default=None)
@click.option("--model", default=None, help="Default Claude model preset (sonnet, opus, haiku or raw model string)")
def setup(mcp_config: bool, hermes_plugin: bool, plugins_dir: str | None, model: str | None):
    ...
    if mcp_config:
        click.echo(yaml.dump(generate_mcp_config(model=model), sort_keys=False))
```

**Step 4: Verify**

```bash
pytest tests/test_cli_setup_mcp.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(bridge): add --model flag to setup --mcp-config with TDD"
```

---

### Task 3: Hermes plugin reads bridge_url from env var

**Objective:** Plugin usa `HERMES_CLAUDE_BRIDGE_URL` como fallback quando `bridge_url` não é passado.

**Files:**
- Modify: `src/hermes_claude_bridge/plugin_template/tools.py`
- Test: `tests/test_hermes_plugin_env.py`

**Step 1: Write failing test**

```python
import os
import pytest

@pytest.mark.asyncio
async def test_plugin_uses_env_bridge_url(monkeypatch):
    monkeypatch.setenv("HERMES_CLAUDE_BRIDGE_URL", "http://bridge.example")
    from hermes_claude_bridge.plugin_template.tools import handle_delegate

    # Mock BridgeClient
    class FakeClient:
        def __init__(self, url):
            self.url = url
        async def create_session(self, **kwargs):
            return {"session_id": "abc"}
        async def send_prompt(self, *args, **kwargs):
            return {"status": "completed", "url": self.url}
        async def close(self):
            pass

    from hermes_claude_bridge.plugin_template import tools
    tools.BridgeClient = FakeClient
    result = await handle_delegate({"prompt": "hello"})
    data = json.loads(result)
    assert data["url"] == "http://bridge.example"
```

**Step 2: Run test**

```bash
pytest tests/test_hermes_plugin_env.py -v
# Expected: FAIL
```

**Step 3: Implement**

```python
bridge_url = args.get("bridge_url") or os.environ.get("HERMES_CLAUDE_BRIDGE_URL")
```

**Step 4: Verify**

```bash
pytest tests/test_hermes_plugin_env.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(bridge): Hermes plugin reads bridge_url from env var with TDD"
```

---

### Task 4: E2E plugin with persistent bridge server

**Objective:** Criar teste E2E que sobe o bridge server e usa o plugin handler para sessão persistente.

**Files:**
- Create: `tests/test_e2e_plugin_persistent.py`
- Modify: `src/hermes_claude_bridge/server.py` se necessário para health check.

**Step 1: Write failing test**

```python
import asyncio
import json
import os
import pytest

from hermes_claude_bridge.server import create_app
from hermes_claude_bridge.plugin_template.tools import handle_delegate


@pytest.mark.asyncio
async def test_plugin_persistent_session_on_bridge_server(tmp_path):
    os.environ.setdefault("HERMES_CLAUDE_BRIDGE_URL", "http://localhost:9876")
    app = create_app()
    # start uvicorn in background
    proc = await asyncio.create_subprocess_exec(
        "python", "-m", "uvicorn", "hermes_claude_bridge.server:app",
        "--host", "127.0.0.1", "--port", "9876"
    )
    try:
        # wait for health
        import httpx
        for _ in range(30):
            try:
                r = httpx.get("http://localhost:9876/health")
                if r.status_code == 200:
                    break
            except Exception:
                await asyncio.sleep(0.5)
        else:
            pytest.fail("server did not start")

        result1 = await handle_delegate({
            "prompt": "Remember the secret number is 42",
            "working_dir": str(tmp_path),
            "mode": "interactive",
            "bridge_url": "http://localhost:9876",
        })
        data1 = json.loads(result1)
        assert "session_id" in data1

        result2 = await handle_delegate({
            "prompt": "What is the secret number?",
            "working_dir": str(tmp_path),
            "mode": "interactive",
            "bridge_url": "http://localhost:9876",
        })
        data2 = json.loads(result2)
        assert "42" in data2.get("stdout", "") or "42" in data2.get("claude_response", "")
    finally:
        proc.terminate()
        await proc.wait()
```

**Step 2: Run test**

```bash
pytest tests/test_e2e_plugin_persistent.py -v
# Expected: FAIL
```

**Step 3: Implement / adjust**

- Garantir que o plugin handler reutilize sessão existente. Pode precisar adicionar `client.list_sessions()` e selecionar por `working_dir`.
- Ou implementar sessão por `working_dir` no handler.

**Step 4: Verify**

```bash
pytest tests/test_e2e_plugin_persistent.py -v
# Expected: PASS (requires claude CLI logged in)
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(bridge): E2E plugin test with persistent bridge server session"
```

---

### Task 5: Update docs, skill, bump version

**Objective:** Documentar novas features e publicar v0.6.0.

**Files:**
- Modify: `README.md`
- Modify: `.skills/hermes-claude-bridge/SKILL.md`
- Modify: `pyproject.toml`
- Modify: `src/hermes_claude_bridge/__init__.py`
- Modify: `src/hermes_claude_bridge/plugin_template/plugin.yaml`

**Changes:**
- Documentar `--model` no setup.
- Documentar `HERMES_CLAUDE_BRIDGE_URL` env var.
- Atualizar versão para 0.6.0.

**Commit:**

```bash
git add -A && git commit -m "docs(bridge): document v0.6.0 model presets and env bridge URL"
```

---

### Task 6: Final lint, test, release, install

**Objective:** Finalizar com lint, testes, release v0.6.0 e instalar o plugin nativo no Hermes.

**Steps:**

```bash
ruff check src/ tests/ examples/
ruff format src/ tests/ examples/
pytest tests/ -v --ignore=tests/test_e2e.py
pytest tests/test_e2e.py -v
pytest tests/test_e2e_plugin_persistent.py -v
git add -A && git commit -m "chore(release): bump version to v0.6.0"
git tag v0.6.0 && git push origin main --tags

# Instalar plugin no Hermes do usuário
hermes-claude setup --hermes-plugin
```

**Success criteria:**
- 65+ tests pass.
- Release v0.6.0 publicada.
- Plugin instalado em `~/.hermes/plugins/hermes-claude-bridge/`.

---

## Risks / Open Questions

1. **E2E persistente:** depende do claude CLI autenticado. Se falhar por não-login, manter teste como skip opcional.
2. **Reutilização de sessão:** o plugin precisa encontrar sessão existente por working_dir. BridgeClient precisa de `list_sessions()`.
3. **Porta 9876:** pode estar ocupada; usar porta dinâmica com `get_port()` se necessário.
