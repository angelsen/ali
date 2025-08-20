#!/usr/bin/env python3
"""Distribute tmux panes evenly or by fraction with column/row awareness."""

import argparse
import subprocess
import sys
from collections import defaultdict


def get_detailed_pane_info():
    """Get detailed pane information from tmux."""
    try:
        output = subprocess.check_output(
            [
                "tmux",
                "list-panes",
                "-F",
                "#{pane_index}:#{pane_id}:#{pane_width}:#{pane_height}:#{pane_left}:#{pane_top}",
            ],
            timeout=1,
            text=True,
        )

        panes = {}
        for line in output.strip().split("\n"):
            if line:
                parts = line.split(":")
                idx = parts[0]
                panes[idx] = {
                    "index": idx,
                    "id": parts[1],
                    "width": int(parts[2]),
                    "height": int(parts[3]),
                    "left": int(parts[4]),
                    "top": int(parts[5]),
                    "right": int(parts[4]) + int(parts[2]),
                    "bottom": int(parts[5]) + int(parts[3]),
                }
        return panes
    except subprocess.CalledProcessError:
        return {}
    except subprocess.TimeoutExpired:
        print("Error: tmux command timed out", file=sys.stderr)
        return {}


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


def main():
    """Main entry point for tmux pane distribution."""
    # Check if we're in a tmux session
    try:
        subprocess.check_output(["tmux", "info"], stderr=subprocess.DEVNULL, timeout=1)
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        print("Error: Not in a tmux session or tmux not available", file=sys.stderr)
        return 1

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
        "--panes", "-p", required=True, help="Pane indices: 012 for panes 0,1,2"
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

    selected_indices = list(args.panes)

    dimension_key = f"window_{args.dimension}"
    try:
        output = subprocess.check_output(
            ["tmux", "display", "-p", f"#{{{dimension_key}}}"], timeout=1, text=True
        ).strip()
        window_size = int(output)
    except subprocess.CalledProcessError:
        print(f"Error: Could not get window {args.dimension}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("Error: tmux command timed out", file=sys.stderr)
        return 1

    all_panes = get_detailed_pane_info()
    if not all_panes:
        print("Error: Could not get pane information", file=sys.stderr)
        return 1

    selected_panes = []
    for idx in selected_indices:
        if idx not in all_panes:
            print(f"Error: Pane {idx} does not exist", file=sys.stderr)
            return 1
        selected_panes.append(all_panes[idx])

    # Validate that distribution is possible
    if args.dimension == "height":
        # Check if all panes are in same row (same top coordinate)
        unique_tops = set(p["top"] for p in all_panes.values())
        if len(unique_tops) == 1:
            print(
                "Error: Cannot distribute height - all panes are in a single row",
                file=sys.stderr,
            )
            return 1

    elif args.dimension == "width":
        # Check if all panes are in same column (same left coordinate)
        unique_lefts = set(p["left"] for p in all_panes.values())
        if len(unique_lefts) == 1:
            print(
                "Error: Cannot distribute width - all panes are in a single column",
                file=sys.stderr,
            )
            return 1

    commands = []
    flag = "-x" if args.dimension == "width" else "-y"

    if args.fraction:
        if "/" not in args.fraction:
            print(f"Error: Invalid fraction format: {args.fraction}", file=sys.stderr)
            return 1

        num, denom = args.fraction.split("/")
        target_size = int(window_size * int(num) / int(denom))

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

        if args.dimension == "width":
            limiting = max(affected_panes, key=lambda p: p["width"])
            current_size = limiting["width"]
        else:
            limiting = max(affected_panes, key=lambda p: p["height"])
            current_size = limiting["height"]

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
                if args.dimension == "width":
                    each_size = target_size // len(group)
                    if args.verbose:
                        print(
                            f"Row at y={position}: {len(group)} panes × {each_size}px",
                            file=sys.stderr,
                        )
                else:
                    each_size = target_size // len(group)
                    if args.verbose:
                        print(
                            f"Column at x={position}: {len(group)} panes × {each_size}px",
                            file=sys.stderr,
                        )

                for pane in group:
                    commands.append(
                        f"tmux resize-pane -t {pane['id']} {flag} {each_size}"
                    )

    else:
        if args.dimension == "width":
            total_width = sum(p["width"] for p in selected_panes)
            each_width = total_width // len(selected_panes)

            if args.verbose:
                print(
                    f"Redistributing {len(selected_panes)} panes: {total_width}px → {len(selected_panes)} × {each_width}px",
                    file=sys.stderr,
                )

            for pane in selected_panes:
                commands.append(f"tmux resize-pane -t {pane['id']} -x {each_width}")
        else:
            total_height = sum(p["height"] for p in selected_panes)
            each_height = total_height // len(selected_panes)

            if args.verbose:
                print(
                    f"Redistributing {len(selected_panes)} panes: {total_height}px → {len(selected_panes)} × {each_height}px",
                    file=sys.stderr,
                )

            for pane in selected_panes:
                commands.append(f"tmux resize-pane -t {pane['id']} -y {each_height}")

    if commands:
        output = []
        for i, cmd in enumerate(commands):
            output.append(cmd)
            if i < len(commands) - 1:
                output.append("sleep 0.05")

        print(" && ".join(output))
    else:
        if args.verbose:
            print("No resize needed", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
