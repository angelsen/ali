#!/usr/bin/env python3
"""ALI CLI - Execute ALI commands from the command line."""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, Any
from .core.router import Router


def capture_context() -> Dict[str, Any]:
    """Capture context from environment."""
    context = {
        "env": dict(os.environ),
        "caller": os.environ.get("ALI_CALLER", "cli"),
        "cwd": os.getcwd(),
    }

    # Add tmux-specific context if in tmux
    if "TMUX" in os.environ:
        context["tmux_pane"] = os.environ.get("TMUX_PANE", "")

    return context


def find_plugins_dir() -> Path:
    """Find the plugins directory."""
    # Look for plugins in package
    package_dir = Path(__file__).parent / "plugins"
    if package_dir.exists():
        return package_dir

    # Look in user config
    user_plugins = Path.home() / ".config" / "ali" / "plugins"
    if user_plugins.exists():
        return user_plugins

    # Fallback to package location
    return package_dir


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ALI - Action Language Interpreter",
        epilog="Examples:\n"
        "  ali 'CREATE PANE LEFT'\n"
        "  ali 'DELETE .THIS'\n"
        "  ali 'GO :1'\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("command", nargs="?", help="ALI command to execute")

    parser.add_argument(
        "--list-verbs", action="store_true", help="List all available verbs"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )

    parser.add_argument(
        "--plugins-dir", type=Path, help="Directory containing plugin definitions"
    )

    args = parser.parse_args()

    # Initialize router
    router = Router()

    # Load plugins
    plugins_dir = args.plugins_dir or find_plugins_dir()
    if not plugins_dir.exists():
        print(f"Error: Plugins directory not found: {plugins_dir}", file=sys.stderr)
        sys.exit(1)

    router.load_plugins(plugins_dir)

    # Handle list-verbs
    if args.list_verbs:
        verbs = router.list_verbs()
        if verbs:
            print("Available commands:")
            for verb, plugins in sorted(verbs.items()):
                print(f"  {verb:10} ({', '.join(plugins)})")
        else:
            print("No plugins loaded")
        return

    # Need a command
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Capture context
    context = capture_context()

    # Execute command
    result = router.execute(args.command, context)

    if args.dry_run:
        print(f"Would execute: {result}")
    else:
        if result.startswith("Error:") or result.startswith("Unknown command:"):
            print(result, file=sys.stderr)
            sys.exit(1)
        else:
            # Actually execute the command
            import subprocess

            try:
                output = subprocess.run(
                    result, shell=True, capture_output=True, text=True
                )
                if output.stdout:
                    print(output.stdout)
                if output.stderr:
                    print(output.stderr, file=sys.stderr)
                sys.exit(output.returncode)
            except Exception as e:
                print(f"Failed to execute: {e}", file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
