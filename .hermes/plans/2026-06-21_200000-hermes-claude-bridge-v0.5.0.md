# Hermes-Claude Bridge v0.5.0 — MCP Config Generator & Hermes Plugin

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Tornar a integração com o Hermes Agent plug-and-play: gerar configuração MCP pronta e instalar um plugin nativo do Hermes que expõe a tool `claude_code_delegate`.

**Architecture:**
- Adicionar módulo `setup_manager.py` com funções para gerar snippets de configuração MCP (`mcp_servers` YAML) e instalar o plugin do Hermes em `~/.hermes/plugins/hermes-claude-bridge/`.
- O plugin Hermes implementa `register(ctx)` e usa `ctx.register_tool()` para expor `claude_code_delegate`, usando `BridgeClient` para sessões persistentes.
- CLI `hermes-claude setup` ganha flags `--mcp-config` e `--hermes-plugin`.
- Testes TDD validam geração de config, instalação de arquivos e registro da tool.

**Tech Stack:** Python 3.11+, Click, PyYAML, Hermes Agent plugin API (`ctx.register_tool`), MCP stdio transport.

---

### Task 1: MCP config generator

**Objective:** Gerar snippet YAML/JSON de configuração MCP para o Hermes Agent.

**Files:**
- Create: `src/hermes_claude_bridge/setup_manager.py`
- Test: `tests/test_setup_manager_mcp.py`

**Step 1: Write failing test**

```python
def test_generate_mcp_config():
    from hermes_claude_bridge.setup_manager import generate_mcp_config
    config = generate_mcp_config()
    assert "mcp_servers" in config
    assert "hermes-claude-bridge" in config["mcp_servers"]
    assert config["mcp_servers"]["hermes-claude-bridge"]["command"] == "hermes-claude"
    assert "mcp-server" in config["mcp_servers"]["hermes-claude-bridge"]["args"]
```

**Step 2: Run test**

```bash
pytest tests/test_setup_manager_mcp.py -v
# Expected: FAIL — module not found
```

**Step 3: Implement**

```python
def generate_mcp_config():
    return {
        "mcp_servers": {
            "hermes-claude-bridge": {
                "command": "hermes-claude",
                "args": ["mcp-server"],
                "env": {},
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
git add -A && git commit -m "feat(bridge): add MCP config generator with TDD"
```

---

### Task 2: CLI setup command for MCP config

**Objective:** Adicionar `hermes-claude setup --mcp-config`.

**Files:**
- Modify: `src/hermes_claude_bridge/cli.py`
- Test: `tests/test_cli_setup_mcp.py`

**Step 1: Write failing test**

```python
from click.testing import CliRunner
from hermes_claude_bridge.cli import cli

def test_setup_mcp_config():
    runner = CliRunner()
    result = runner.invoke(cli, ["setup", "--mcp-config"])
    assert result.exit_code == 0
    assert "mcp_servers" in result.output
    assert "hermes-claude-bridge" in result.output
```

**Step 2: Run test**

```bash
pytest tests/test_cli_setup_mcp.py -v
# Expected: FAIL — command not found
```

**Step 3: Implement**

```python
@cli.command()
@click.option("--mcp-config", is_flag=True, help="Print MCP server config for Hermes")
def setup(mcp_config: bool):
    import yaml
    if mcp_config:
        from hermes_claude_bridge.setup_manager import generate_mcp_config
        click.echo(yaml.dump(generate_mcp_config(), sort_keys=False))
```

**Step 4: Verify**

```bash
pytest tests/test_cli_setup_mcp.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(bridge): add hermes-claude setup --mcp-config CLI with TDD"
```

---

### Task 3: Hermes plugin installer

**Objective:** Instalar plugin nativo do Hermes em `~/.hermes/plugins/hermes-claude-bridge/`.

**Files:**
- Modify: `src/hermes_claude_bridge/setup_manager.py`
- Create: `src/hermes_claude_bridge/plugin_template/plugin.yaml`
- Create: `src/hermes_claude_bridge/plugin_template/__init__.py`
- Create: `src/hermes_claude_bridge/plugin_template/schemas.py`
- Create: `src/hermes_claude_bridge/plugin_template/tools.py`
- Test: `tests/test_setup_manager_plugin.py`

**Step 1: Write failing test**

```python
import os
import tempfile

def test_install_hermes_plugin():
    from hermes_claude_bridge.setup_manager import install_hermes_plugin
    with tempfile.TemporaryDirectory() as tmp:
        install_hermes_plugin(tmp)
        plugin_dir = os.path.join(tmp, "hermes-claude-bridge")
        assert os.path.isdir(plugin_dir)
        assert os.path.isfile(os.path.join(plugin_dir, "plugin.yaml"))
        assert os.path.isfile(os.path.join(plugin_dir, "__init__.py"))
```

**Step 2: Run test**

```bash
pytest tests/test_setup_manager_plugin.py -v
# Expected: FAIL — function not found
```

**Step 3: Implement**

```python
def install_hermes_plugin(plugins_dir: str) -> str:
    import shutil
    from pathlib import Path
    src = Path(__file__).parent / "plugin_template"
    dst = Path(plugins_dir) / "hermes-claude-bridge"
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return str(dst)
```

**Step 4: Verify**

```bash
pytest tests/test_setup_manager_plugin.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(bridge): add Hermes plugin installer with TDD"
```

---

### Task 4: Hermes plugin implementation

**Objective:** Implementar `register(ctx)` no plugin que expõe `claude_code_delegate`.

**Files:**
- Modify: `src/hermes_claude_bridge/plugin_template/__init__.py`
- Modify: `src/hermes_claude_bridge/plugin_template/schemas.py`
- Modify: `src/hermes_claude_bridge/plugin_template/tools.py`
- Test: `tests/test_hermes_plugin.py`

