"""Command Router - Parses commands and orchestrates resolution."""

import shlex
import re
from typing import Dict, Any, Optional, List
from .plugin import Plugin
from .registry import ServiceRegistry
from .resolver import resolve_command


class Router:
    """Routes commands to plugins and resolves them."""

    def __init__(self, registry: ServiceRegistry):
        """Initialize with a service registry."""
        self.registry = registry

    def execute(self, command_str: str) -> str:
        """Parse, route, and resolve a command to executable string.

        This is the main entry point - takes a command string,
        returns an executable command or error.
        """
        # Parse into tokens
        try:
            tokens = shlex.split(command_str)
        except ValueError as e:
            return f"Error: Parse error: {e}"

        if not tokens:
            return "Error: Empty command"

        # First token is the verb
        verb = tokens[0].upper()

        # Find plugin that handles this verb
        plugin = self.registry.get_plugin_for_verb(verb)
        if not plugin:
            available = list(self.registry.verb_index.keys())
            if available:
                return (
                    f"Unknown verb: {verb}. Available: {', '.join(sorted(available))}"
                )
            return f"Unknown verb: {verb}. No plugins loaded."

        # Parse according to plugin's expectations
        state = self._parse(verb, tokens[1:], plugin)

        # Apply plugin's inference rules
        state = self._apply_inference(state, plugin)

        # Find matching command in plugin
        command = self._find_command(state, plugin)
        if not command:
            return f"No matching command for: {command_str}"

        # Resolve to executable command
        return resolve_command(state, plugin, command, self.registry)

    def _parse(self, verb: str, tokens: List[str], plugin: Plugin) -> Dict[str, Any]:
        """Parse tokens according to plugin's expectations."""
        state: Dict[str, Any] = {"verb": verb}

        # Get expectations for this verb
        expectations = plugin.expectations.get(verb, [])
        if not expectations:
            # No expectations, just store tokens as args
            if tokens:
                state["args"] = tokens
            return state

        token_index = 0
        for expectation in expectations:
            # Check if optional (ends with ?)
            optional = expectation.endswith("?")
            field_name = expectation.rstrip("?")

            # No more tokens
            if token_index >= len(tokens):
                if not optional:
                    # Required field missing, but continue anyway
                    pass
                break

            token = tokens[token_index]

            # Check if token matches any plugin patterns
            matched_field = self._match_pattern(token, plugin)
            if matched_field:
                state[matched_field] = token
                token_index += 1
                continue

            # Parse based on field type
            if field_name == "object":
                if token.upper() in plugin.objects:
                    state["object"] = token.upper()
                    token_index += 1
                elif not optional:
                    # Take it anyway
                    state["object"] = token.upper()
                    token_index += 1

            elif field_name == "direction":
                if token.lower() in plugin.directions:
                    state["direction"] = token.lower()
                    token_index += 1

            else:
                # Generic field, just store the token
                state[field_name] = token
                token_index += 1

        # Any remaining tokens become args
        if token_index < len(tokens):
            state["args"] = tokens[token_index:]

        return state

    def _match_pattern(self, token: str, plugin: Plugin) -> Optional[str]:
        """Check if token matches any of plugin's patterns."""
        for pattern in plugin.patterns:
            field = pattern.get("field")

            # Check regex
            if "regex" in pattern:
                if re.match(pattern["regex"], token):
                    return field

            # Check keywords
            if "keywords" in pattern:
                if token in pattern["keywords"]:
                    return field

        return None

    def _apply_inference(self, state: Dict[str, Any], plugin: Plugin) -> Dict[str, Any]:
        """Apply plugin's inference rules."""
        for rule in plugin.inference:
            when = rule.get("when", {})

            # Check if rule conditions match
            if self._matches_conditions(state, when):
                # Apply transformations
                if "transform" in rule:
                    for field, value in rule["transform"].items():
                        if field in state:
                            state[field] = value

                # Set new fields
                if "set" in rule:
                    for field, value in rule["set"].items():
                        state[field] = value

        return state

    def _matches_conditions(self, state: Dict, conditions: Dict) -> bool:
        """Check if state matches rule conditions."""
        for key, expected in conditions.items():
            actual = state.get(key)

            # Special checks
            if expected == "present":
                if key not in state or not state[key]:
                    return False
            elif expected is None or expected == "null":
                if actual is not None:
                    return False
            elif isinstance(expected, str) and expected.startswith("^"):
                # Regex pattern
                if actual is None or not re.match(expected, str(actual)):
                    return False
            else:
                # Direct comparison
                if actual != expected:
                    return False

        return True

    def _find_command(self, state: Dict[str, Any], plugin: Plugin) -> Optional[Dict]:
        """Find matching command in plugin."""
        for command in plugin.commands:
            match = command.get("match", {})
            if self._matches_conditions(state, match):
                return command
        return None
