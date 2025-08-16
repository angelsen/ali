"""Tmux plugin helper functions."""

import subprocess
import sys
from typing import Dict, Any, List


def expand_direction(state: Dict[str, Any]) -> str:
    """Expand direction to tmux flags based on object type."""
    obj = state.get("object", "PANE")
    direction = state.get("direction", "")

    DIRECTION_FLAGS = {
        "PANE": {
            "left": "-h -b",
            "right": "-h",
            "up": "-v -b",
            "down": "-v",
            "above": "-v -b",
            "below": "-v",
        },
        "COL": {"left": "-h -f -b", "right": "-h -f"},
        "ROW": {
            "up": "-v -f -b",
            "down": "-v -f",
            "above": "-v -f -b",
            "below": "-v -f",
        },
    }

    return DIRECTION_FLAGS.get(obj, {}).get(direction, "")


def expand_target_flag(state: Dict[str, Any]) -> str:
    """Format target flag if target exists."""
    target = state.get("target", "")
    if target:
        return f"-t {target}"
    return ""


def handle_visual_selector(state: Dict[str, Any]) -> str | None:
    """Generate visual selector command based on verb and object."""
    verb = state.get("verb")
    obj = state.get("object")
    target = state.get("target", "")
    with_target = state.get("with", "")

    # Standard display time for consistency
    display_time = "-d 2000"

    # Pane visual selectors
    if obj == "PANE" and (target == ".?" or with_target == ".?"):
        callbacks = {
            "GO": "",
            "DELETE": "'kill-pane -t \"%%\"'",
            "SWAP": "'swap-pane -t \"%%\"'",
        }
        callback = callbacks.get(verb, "") if verb else ""
        return f"tmux display-panes {display_time} {callback}".strip()

    # Window visual selectors
    elif obj == "WINDOW" and (target == ":?" or with_target == ":?"):
        callbacks = {
            "GO": "",
            "DELETE": "'kill-window -t \"%%\"'",
        }
        callback = (
            callbacks.get(verb, "'select-window -t \"%%\"'")
            if verb
            else "'select-window -t \"%%\"'"
        )
        if callback:
            return f"tmux choose-window {callback}"
        return "tmux choose-window"

    # Session visual selectors
    elif obj == "SESSION" and target == "?":
        return "tmux choose-session"

    return None


def generate_command(state: Dict[str, Any]) -> str | None:
    """Generate tmux command from state."""
    verb = state.get("verb")
    obj = state.get("object")

    # First check for visual selectors
    if visual_cmd := handle_visual_selector(state):
        return visual_cmd

    # Need both verb and object for command lookup
    if not verb or not obj:
        return None

    # Base command mapping
    base_commands = {
        ("CREATE", "PANE"): "split-window",
        ("CREATE", "WINDOW"): "new-window",
        ("CREATE", "SESSION"): "new-session",
        ("CREATE", "ROW"): "split-window",
        ("CREATE", "COL"): "split-window",
        ("DELETE", "PANE"): "kill-pane",
        ("DELETE", "WINDOW"): "kill-window",
        ("DELETE", "SESSION"): "kill-session",
        ("GO", "PANE"): "select-pane",
        ("GO", "WINDOW"): "select-window",
        ("SWITCH", "PANE"): "select-pane",
        ("SWITCH", "WINDOW"): "select-window",
        ("SWITCH", "SESSION"): "switch-client",
        ("SWAP", "PANE"): "swap-pane",
        ("SWAP", "WINDOW"): "swap-window",
        ("RENAME", "WINDOW"): "rename-window",
        ("RENAME", "SESSION"): "rename-session",
        ("LIST", "PANES"): "list-panes",
        ("LIST", "WINDOWS"): "list-windows",
        ("LIST", "SESSIONS"): "list-sessions",
    }

    cmd = base_commands.get((verb, obj))
    if not cmd:
        return None

    cmd = f"tmux {cmd}"

    # Add direction flags for CREATE
    if verb == "CREATE" and obj in ["PANE", "ROW", "COL"]:
        if direction_flags := expand_direction(state):
            cmd += f" {direction_flags}"

    # Add target flag
    if target := state.get("target"):
        cmd += f" -t {target}"

    # Add source/target for SWAP (already checked verb and obj are not None above)
    if verb == "SWAP":
        if with_target := state.get("with"):
            base_cmd = base_commands.get((verb, obj))
            if base_cmd:
                cmd = f"tmux {base_cmd} -s {state.get('target', '')} -t {with_target}"

    # Add name for RENAME
    if verb == "RENAME":
        if name := state.get("name"):
            cmd += f" {name}"

    return cmd


def normalize_target(target: str) -> str:
    """Normalize target notation."""
    # Map common aliases to empty (current)
    if target in [".", ":", ".THIS", ":THIS", "THIS", "CURRENT"]:
        return ""
    return target


def parse_panes(panes_str: str) -> List[str]:
    """Parse pane string like '024' into list ['0', '2', '4']."""
    # Remove any dots or separators
    panes_str = panes_str.replace(".", "").replace(",", "").replace(" ", "")
    return list(panes_str)


def script_distribute(args: List[str]) -> int:
    """
    Distribute panes evenly or by fraction.
    Called via: ali --plugin-script tmux distribute --panes 012 --dimension width --value 1/3

    Args:
        args: Command line arguments to parse

    Returns:
        Exit code (0 for success)
    """
    import argparse

    parser = argparse.ArgumentParser(prog="ali --plugin-script tmux distribute")
    parser.add_argument("--panes", "-p", required=True, help="Pane indices (e.g., 012)")
    parser.add_argument(
        "--dimension",
        "-d",
        required=True,
        choices=["width", "height"],
        help="Dimension to adjust",
    )
    parser.add_argument(
        "--value",
        "-v",
        default="equal",
        help="Distribution value (equal or fraction like 1/3)",
    )

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        return 1

    panes = parsed.panes
    dimension = parsed.dimension
    distribution = parsed.value

    try:
        pane_list = parse_panes(panes)

        if distribution == "equal":
            # Get total size available
            total_size = get_total_size(pane_list, dimension)
            equal_size = total_size // len(pane_list)

            # Resize each pane
            for pane in pane_list:
                resize_pane(pane, dimension, equal_size)

        else:
            # Parse fraction
            if "/" in distribution:
                numerator, denominator = distribution.split("/")
                fraction = float(numerator) / float(denominator)

                # Get container size
                container_size = get_container_size(dimension)
                target_total = int(container_size * fraction)
                size_per_pane = target_total // len(pane_list)

                # Resize each pane
                for pane in pane_list:
                    resize_pane(pane, dimension, size_per_pane)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def get_total_size(panes: List[str], dimension: str) -> int:
    """Get total current size of specified panes."""
    total = 0

    for pane in panes:
        try:
            output = subprocess.check_output(
                f"tmux display -p -t .{pane} '#{{pane_{dimension}}}'",
                shell=True,
                text=True,
            ).strip()
            total += int(output)
        except subprocess.CalledProcessError:
            pass  # Skip invalid panes

    return total


def get_container_size(dimension: str) -> int:
    """Get the container (window) size."""
    try:
        output = subprocess.check_output(
            f"tmux display -p '#{{window_{dimension}}}'", shell=True, text=True
        ).strip()
        return int(output)
    except subprocess.CalledProcessError:
        return 100  # Default fallback


def resize_pane(pane_id: str, dimension: str, size: int) -> None:
    """Resize a single pane."""
    flag = "-x" if dimension == "width" else "-y"
    cmd = f"tmux resize-pane -t .{pane_id} {flag} {size}"
    subprocess.run(cmd, shell=True)
