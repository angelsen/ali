#!/usr/bin/env python3
"""Distribute tmux panes evenly or by fraction with column/row awareness."""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict

PANE_FORMAT = (
    "#{pane_index}:#{pane_id}:#{pane_width}:#{pane_height}:#{pane_left}:#{pane_top}"
)


class TmuxError(Exception):
    pass


def tmux(*args):
    try:
        result = subprocess.run(
            ["tmux", *args], capture_output=True, text=True, timeout=1, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise TmuxError(f"tmux unavailable: {e}") from e
    if result.returncode != 0:
        raise TmuxError(result.stderr.strip() or "tmux failed")
    return result.stdout.strip()


def target_args():
    # Under run-shell, tmux's "current" window is not the caller's; the binding exports TMUX_PANE.
    pane = os.environ.get("TMUX_PANE")
    return ["-t", pane] if pane else []


def parse_panes(text):
    # Digits are single-pane shorthand ("012"); commas allow multi-digit indices ("2,10").
    return text.split(",") if "," in text else list(text)


def parse_fraction(text):
    try:
        num, denom = (int(part) for part in text.split("/"))
    except ValueError:
        raise ValueError(f"Invalid fraction format: {text}") from None
    if denom == 0 or not 0 < num <= denom:
        raise ValueError(f"Fraction out of range: {text}")
    return num, denom


def get_detailed_pane_info():
    """Get tiled pane geometry from tmux, keyed by pane index."""
    output = tmux(
        "list-panes",
        *target_args(),
        "-f",
        "#{!=:#{pane_floating_flag},1}",
        "-F",
        PANE_FORMAT,
    )
    panes = {}
    for line in output.splitlines():
        idx, pid, width, height, left, top = line.split(":")
        panes[idx] = {
            "index": idx,
            "id": pid,
            "width": int(width),
            "height": int(height),
            "left": int(left),
            "top": int(top),
            "right": int(left) + int(width),
            "bottom": int(top) + int(height),
        }
    return panes


def find_enclosing_cell(node, pane_id, cell_type, enclosing=None):
    """Nearest ancestor cell of cell_type ("h" = side by side, "v" = stacked) holding pane_id."""
    if node["t"] == "p":
        return enclosing if node.get("I") == pane_id else None
    if node["t"] == cell_type:
        enclosing = node
    for child in node["c"]:
        found = find_enclosing_cell(child, pane_id, cell_type, enclosing)
        if found:
            return found
    return None


def available_size(dimension, pane_id):
    """Size of the cell a fraction applies to, not the whole window, for nested splits."""
    window_size = int(tmux("display", "-p", *target_args(), f"#{{window_{dimension}}}"))
    try:
        layout = json.loads(tmux("display", "-p", *target_args(), "#{window_layout}"))
        cell = find_enclosing_cell(
            layout["L"], pane_id, "h" if dimension == "width" else "v"
        )
        return cell["w" if dimension == "width" else "h"] if cell else window_size
    except (ValueError, KeyError, TypeError):
        return window_size


def group_panes_by_position(panes, dimension):
    """Group panes by row or column based on dimension."""
    groups = defaultdict(list)

    if dimension == "width":
        for pane in panes:
            groups[pane["top"]].append(pane)
    else:
        for pane in panes:
            groups[pane["left"]].append(pane)

    for key in groups:
        if dimension == "width":
            groups[key].sort(key=lambda p: p["left"])
        else:
            groups[key].sort(key=lambda p: p["top"])

    return dict(groups)


def find_column_panes(all_panes, selected_panes):
    """Find all panes within column boundaries of selected panes."""
    left_bound = min(p["left"] for p in selected_panes)
    right_bound = max(p["right"] for p in selected_panes)

    column = []
    for pane in all_panes.values():
        if pane["left"] >= left_bound and pane["right"] <= right_bound:
            column.append(pane)

    return column


def find_row_panes(all_panes, selected_panes):
    """Find all panes within row boundaries of selected panes."""
    top_bound = min(p["top"] for p in selected_panes)
    bottom_bound = max(p["bottom"] for p in selected_panes)

    row = []
    for pane in all_panes.values():
        if pane["top"] >= top_bound and pane["bottom"] <= bottom_bound:
            row.append(pane)

    return row


def are_all_siblings(all_panes, selected_panes, dimension):
    """True when the selection is every pane sharing one column (height) or row (width)."""
    first = selected_panes[0]
    if dimension == "height":
        siblings = {
            p["id"]
            for p in all_panes.values()
            if p["left"] == first["left"] and p["width"] == first["width"]
        }
    else:
        siblings = {
            p["id"]
            for p in all_panes.values()
            if p["top"] == first["top"] and p["height"] == first["height"]
        }
    return siblings == {p["id"] for p in selected_panes}


def main():
    """Main entry point for tmux pane distribution."""
    parser = argparse.ArgumentParser(
        description="Distribute tmux panes with column/row awareness"
    )
    parser.add_argument(
        "--dimension",
        "-d",
        required=True,
        choices=["width", "height"],
        help="Width or height",
    )
    parser.add_argument(
        "--panes",
        "-p",
        required=True,
        help="Pane indices: 012 for panes 0,1,2 or 2,10,11 for multi-digit",
    )
    parser.add_argument(
        "--fraction",
        "-f",
        help="Target fraction: 1/2, 2/3, etc. (default: equal distribution)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show diagnostic information",
    )

    args = parser.parse_args()

    try:
        return distribute(args)
    except TmuxError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def distribute(args):
    # Zoom reports the zoomed pane at full window size and leaves the others stale.
    if tmux("display", "-p", *target_args(), "#{window_zoomed_flag}") == "1":
        raise TmuxError("window is zoomed - unzoom before resizing")

    fraction = parse_fraction(args.fraction) if args.fraction else None

    all_panes = get_detailed_pane_info()
    if not all_panes:
        raise TmuxError("Could not get pane information")

    selected_panes = []
    for idx in parse_panes(args.panes):
        if idx not in all_panes:
            raise TmuxError(f"Pane {idx} does not exist")
        selected_panes.append(all_panes[idx])

    if args.dimension == "height":
        if len({p["top"] for p in all_panes.values()}) == 1:
            raise TmuxError("Cannot distribute height - all panes are in a single row")
    elif len({p["left"] for p in all_panes.values()}) == 1:
        raise TmuxError("Cannot distribute width - all panes are in a single column")

    commands = []
    flag = "-x" if args.dimension == "width" else "-y"

    if fraction:
        num, denom = fraction
        window_size = available_size(args.dimension, selected_panes[0]["id"])
        target_size = window_size * num // denom

        if args.dimension == "width":
            affected_panes = find_column_panes(all_panes, selected_panes)
        else:
            affected_panes = find_row_panes(all_panes, selected_panes)

        if args.verbose:
            print(
                f"Selected panes: {[p['index'] for p in selected_panes]}",
                file=sys.stderr,
            )
            print(
                f"Affected column/row: {[p['index'] for p in affected_panes]}",
                file=sys.stderr,
            )
            print(
                f"Target {args.dimension}: {target_size}px ({args.fraction} of {window_size}px)",
                file=sys.stderr,
            )

        limiting = max(affected_panes, key=lambda p: p[args.dimension])
        current_size = limiting[args.dimension]

        if args.verbose:
            print(
                f"Limiting pane: {limiting['index']} ({current_size}px → {target_size}px)",
                file=sys.stderr,
            )

        if current_size != target_size:
            commands.append(
                f"tmux resize-pane -t {limiting['id']} {flag} {target_size}"
            )

        groups = group_panes_by_position(affected_panes, args.dimension)

        for position, group in groups.items():
            if len(group) > 1:
                each_size = target_size // len(group)
                if args.verbose:
                    label = (
                        f"Row at y={position}"
                        if args.dimension == "width"
                        else f"Column at x={position}"
                    )
                    print(
                        f"{label}: {len(group)} panes × {each_size}px",
                        file=sys.stderr,
                    )

                for pane in group:
                    commands.append(
                        f"tmux resize-pane -t {pane['id']} {flag} {each_size}"
                    )

    elif len(selected_panes) > 1 and are_all_siblings(
        all_panes, selected_panes, args.dimension
    ):
        # tmux spreads siblings itself, borders and remainder included.
        commands.append(f"tmux select-layout -E -t {selected_panes[0]['id']}")

    elif len(selected_panes) > 1:
        total = sum(p[args.dimension] for p in selected_panes)
        each_size, remainder = divmod(total, len(selected_panes))

        if args.verbose:
            print(
                f"Redistributing {len(selected_panes)} panes: {total}px → {each_size}px (+1 on first {remainder})",
                file=sys.stderr,
            )

        for i, pane in enumerate(selected_panes):
            size = each_size + (1 if i < remainder else 0)
            commands.append(f"tmux resize-pane -t {pane['id']} {flag} {size}")

    if commands:
        print(" && sleep 0.05 && ".join(commands))
    elif args.verbose:
        print("No resize needed", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
