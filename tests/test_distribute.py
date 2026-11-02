import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parent.parent
    / "src/ali_tool/plugins/tmux/scripts/distribute.py"
)

pytestmark = pytest.mark.skipif(shutil.which("tmux") is None, reason="needs tmux")


def tmux(sock, *args):
    result = subprocess.run(
        ["tmux", "-L", sock, *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@pytest.fixture
def server():
    # -L, not -S: tmp_path can exceed the unix socket path limit.
    sock = f"ali-test-{os.getpid()}"
    tmux(sock, "-f", "/dev/null", "new-session", "-d", "-x", "200", "-y", "50")
    tmux(sock, "split-window", "-h")
    tmux(sock, "new-window")
    tmux(sock, "split-window", "-h")
    yield sock
    subprocess.run(["tmux", "-L", sock, "kill-server"], check=False)


def pane_ids(sock, window):
    return set(tmux(sock, "list-panes", "-t", window, "-F", "#{pane_id}").split())


def distribute(sock, pane):
    env = {k: v for k, v in os.environ.items() if k != "TMUX_PANE"}
    env["TMUX"] = tmux(sock, "display", "-p", "#{socket_path},#{pid},0")
    if pane:
        env["TMUX_PANE"] = pane
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "-d", "width", "-p", "01"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return {word for word in result.stdout.split() if word.startswith("%")}


def test_targets_the_callers_window_not_the_current_one(server):
    first, second = pane_ids(server, ":0"), pane_ids(server, ":1")
    assert tmux(server, "display", "-p", "#{window_index}") == "1"

    assert distribute(server, sorted(first)[0]) == first
    assert distribute(server, None) == second
