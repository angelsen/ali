import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parent.parent / "src/ali_tool/plugins/tmux/scripts/distribute.py"
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
    sock = f"ali-test-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    tmux(sock, "-f", "/dev/null", "new-session", "-d", "-x", "200", "-y", "50")
    tmux(sock, "split-window", "-h")
    tmux(sock, "new-window")
    tmux(sock, "split-window", "-h")
    yield sock
    subprocess.run(["tmux", "-L", sock, "kill-server"], check=False)


def pane_ids(sock, window):
    return set(tmux(sock, "list-panes", "-t", window, "-F", "#{pane_id}").split())


def env_for(sock, pane):
    env = {k: v for k, v in os.environ.items() if k != "TMUX_PANE"}
    env["TMUX"] = tmux(sock, "display", "-p", "#{socket_path},#{pid},0")
    if pane:
        env["TMUX_PANE"] = pane
    return env


def run_script(sock, pane, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env_for(sock, pane),
        capture_output=True,
        text=True,
        check=False,
    )


def apply(sock, pane, *args):
    result = run_script(sock, pane, *args)
    assert result.returncode == 0, result.stderr
    subprocess.run(["sh", "-c", result.stdout], env=env_for(sock, pane), check=True)
    return result.stdout


def sizes(sock, window, field):
    out = tmux(sock, "list-panes", "-t", window, "-F", f"#{{{field}}}")
    return [int(line) for line in out.split()]


def new_window(sock, *splits):
    window = tmux(sock, "new-window", "-P", "-F", "#{window_id}")
    for split in splits:
        tmux(sock, "split-window", *split)
    return window


def test_targets_the_callers_window_not_the_current_one(server):
    first, second = pane_ids(server, ":0"), pane_ids(server, ":1")
    assert tmux(server, "display", "-p", "#{window_index}") == "1"

    def touched(pane):
        result = run_script(server, pane, "-d", "width", "-p", "01")
        return {w for w in result.stdout.split() if w.startswith("%")}

    assert touched(min(first)) <= first
    assert touched(None) <= second


def test_equal_height_balances_the_remainder(server):
    window = new_window(server, ["-v"], ["-v"], ["-v"])
    pane = tmux(server, "list-panes", "-t", window, "-F", "#{pane_id}").split()[0]
    tmux(server, "resize-pane", "-t", pane, "-y", "30")

    apply(server, pane, "-d", "height", "-p", "0123")

    heights = sizes(server, window, "pane_height")
    assert max(heights) - min(heights) <= 1
    assert sum(heights) + 3 == 50


def test_multi_digit_indices_need_commas(server):
    window = new_window(server)
    for _ in range(11):
        tmux(server, "split-window", "-h")
        tmux(server, "select-layout", "even-horizontal")
    ids = tmux(server, "list-panes", "-t", window, "-F", "#{pane_id}").split()

    result = run_script(server, ids[0], "-d", "width", "-p", "0,10,11")

    assert result.returncode == 0, result.stderr
    used = {w for w in result.stdout.split() if w.startswith("%")}
    assert used == {ids[0], ids[10], ids[11]}


def test_fraction_applies_to_the_enclosing_cell(server):
    window = new_window(server, ["-v"])
    bottom = tmux(server, "list-panes", "-t", window, "-F", "#{pane_id}").split()[1]
    tmux(server, "split-window", "-t", bottom, "-h")
    tmux(server, "split-window", "-t", bottom, "-v")
    index = tmux(server, "display", "-p", "-t", bottom, "#{pane_index}")

    apply(server, bottom, "-d", "height", "-p", index, "-f", "1/2")

    cell = int(tmux(server, "display", "-p", "-t", bottom, "#{pane_height}"))
    stacked = [
        int(tmux(server, "display", "-p", "-t", p, "#{pane_height}"))
        for p in pane_ids(server, window)
    ]
    assert cell < 20
    assert max(stacked) > cell


@pytest.mark.parametrize("fraction", ["1/0", "a/b", "3/2", "0/2", "12"])
def test_bad_fraction_is_an_error_not_a_traceback(server, fraction):
    pane = min(pane_ids(server, ":0"))

    result = run_script(server, pane, "-d", "width", "-p", "0", "-f", fraction)

    assert result.returncode == 1
    assert result.stderr.startswith("Error:")
    assert "Traceback" not in result.stderr


def test_zoomed_window_is_refused(server):
    pane = min(pane_ids(server, ":0"))
    tmux(server, "resize-pane", "-Z", "-t", pane)

    result = run_script(server, pane, "-d", "width", "-p", "01")

    assert result.returncode == 1
    assert "zoomed" in result.stderr
