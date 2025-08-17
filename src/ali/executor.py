"""Command executor - Handles actual command execution."""

import subprocess
import sys
from typing import List, Union


def execute_command(command: Union[str, List[str]], execute: bool = False) -> int:
    """Execute a command - dry-run by default, must explicitly request execution.

    Args:
        command: Command to execute (string or list)
        execute: If True, actually execute. If False, just print (default!)

    Returns:
        Exit code from the command (0 for dry-run)
    """
    # Convert list to string for display
    cmd_str = command if isinstance(command, str) else " ".join(command)

    if not execute:
        print(f"Would execute: {cmd_str}")
        return 0

    try:
        # Execute based on type
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, capture_output=True, text=True)

        # Output as it appeared
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")

        return result.returncode
    except Exception as e:
        print(f"Failed to execute: {e}", file=sys.stderr)
        return 1
