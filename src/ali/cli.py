#!/usr/bin/env python3
"""ALI CLI - Main entry point."""

import sys
import argparse
from pathlib import Path

from .core import ServiceRegistry, Router
from .executor import execute_command
from .scripts import execute_script

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_COMMAND_NOT_FOUND = 127

# Version
ALI_VERSION = "2.0.0"


def find_plugins_dir() -> Path:
    """Find the plugins directory."""
    # Look in package first
    package_dir = Path(__file__).parent / "plugins"
    if package_dir.exists():
        return package_dir

    # Look in user config
    user_plugins = Path.home() / ".config" / "ali" / "plugins"
    if user_plugins.exists():
        return user_plugins

    return package_dir


def main():
    """Main CLI entry point."""
    # Early check for --plugin-script to handle specially
    if "--plugin-script" in sys.argv:
        exit_code = execute_script(sys.argv)
        sys.exit(exit_code)

    parser = argparse.ArgumentParser(
        description="ALI - Action Language Interpreter",
        epilog="Examples:\n"
        "  ali 'GO .2'           # Go to pane 2\n"
        "  ali 'SPLIT left'      # Split pane left\n"
        "  ali 'WIDTH 012'       # Distribute panes evenly\n"
        "  ali 'WIDTH 012 AS 1/2'# Make panes half window width\n"
        "  ali 'EDIT @?'         # Edit with file selector\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ALI {ALI_VERSION}",
        help="Show version and exit",
    )

    parser.add_argument(
        "--list-verbs",
        action="store_true",
        help="List all available verbs",
    )

    parser.add_argument(
        "--list-services",
        action="store_true",
        help="List all available services",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )

    parser.add_argument(
        "--plugins-dir",
        type=Path,
        help="Directory containing plugin definitions",
    )

    parser.add_argument(
        "command",
        nargs="*",
        help="ALI command to execute",
    )

    args = parser.parse_args()

    # Initialize registry and load plugins
    registry = ServiceRegistry()
    plugins_dir = args.plugins_dir or find_plugins_dir()

    if not plugins_dir.exists():
        print(f"Error: Plugins directory not found: {plugins_dir}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    registry.load_plugins(plugins_dir)

    # Handle --list-services
    if args.list_services:
        print("Available services:")
        for service, providers in sorted(registry.providers.items()):
            provider_names = [p.name for p in providers]
            print(f"  {service:20} provided by: {', '.join(provider_names)}")
        sys.exit(EXIT_SUCCESS)

    # Handle --list-verbs
    if args.list_verbs:
        if registry.verb_index:
            print("Available verbs:")
            for verb, plugin in sorted(registry.verb_index.items()):
                print(f"  {verb:12} ({plugin.name})")
        else:
            print("No verbs available (no plugins loaded)")
        sys.exit(EXIT_SUCCESS)

    # Need a command
    if not args.command:
        parser.print_help()
        sys.exit(EXIT_ERROR)

    # Join command parts
    command_str = " ".join(args.command)

    # Create router and execute
    router = Router(registry)
    result = router.execute(command_str)

    # Check for errors
    if result.startswith("Error:") or result.startswith("Unknown"):
        print(result, file=sys.stderr)
        exit_code = (
            EXIT_COMMAND_NOT_FOUND if result.startswith("Unknown") else EXIT_ERROR
        )
        sys.exit(exit_code)

    # Execute the resolved command
    exit_code = execute_command(result, execute=not args.dry_run)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
