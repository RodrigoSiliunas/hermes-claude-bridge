"""Tests for the Hermes plugin registration."""

from hermes_claude_bridge.plugin_template import register


class FakeCtx:
    def __init__(self):
        self.tools = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)


def test_plugin_register_exposes_tool():
    ctx = FakeCtx()
    register(ctx)
    assert any(t["name"] == "claude_code_delegate" for t in ctx.tools)
    tool = next(t for t in ctx.tools if t["name"] == "claude_code_delegate")
    assert tool["toolset"] == "hermes-claude-bridge"
    assert tool["is_async"] is True
    assert "schema" in tool