**Step 1: Write failing test**

```python
import pytest

def test_plugin_register_exposes_tool():
    from hermes_claude_bridge.plugin_template import register

    class FakeCtx:
        def __init__(self):
            self.tools = []
        def register_tool(self, **kwargs):
            self.tools.append(kwargs)

    ctx = FakeCtx()
    register(ctx)
    assert any(t["name"] == "claude_code_delegate" for t in ctx.tools)
```

**Step 2: Run test**

```bash
pytest tests/test_hermes_plugin.py -v
# Expected: FAIL — plugin not implemented
```

**Step 3: Implement**

```python
"""Hermes plugin registration."""
import json
from . import schemas, tools

def register(ctx):
    ctx.register_tool(
        name="claude_code_delegate",
        toolset="hermes-claude-bridge",
        schema=schemas.CLAUDE_CODE_DELEGATE,
        handler=tools.handle_delegate,
        description="Delegate complex coding tasks to Claude Code CLI via the bridge.",
        is_async=True,
    )
```

**Step 4: Verify**

```bash
pytest tests/test_hermes_plugin.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(bridge): implement Hermes plugin register() with TDD"
```

---

### Task 5: CLI setup command for Hermes plugin

**Objective:** Adicionar `hermes-claude setup --hermes-plugin`.

**Files:**
- Modify: `src/hermes_claude_bridge/cli.py`
- Test: `tests/test_cli_setup_plugin.py`

**Step 1: Write failing test**

```python
import os
import tempfile
from click.testing import CliRunner
from hermes_claude_bridge.cli import cli

def test_setup_hermes_plugin():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        result = runner.invoke(cli, ["setup", "--hermes-plugin", "--plugins-dir", tmp])
        assert result.exit_code == 0
        assert os.path.isdir(os.path.join(tmp, "hermes-claude-bridge"))
```

**Step 2: Run test**

```bash
pytest tests/test_cli_setup_plugin.py -v
# Expected: FAIL — flags not found
```

**Step 3: Implement**

```python
@cli.command()
@click.option("--mcp-config", is_flag=True)
@click.option("--hermes-plugin", is_flag=True)
@click.option("--plugins-dir", default=None)
def setup(mcp_config: bool, hermes_plugin: bool, plugins_dir: str | None):
    if mcp_config:
        ...
    if hermes_plugin:
        from hermes_claude_bridge.setup_manager import install_hermes_plugin
        target = plugins_dir or os.path.expanduser("~/.hermes/plugins")
        path = install_hermes_plugin(target)
        click.echo(f"Hermes plugin installed at {path}")
```

**Step 4: Verify**

```bash
pytest tests/test_cli_setup_plugin.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(bridge): add hermes-claude setup --hermes-plugin CLI with TDD"
```

---

### Task 6: Update docs and skill

**Objective:** Documentar setup automático no README e SKILL.md.

**Files:**
- Modify: `README.md`
- Modify: `.skills/hermes-claude-bridge/SKILL.md`

**Changes:**
- Seção "Setup for Hermes Agent" com comandos `hermes-claude setup --mcp-config` e `hermes-claude setup --hermes-plugin`.
- Instruções para habilitar plugin em `~/.hermes/config.yaml`:
  ```yaml
  plugins:
    enabled:
      - hermes-claude-bridge
  ```

**Commit:**

```bash
git add -A && git commit -m "docs(bridge): document Hermes plugin and MCP setup"
```

---

### Task 7: Bump version and release

**Objective:** Atualizar para v0.5.0 e publicar release.

**Files:**
- Modify: `src/hermes_claude_bridge/__init__.py`
- Modify: `pyproject.toml`
- Modify: `README.md` releasing section
- Modify: `.skills/hermes-claude-bridge/SKILL.md` version

**Steps:**

```bash
ruff check src/ tests/ examples/
ruff format src/ tests/ examples/
pytest tests/ -v --ignore=tests/test_e2e.py
pytest tests/test_e2e.py -v
git add -A && git commit -m "chore(release): bump version to v0.5.0"
git tag v0.5.0 && git push origin main --tags
```

---

### Task 8: E2E validation

**Objective:** Validar a integração end-to-end: plugin instalado e tool chamável.

**Steps:**

1. Instalar plugin em diretório temporário:
   ```bash
   tmp=$(mktemp -d)
   hermes-claude setup --hermes-plugin --plugins-dir "$tmp"
   ```

2. Verificar arquivos do plugin:
   ```bash
   ls "$tmp/hermes-claude-bridge"
   cat "$tmp/hermes-claude-bridge/plugin.yaml"
   ```

3. Gerar config MCP:
   ```bash
   hermes-claude setup --mcp-config
   ```

4. Validar tool E2E real com Claude:
   ```bash
   pytest tests/test_e2e.py -v
   ```

**Success criteria:**
- Plugin files existem e `plugin.yaml` é válido.
- MCP config contém `mcp_servers.hermes-claude-bridge`.
- `pytest tests/test_e2e.py` passa.

---

## Risks / Open Questions

1. **Hermes plugin path:** o instalador assume `~/.hermes/plugins/`. Em alguns setups pode ser diferente; `--plugins-dir` cobre isso.
2. **PyYAML dependency:** já está em `dev`, mas setup imprime YAML. Considerar mantê-lo como dependência principal ou usar `json`. Optar por YAML pois é o formato nativo do Hermes.
3. **Plugin handler síncrono vs assíncrono:** Hermes suporta `is_async=True`; usaremos async com `BridgeClient`.
4. **E2E real:** requer `claude` CLI autenticado e funcionando; teste existente `test_e2e.py` já cobre.
