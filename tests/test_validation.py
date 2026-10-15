import subprocess
import sys

import pytest

from ali_tool.core import ServiceRegistry
from ali_tool.core.resolver import PluginError

from .conftest import PLUGINS_DIR


def write_plugin(root, body):
    plugin_dir = root / "bad"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text(body)
    return root


EXEC_PLUGIN = """
name: bad
vocabulary: {verbs: [PING]}
commands:
  - match: {verb: PING}
    exec: "echo {pane_id}"
"""

SERVICE_PLUGIN = """
name: bad
vocabulary: {verbs: [PING]}
commands:
  - match: {verb: PING}
    exec: "{ping}"
services:
  ping: "tmux display -p -t {?pane_id:{pane_id}}"
"""


@pytest.mark.parametrize(
    ("body", "template"),
    [
        (EXEC_PLUGIN, "command 1 exec 'echo {pane_id}'"),
        (SERVICE_PLUGIN, "service 'ping' 'tmux display -p -t {?pane_id:{pane_id}}'"),
    ],
)
def test_unknown_placeholder_fails_load(tmp_path, body, template):
    plugins = write_plugin(tmp_path, body)
    expected = f"plugin 'bad': {template}: unknown placeholder 'pane_id'"

    with pytest.raises(PluginError) as exc:
        ServiceRegistry().load_plugins(plugins)
    assert str(exc.value) == expected

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ali_tool.cli",
            "--quiet",
            "--plugins-dir",
            str(plugins),
            "PING",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert f"Error: {expected}" in result.stderr.splitlines()


def test_service_cannot_name_another_service(tmp_path):
    plugins = write_plugin(
        tmp_path,
        SERVICE_PLUGIN.replace("{?pane_id:{pane_id}}", "{split}"),
    )
    with pytest.raises(PluginError, match="unknown placeholder 'split'"):
        ServiceRegistry().load_plugins(plugins)


@pytest.mark.parametrize("tmux", [True, False])
def test_shipped_plugins_load(monkeypatch, tmux):
    if tmux:
        monkeypatch.setenv("TMUX", "/tmp/tmux-test/default,1,0")
    else:
        monkeypatch.delenv("TMUX", raising=False)
    registry = ServiceRegistry()
    registry.load_plugins(PLUGINS_DIR)
    names = {plugin.name for plugin in registry.plugins}
    assert names == (
        {"broot", "claude", "micro", "tmux"} if tmux else {"broot", "claude", "micro"}
    )
