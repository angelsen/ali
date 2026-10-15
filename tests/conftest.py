from pathlib import Path

import pytest

from ali_tool.core import Router, ServiceRegistry

PLUGINS_DIR = Path(__file__).parent.parent / "src" / "ali_tool" / "plugins"


@pytest.fixture
def router(monkeypatch):
    monkeypatch.setenv("TMUX", "/tmp/tmux-test/default,1,0")
    registry = ServiceRegistry()
    registry.load_plugins(PLUGINS_DIR)
    return Router(registry)
