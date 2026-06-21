"""Tests for Hermes plugin installer."""

import os
import tempfile

from hermes_claude_bridge.setup_manager import install_hermes_plugin


def test_install_hermes_plugin():
    with tempfile.TemporaryDirectory() as tmp:
        plugin_path = install_hermes_plugin(tmp)
        assert os.path.isdir(plugin_path)
        assert os.path.isfile(os.path.join(plugin_path, "plugin.yaml"))
        assert os.path.isfile(os.path.join(plugin_path, "__init__.py"))
        assert os.path.isfile(os.path.join(plugin_path, "schemas.py"))
        assert os.path.isfile(os.path.join(plugin_path, "tools.py"))
