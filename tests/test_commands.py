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
    "TERMTAP": f"{POPUP} {ORIGIN} 'termtap companion --popup'",
    "GO THIS": "tmux select-pane -t .",
    "GO .CURRENT": "tmux select-pane -t .",
    "KILL :THIS": "tmux kill-window -t :",
    "JOIN THIS .2": "tmux join-pane -h -s . -t .2",
    "SWAP .1 CURRENT": "tmux swap-pane -s .1 -t .",
}


@pytest.mark.parametrize(("command", "expected"), COMMANDS.items())
def test_printed_command(router, command, expected):
    printed = router.execute(command)
    assert printed == expected
    assert not any(ch in printed for ch in "{}")
    assert "ORIGIN_PANE= " not in printed and "ORIGIN_WINDOW= " not in printed
    assert "ORIGIN_SESSION= " not in printed and not printed.endswith("=")
    assert subprocess.run(["sh", "-n", "-c", printed], check=False).returncode == 0


def test_selector_file_keeps_xargs_placeholder(router):
    printed = router.execute("EDIT br?")
    assert printed == f"broot | xargs -I {{}} tmux split-window {ORIGIN} -h 'micro {{}}'"
    assert subprocess.run(["sh", "-n", "-c", printed], check=False).returncode == 0


def test_unknown_verb_suggests_closest(router):
    assert "Did you mean LAZYGIT?" in router.execute("LAZYGTI")
    assert "Did you mean" not in router.execute("QQQQQQ")


def test_selector_lookup_ignores_case(router):
    assert router.execute("ECHO BR?") == router.execute("ECHO br?")


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("ECHO bt?", "Error: Unknown selector: bt?. Did you mean br?"),
        ("ECHO zzzzzz?", "Error: Unknown selector: zzzzzz?. Available: "),
    ],
)
def test_unknown_selector_is_named(router, command, message):
    assert router.execute(command).startswith(message)
