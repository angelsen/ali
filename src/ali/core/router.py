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

        # Check for parse errors
        if "_parse_error" in state:
            return f"Error: {state['_parse_error']}"

        # Apply plugin's inference rules
        state = self._apply_inference(state, plugin)

        # Find matching command in plugin
        command = self._find_command(state, plugin)
        if not command:
            # Provide helpful error about what's missing
            expectations = plugin.expectations.get(verb, [])
            if expectations:
                parsed_exp = self._parse_expectations(expectations)
                required = [
                    e["field"] for e in parsed_exp if not e.get("optional", False)
                ]
                missing = [f for f in required if f not in state]
                if missing:
                    return f"Error: {verb} requires: {', '.join(missing)}"
            return f"No matching command for: {command_str}"

        # Resolve to executable command
        return resolve_command(state, plugin, command, self.registry)

    def _parse(self, verb: str, tokens: List[str], plugin: Plugin) -> Dict[str, Any]:
        """Parse tokens according to plugin's expectations and grammar."""
        state: Dict[str, Any] = {"verb": verb}

        # Get expectations for this verb
        expectations = plugin.expectations.get(verb, [])
        if not expectations:
            # No expectations, just store tokens as args
            if tokens:
                state["args"] = tokens
            return state

        # Parse expectations (handle dict or list format)
        parsed_expectations = self._parse_expectations(expectations)

        token_index = 0
        for exp in parsed_expectations:
            field_name = exp["field"]
            optional = exp.get("optional", False)
            default = exp.get("default")

            # No more tokens
            if token_index >= len(tokens):
                # Apply default if available
                if default is not None:
                    state[field_name] = default
                elif not optional:
                    # Required field missing, but continue anyway
                    pass
                continue

            token = tokens[token_index]

            # Try to match token against field's grammar type
            parsed_value = self._match_grammar(token, field_name, plugin)
            if parsed_value is not None:
                state[field_name] = parsed_value
                token_index += 1
            elif optional and field_name in plugin.grammar:
                # Optional field with grammar - if token doesn't match, don't consume it
                # It might be for the next field
                pass
            elif not optional:
                # Required field but grammar didn't match - don't consume token
                pass

        # Apply defaults for missing optional fields
        for exp in parsed_expectations:
            field_name = exp["field"]
            if field_name not in state and exp.get("default") is not None:
                state[field_name] = exp["default"]

        # Check for leftover tokens - this indicates invalid input
        if token_index < len(tokens):
            leftover = tokens[token_index:]
            state["_parse_error"] = f"Unexpected tokens: {' '.join(leftover)}"

        return state

    def _match_grammar(
        self, token: str, field_name: str, plugin: Plugin
    ) -> Optional[Any]:
        """Match a token against the grammar definition for a field.

        Returns parsed value if match, None otherwise.
        """
        # Check if field has a grammar definition
        if field_name not in plugin.grammar:
            # No grammar defined - field must define its grammar
            return None

        grammar = plugin.grammar[field_name]

        # Pattern matching (regex)
        if "pattern" in grammar:
            if re.match(grammar["pattern"], token):
                # Apply transform if specified
                if "transform" in grammar:
                    transform = grammar["transform"]
                    if transform == "lower":
                        return token.lower()
                    elif transform == "upper":
                        return token.upper()
                return token
            return None

        # Enumeration matching (list of valid values)
        if "values" in grammar:
            values = grammar["values"]
            case_sensitive = grammar.get("case_sensitive", False)

            if case_sensitive:
                if token in values:
                    return token
            else:
                # Case-insensitive matching
                token_lower = token.lower()
                for value in values:
                    if token_lower == value.lower():
                        # Return in the case specified by grammar
                        if "transform" in grammar:
                            if grammar["transform"] == "lower":
                                return token.lower()
                            elif grammar["transform"] == "upper":
                                return token.upper()
                            elif grammar["transform"] == "original":
                                return value  # Use the case from values list
                        return token
            return None

        # Type checking
        if "type" in grammar:
            type_name = grammar["type"]
            if type_name == "integer":
                try:
                    return int(token)
                except ValueError:
                    return None
            elif type_name == "float":
                try:
                    return float(token)
                except ValueError:
                    return None
            elif type_name == "string":
                return token

        # No matching rule found
        return None

    def _parse_expectations(self, expectations):
        """Parse expectations into normalized format."""
        result = []
        for exp in expectations:
            if isinstance(exp, str):
                # Simple string format: "field?" or "field?=default"
                if "=" in exp:
                    field_part, default = exp.split("=", 1)
                    field = field_part.rstrip("?")
                    optional = field_part.endswith("?")
                    result.append(
                        {"field": field, "optional": optional, "default": default}
                    )
                else:
                    optional = exp.endswith("?")
                    field = exp.rstrip("?")
                    result.append({"field": field, "optional": optional})
            elif isinstance(exp, dict):
                # Dict format already
                result.append(exp)
        return result

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
            elif isinstance(expected, list):
                # List matching - actual must be in the list
                if actual not in expected:
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
