"""Script executor - Simple pass-through to plugin scripts."""

import sys
import subprocess
from pathlib import Path
from typing import List, Optional


def execute_script(argv: List[str]) -> int:
    """Execute a plugin script.

    Expected format: ali --plugin-script tmux.distribute --dimension width --panes 012

    Args:
        argv: Command line arguments

    Returns:
        Exit code
    """
    try:
        # Find --plugin-script position
        script_idx = argv.index("--plugin-script")
        if script_idx + 1 >= len(argv):
            print(
                "Error: --plugin-script requires plugin.script argument",
                file=sys.stderr,
            )
            return 1

        # Parse plugin.script notation
        plugin_script = argv[script_idx + 1]
        if "." not in plugin_script:
            print(
                f"Error: Expected plugin.script format, got: {plugin_script}",
                file=sys.stderr,
            )
            return 1

        plugin_name, script_name = plugin_script.split(".", 1)

        # Remaining args go to the script
        script_args = argv[script_idx + 2 :]

        # Find script file
        script_file = find_script(plugin_name, script_name)
        if not script_file:
            print(
                f"Error: Script '{script_name}' not found in plugin '{plugin_name}'",
                file=sys.stderr,
            )
            return 1

        # Build command based on file type
        if script_file.suffix == ".py":
            cmd = [sys.executable, str(script_file)] + script_args
        else:
            # Let the system figure out how to run it (shebang, etc.)
            cmd = [str(script_file)] + script_args

        # Run and pass through output (stdout goes to stdout, stderr to stderr)
        # This is the default behavior when not capturing output
        result = subprocess.run(cmd)
        return result.returncode

    except ValueError:
        print("Error: --plugin-script not found in arguments", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error executing script: {e}", file=sys.stderr)
        return 1


def find_script(plugin_name: str, script_name: str) -> Optional[Path]:
    """Find a script file in a plugin's scripts directory.

    Resolves script name to actual file:
    - "distribute" → distribute, distribute.py, distribute.sh, etc.
    - "pane.manage" → pane/manage, pane/manage.py, etc.

    Args:
        plugin_name: Name of the plugin (e.g., "tmux")
        script_name: Name of script (e.g., "distribute" or "pane.distribute")

    Returns:
        Path to script file if found, None otherwise
    """
    from . import cli

    plugins_dir = cli.find_plugins_dir()

    # Convert dots to slashes for nested paths
    script_path = script_name.replace(".", "/")
    scripts_dir = plugins_dir / plugin_name / "scripts"

    # Look for files starting with the script name
    script_base = scripts_dir / script_path

    # Try exact match first (no extension)
    if script_base.exists() and script_base.is_file():
        return script_base

    # Find any file matching pattern: script_name*
    # This matches: distribute, distribute.py, distribute.sh, etc.
    if script_base.parent.exists():
        for file in script_base.parent.glob(f"{script_base.name}*"):
            if file.is_file():
                return file

    return None
