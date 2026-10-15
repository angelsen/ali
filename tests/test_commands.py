import subprocess

import pytest

ORIGIN = (
    r'-e ORIGIN_PANE="$TMUX_PANE"'
    r''' -e ORIGIN_WINDOW="$(test -n "$TMUX_WINDOW" && printf %s "$TMUX_WINDOW" || tmux display -p -t "$TMUX_PANE" "$(printf '#\173window_id\175')")"'''
    r''' -e ORIGIN_SESSION="$(test -n "$TMUX_SESSION" && printf %s "$TMUX_SESSION" || tmux display -p -t "$TMUX_PANE" "$(printf '#\173session_name\175')")"'''
)
POPUP = 'tmux display-popup -w 80% -h 80% -d "$PWD" -E'
FORK = "'claude --continue --fork-session'"

COMMANDS = {
    "SPLIT pop": f"{POPUP} {ORIGIN}",
    "SPLIT down": f"tmux split-window {ORIGIN} -v",
    "CREATE WINDOW": f"tmux new-window {ORIGIN}",
    "FORK pop": f"{POPUP} {ORIGIN} {FORK}",
    "FORK": f"tmux split-window {ORIGIN} -v {FORK}",
}


@pytest.mark.parametrize(("command", "expected"), COMMANDS.items())
def test_printed_command(router, command, expected):
    printed = router.execute(command)
    assert printed == expected
    assert not any(ch in printed for ch in "{}")
    assert "ORIGIN_PANE= " not in printed and "ORIGIN_WINDOW= " not in printed
    assert "ORIGIN_SESSION= " not in printed and not printed.endswith("=")
    assert subprocess.run(["sh", "-n", "-c", printed], check=False).returncode == 0
