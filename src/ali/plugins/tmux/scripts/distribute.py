#!/usr/bin/env python3
"""Distribute tmux panes evenly or by fraction."""

import argparse
import subprocess
import sys
from pathlib import Path

# Add src to path to import executor
sys.path.insert(0, str(Path(__file__).parents[4]))
from ali.executor import execute_command


def main():
    parser = argparse.ArgumentParser(description="Distribute tmux panes")
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
        "--dry-run", action="store_true", help="Show commands without executing"
    )

    args = parser.parse_args()

    # Parse panes: "012" → ['0', '1', '2']
    panes = list(args.panes)

    # Get window size
    dimension_key = f"window_{args.dimension}"
    try:
        output = subprocess.check_output(
            f"tmux display -p '#{{{dimension_key}}}'", shell=True, text=True
        ).strip()
        window_size = int(output)
    except subprocess.CalledProcessError:
        print(f"Error: Could not get window {args.dimension}", file=sys.stderr)
        return 1

    # Calculate target size
    if args.fraction:
        # Parse fraction like "1/2"
        if "/" in args.fraction:
            num, denom = args.fraction.split("/")
            target_total = int(window_size * int(num) / int(denom))
        else:
            print(f"Error: Invalid fraction format: {args.fraction}", file=sys.stderr)
            return 1
    else:
        # Equal distribution - use full window
        target_total = window_size

    # Size per pane (with remainder going to first pane)
    size_per_pane = target_total // len(panes)
    remainder = target_total % len(panes)

    # Resize each pane
    flag = "-x" if args.dimension == "width" else "-y"

    for i, pane in enumerate(panes):
        # First pane gets the remainder pixels
        size = size_per_pane + (remainder if i == 0 else 0)

        cmd = f"tmux resize-pane -t .{pane} {flag} {size}"
        execute_command(cmd, execute=not args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
