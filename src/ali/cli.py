#!/usr/bin/env python3
"""ALI CLI - Execute ALI commands from the command line."""

import sys
import os
import argparse
import importlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from .core.router import Router

# Exit code constants
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_COMMAND_NOT_FOUND = 127

# Version from pyproject.toml
ALI_VERSION = "0.1.0"


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


def handle_plugin_script(argv: List[str]) -> None:
    """Handle --plugin-script execution.

    Args:
        argv: Complete sys.argv list

    This function handles the special case of plugin script execution
    and exits the program with appropriate code.
    """
    idx = argv.index("--plugin-script")

    # Check if we have enough arguments
    if idx + 2 >= len(argv):
        print(
            "Error: --plugin-script requires PLUGIN and SCRIPT arguments",
            file=sys.stderr,
        )
        print("Usage: ali --plugin-script PLUGIN SCRIPT [ARGS...]", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    # Extract plugin and script name
    plugin_name = argv[idx + 1]
    script_name = argv[idx + 2]

    # Everything after script name goes to the plugin
    script_args = argv[idx + 3 :]

    # Check for --help or -h in script args to pass through
    if "--help" in script_args or "-h" in script_args:
        # Let the plugin script handle its own help
        pass

    # Check for --dry-run in the main args (before --plugin-script)
    dry_run = "--dry-run" in argv[:idx]

    try:
        # Import plugin module
        module = importlib.import_module(f"ali.plugins.{plugin_name}.plugin")

        # Look for script_<name> function
        func_name = f"script_{script_name}"
        if not hasattr(module, func_name):
            # Try without prefix as fallback
            func_name = script_name

        if not hasattr(module, func_name):
            print(
                f"Error: Script '{script_name}' not found in plugin '{plugin_name}'",
                file=sys.stderr,
            )
            print(f"Available scripts in {plugin_name}:", file=sys.stderr)
            # List available script functions
            for attr in dir(module):
                if attr.startswith("script_") or attr == "distribute":
                    print(f"  - {attr.replace('script_', '')}", file=sys.stderr)
            sys.exit(EXIT_ERROR)

        func = getattr(module, func_name)

        # Execute the script
        if dry_run:
            print(
                f"Would execute plugin script: {plugin_name}.{func_name}({script_args})"
            )
            sys.exit(EXIT_SUCCESS)
        else:
            exit_code = func(script_args)
            sys.exit(exit_code if exit_code is not None else EXIT_SUCCESS)

    except ImportError as e:
        print(f"Error: Plugin '{plugin_name}' not found: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    except Exception as e:
        print(f"Error executing plugin script: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)


def execute_command(command: str, dry_run: bool = False) -> int:
    """Execute a shell command.

    Args:
        command: The command to execute
        dry_run: If True, only print what would be executed

    Returns:
        Exit code from the command
    """
    if dry_run:
        print(f"Would execute: {command}")
        return EXIT_SUCCESS

    try:
        output = subprocess.run(command, shell=True, capture_output=True, text=True)
        if output.stdout:
            print(output.stdout, end="")
        if output.stderr:
            print(output.stderr, file=sys.stderr, end="")
        return output.returncode
    except Exception as e:
        print(f"Failed to execute: {e}", file=sys.stderr)
        return EXIT_ERROR


def main():
    """Main CLI entry point."""
    # Check for --plugin-script early to handle its args specially
    if "--plugin-script" in sys.argv:
        handle_plugin_script(sys.argv)
        # handle_plugin_script always exits, so we never get here
        return

    # Normal argument parsing for non-plugin-script commands
    parser = argparse.ArgumentParser(
        description="ALI - Action Language Interpreter",
        epilog="Examples:\n"
        "  ali 'CREATE PANE LEFT'\n"
        "  ali 'DELETE .THIS'\n"
        "  ali 'GO :1'\n"
        "  ali 'HORIZONTAL 012'  # Distribute panes horizontally\n"
        "  ali 'VERTICAL .? AS 20/50/30'  # Visual selector with fractions\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ALI {ALI_VERSION}",
        help="Show ALI version and exit",
    )

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

    # Note: --plugin-script is handled earlier in main() before argparse
    parser.add_argument(
        "--plugin-script",
        help=argparse.SUPPRESS,  # Hide from help since it's handled specially
    )

    parser.add_argument("command", nargs="*", help="ALI command to execute")

    args = parser.parse_args()

    # Initialize router
    router = Router()

    # Load plugins
    plugins_dir = args.plugins_dir or find_plugins_dir()
    if not plugins_dir.exists():
        print(f"Error: Plugins directory not found: {plugins_dir}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    router.load_plugins(plugins_dir)

    # Handle list-verbs
    if args.list_verbs:
        verbs = router.list_verbs()
        if verbs:
            print("Available commands:")
            for verb, plugins in sorted(verbs.items()):
                # Show verb and its aliases
                print(f"  {verb:12} (plugins: {', '.join(plugins)})")
        else:
            print("No plugins loaded")
        sys.exit(EXIT_SUCCESS)

    # Need a command - args.command is always a list from nargs="*"
    if not args.command:
        parser.print_help()
        sys.exit(EXIT_ERROR)

    # Join command parts
    command = " ".join(args.command)

    # Capture context
    context = capture_context()

    # Execute command through router
    result = router.execute(command, context)

    # Check for errors from router
    if result.startswith("Error:") or result.startswith("Unknown command:"):
        print(result, file=sys.stderr)
        sys.exit(EXIT_COMMAND_NOT_FOUND if result.startswith("Unknown") else EXIT_ERROR)

    # Execute the actual shell command
    exit_code = execute_command(result, args.dry_run)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
