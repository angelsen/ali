#!/usr/bin/env python3
"""ALI CLI - Main entry point."""

import sys
import os
import argparse
from pathlib import Path

from .core import ServiceRegistry, Router
from .core.logging import ALILogger
from .scripts import execute_script

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_COMMAND_NOT_FOUND = 127

ALI_VERSION = "2.0.0"


def find_plugins_dir() -> Path:
    """Find plugins directory in package or user config."""
    package_dir = Path(__file__).parent / "plugins"
    if package_dir.exists():
        return package_dir

    user_plugins = Path.home() / ".config" / "ali" / "plugins"
    if user_plugins.exists():
        return user_plugins

    return package_dir


def main():
    """Main CLI entry point."""
    if "--plugin-script" in sys.argv:
        exit_code = execute_script(sys.argv)
        sys.exit(exit_code)

    parser = argparse.ArgumentParser(
        description="ALI - Action Language Interpreter",
        epilog="Examples:\n"
        "  ali GO .2             # Go to pane 2\n"
        "  ali SPLIT pop         # Open popup shell\n"
        "  ali EDIT file.txt pop # Edit in popup\n"
        "  ali WIDTH 012         # Distribute panes evenly\n"
        "  ali ECHO ed?          # Edit and pipe output\n",
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
        "--list-grammar",
        action="store_true",
        help="List grammar definitions for all plugins",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging to stderr",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Disable all logging",
    )

    parser.add_argument(
        "--plugins-dir",
        type=Path,
        help="Directory containing plugin definitions",
    )

    parser.add_argument(
        "--init",
        metavar="PLUGIN",
        help="Initialize plugin integration (e.g., --init tmux)",
    )

    parser.add_argument(
        "command",
        nargs="*",
        help="ALI command to execute",
    )

    args = parser.parse_args()

    log_level = os.environ.get("ALI_LOG_LEVEL", "")
    if args.quiet:
        logger = None
    elif args.verbose or log_level.upper() in ["DEBUG", "VERBOSE"]:
        logger = ALILogger(verbose=True)
    else:
        logger = ALILogger(verbose=False)

    registry = ServiceRegistry(logger=logger)
    plugins_dir = args.plugins_dir or find_plugins_dir()

    if not plugins_dir.exists():
        print(f"Error: Plugins directory not found: {plugins_dir}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    registry.load_plugins(plugins_dir)

    if logger:
        logger.registry = registry

    if args.init:
        found = False
        for plugin in registry.plugins:
            if plugin.name == args.init:
                found = True
                exit_code = plugin.init()
                sys.exit(exit_code if exit_code == 0 else EXIT_ERROR)
        if not found:
            print(f"Error: Plugin '{args.init}' not found", file=sys.stderr)
            print(
                f"Available plugins: {', '.join(p.name for p in registry.plugins)}",
                file=sys.stderr,
            )
            sys.exit(EXIT_ERROR)

    if args.list_services:
        print("Available services:", file=sys.stderr)
        for service, providers in sorted(registry.providers.items()):
            provider_names = [p.name for p in providers]
            print(
                f"  {service:20} provided by: {', '.join(provider_names)}",
                file=sys.stderr,
            )
        sys.exit(EXIT_SUCCESS)

    if args.list_grammar:
        print("Grammar definitions by plugin:", file=sys.stderr)
        for plugin in registry.plugins:
            if plugin.grammar:
                print(f"\n{plugin.name}:", file=sys.stderr)
                for field, grammar in plugin.grammar.items():
                    if "pattern" in grammar:
                        pattern = grammar["pattern"]
                        if len(pattern) > 40:
                            pattern = pattern[:40] + "..."
                        print(f"  {field:15} pattern: {pattern}", file=sys.stderr)
                    elif "values" in grammar:
                        values_str = ", ".join(grammar["values"][:3])
                        if len(grammar["values"]) > 3:
                            values_str += "..."
                        print(f"  {field:15} values: [{values_str}]", file=sys.stderr)
                    elif "type" in grammar:
                        print(f"  {field:15} type: {grammar['type']}", file=sys.stderr)
        sys.exit(EXIT_SUCCESS)

    if args.list_verbs:
        if registry.verb_index:
            print("Available verbs:", file=sys.stderr)
            for verb, plugin_list in sorted(registry.verb_index.items()):
                if plugin_list:
                    plugin_names = ", ".join(p.name for p in plugin_list)
                    print(f"  {verb:12} ({plugin_names})", file=sys.stderr)
        else:
            print("No verbs available (no plugins loaded)", file=sys.stderr)
        sys.exit(EXIT_SUCCESS)

    if not args.command:
        parser.print_help()
        sys.exit(EXIT_ERROR)

    command_str = " ".join(args.command)

    router = Router(registry)
    result = router.execute(command_str)

    if logger:
        tokens = router.last_tokens if hasattr(router, "last_tokens") else None
        state = router.last_state if hasattr(router, "last_state") else None
        success = not (result.startswith("Error:") or result.startswith("Unknown"))
        logger.log_command(
            command_str,
            tokens=tokens,
            state=state,
            result=result if success else None,
            error=result if not success else None,
            success=success,
        )

    if result.startswith("Error:") or result.startswith("Unknown"):
        print(result, file=sys.stderr)
        exit_code = (
            EXIT_COMMAND_NOT_FOUND if result.startswith("Unknown") else EXIT_ERROR
        )
        sys.exit(exit_code)

    print(result)
    sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
