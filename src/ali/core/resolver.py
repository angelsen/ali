"""Command Resolver - Builds executable commands from service chains."""

from typing import Dict, Any
from .plugin import Plugin
from .registry import ServiceRegistry


def resolve_command(
    state: Dict[str, Any],
    plugin: Plugin,
    command: Dict[str, Any],
    registry: ServiceRegistry,
) -> str:
    """Resolve a command by building the service chain.

    Args:
        state: Parsed command state (verb, file, target, etc.)
        plugin: The plugin handling this command
        command: The matched command config from plugin
        registry: Service registry for finding providers

    Returns:
        Executable command string
    """
    # Get base command
    exec_template = command.get("exec", "")
    if not exec_template:
        return f"Error: No exec defined for {state.get('verb')}"

    # Check if command needs services
    needs = command.get("needs", [])
    if not needs:
        # Simple command, just format and return
        return _format_command(exec_template, state)

    # Normalize needs to list
    if isinstance(needs, str):
        needs = [needs]

    # Handle special service requests
    if "@?" in state.get("file", ""):
        # File selector requested
        return _resolve_file_selector(state, plugin, command, registry)

    # For now, handle pane service simply
    if "pane" in needs:
        return _resolve_with_pane(exec_template, state, command, registry)

    # Default: just format the command
    return _format_command(exec_template, state)


def _resolve_file_selector(
    state: Dict[str, Any],
    plugin: Plugin,
    command: Dict[str, Any],
    registry: ServiceRegistry,
) -> str:
    """Resolve @? file selector to actual command chain."""
    # Find file_selector provider
    file_selector = registry.get_provider("file_selector")
    if not file_selector:
        return "Error: No file selector available (@? requires file_selector service)"

    # Get the service handler from the provider
    handlers = file_selector.service_handlers.get("file_selector", {})
    interactive = handlers.get("interactive", {})

    if not interactive:
        # Fallback: provider has the service but no handler defined
        # Try the select_and_edit handler for EDIT commands
        if state.get("verb") == "EDIT" and "select_and_edit" in handlers:
            handler = handlers["select_and_edit"]
            return _build_service_command(handler, state, registry)

    # Build command: pane + file selector
    selector_cmd = interactive.get("exec", "br")

    # File selector also needs pane
    if "pane" in file_selector.requires:
        return _resolve_with_pane(selector_cmd, state, interactive, registry)

    return selector_cmd


def _resolve_with_pane(
    exec_template: str,
    state: Dict[str, Any],
    command: Dict[str, Any],
    registry: ServiceRegistry,
) -> str:
    """Wrap a command with pane creation."""
    # Get pane provider (tmux)
    pane_provider = registry.get_provider("pane")
    if not pane_provider:
        # No pane provider, just return the command as-is
        return _format_command(exec_template, state)

    # Get pane hints from command
    hints = command.get("pane_hints", {})
    position = hints.get("position", "right")
    size = hints.get("size", "50%")

    # Build tmux command based on position
    if position == "left":
        pane_cmd = f"tmux split-window -h -b -l {size}"
    elif position == "right":
        pane_cmd = f"tmux split-window -h -l {size}"
    elif position == "bottom":
        pane_cmd = f"tmux split-window -v -l {size}"
    else:
        pane_cmd = "tmux split-window -h"

    # Format the inner command
    inner_cmd = _format_command(exec_template, state)

    # Combine
    return f"{pane_cmd} '{inner_cmd}'"


def _build_service_command(
    handler: Dict[str, Any], state: Dict[str, Any], registry: ServiceRegistry
) -> str:
    """Build command from service handler configuration."""
    exec_template = handler.get("exec", "")

    # Check if this handler also needs services
    if "needs" in handler and "pane" in handler["needs"]:
        return _resolve_with_pane(exec_template, state, handler, registry)

    return _format_command(exec_template, state)


def _format_command(template: str, state: Dict[str, Any]) -> str:
    """Format command template with state values."""
    # Simple string formatting
    result = template

    # Replace {key} with state[key]
    import re

    def replacer(match):
        key = match.group(1)
        value = state.get(key, "")
        return str(value) if value else ""

    result = re.sub(r"\{(\w+)\}", replacer, result)

    # Special handling for @?
    if "@?" in result:
        # This shouldn't happen if resolution worked
        result = result.replace("@?", "")

    return result
