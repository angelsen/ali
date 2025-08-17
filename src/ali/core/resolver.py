"""Command Resolver - Pure template substitution.

Services are template fragments.
Commands compose templates.
No complex logic, just string substitution.
"""

from typing import Dict, Any
from .plugin import Plugin
from .registry import ServiceRegistry


def resolve_command(
    state: Dict[str, Any],
    plugin: Plugin,
    command: Dict[str, Any],
    registry: ServiceRegistry,
) -> str:
    """Resolve command through template substitution.

    1. Collect service templates
    2. Create context from services + state
    3. Substitute all {key} with context[key]
    4. Return final command
    """
    # Get the command template
    template = command.get("exec", "")
    if not template:
        return "Error: No exec defined"

    # Collect all available service templates
    services = collect_service_templates(registry)

    # Create substitution context: services + state
    context = {**services, **state}

    # Simple substitution
    return substitute(template, context)


def collect_service_templates(registry: ServiceRegistry) -> Dict[str, str]:
    """Collect all service templates from all plugins.

    Services are just named template strings.
    """
    templates = {}

    for plugin in registry.plugins:
        # Get services from plugin
        plugin_services = plugin.config.get("services", {})

        for service_name, service_def in plugin_services.items():
            if isinstance(service_def, str):
                # Simple string template
                templates[service_name] = service_def
            elif isinstance(service_def, dict):
                # Dict with 'template' key
                template = service_def.get("template", "")
                if template:
                    templates[service_name] = template

    return templates


def substitute(template: str, context: Dict[str, Any]) -> str:
    """Two-pass template substitution for template composition.

    First pass: Replace {key} with context[key] values
    Second pass: Replace any new {template} patterns created

    This enables template composition like {split_{direction}}
    where direction="left" creates {split_left} which then
    resolves to "tmux split-window -h -b"
    """

    def _single_pass(text: str, ctx: Dict[str, Any]) -> str:
        """Perform a single substitution pass."""
        result = text
        while "{" in result:
            # Find the innermost template to substitute
            import re

            match = re.search(r"\{([^{}]+)\}", result)
            if not match:
                break

            full_match = match.group(0)  # The entire {key}
            key = match.group(1)  # Just the key

            # Check for default value: {key|default}
            if "|" in key:
                key, default = key.split("|", 1)
                key = key.strip()
                value = ctx.get(key, default)
            else:
                value = ctx.get(key, "")

            # Replace this specific match
            result = result.replace(full_match, str(value) if value else "", 1)

        return result

    # First pass - resolve variables
    result = _single_pass(template, context)

    # Second pass - resolve any new templates created
    # Only do second pass if there are still templates to resolve
    if "{" in result and "}" in result:
        result = _single_pass(result, context)

    return result.strip()
