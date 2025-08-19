"""Command Router - Parses commands and orchestrates resolution."""

import shlex
import re
from typing import Dict, Any, Optional, List
from .plugin import Plugin
from .registry import ServiceRegistry
from .resolver import resolve_command, collect_selectors, expand_selectors


class Router:
    """Routes commands to plugins and resolves them."""

    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.last_tokens = None
        self.last_state = None

    def execute(self, command_str: str) -> str:
        """Parse and execute command string.

        Args:
            command_str: Raw command string to execute

        Returns:
            Command result or error message
        """
        try:
            tokens = shlex.split(command_str)
        except ValueError as e:
            self.last_tokens = None
            self.last_state = None
            return f"Error: Parse error: {e}"

        if not tokens:
            self.last_tokens = []
            self.last_state = None
            return "Error: Empty command"

        self.last_tokens = tokens
        verb = tokens[0].upper()
        plugins = self.registry.get_plugins_for_verb(verb)
        if not plugins:
            self.last_state = {"verb": verb}
            available = list(self.registry.verb_index.keys())
            if available:
                return (
                    f"Unknown verb: {verb}. Available: {', '.join(sorted(available))}"
                )
            return f"Unknown verb: {verb}. No plugins loaded."

        plugin = plugins[0]

        selectors = collect_selectors(self.registry)

        state = self._parse(verb, tokens[1:], plugin, selectors)
        self.last_state = state

        if "_parse_error" in state:
            return f"Error: {state['_parse_error']}"

        state = self._apply_inference(state, plugin)

        state = expand_selectors(state, selectors, self.registry)

        command = self._find_command(state, plugin)
        if not command:
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

        return resolve_command(state, plugin, command, self.registry)

    def _parse(
        self,
        verb: str,
        tokens: List[str],
        plugin: Plugin,
        selectors: Dict[str, Dict[str, str]],
    ) -> Dict[str, Any]:
        """Parse command tokens into state dictionary.

        Args:
            verb: Command verb
            tokens: Remaining tokens after verb
            plugin: Plugin handling the command
            selectors: Available selectors from all plugins

        Returns:
            State dictionary with parsed values
        """
        state: Dict[str, Any] = {"verb": verb}

        expectations = plugin.expectations.get(verb, [])
        if not expectations:
            if tokens:
                state["args"] = tokens
            return state

        parsed_expectations = self._parse_expectations(expectations)

        token_index = 0
        for exp in parsed_expectations:
            field_name = exp["field"]
            optional = exp.get("optional", False)
            default = exp.get("default")

            if token_index >= len(tokens):
                if default is not None:
                    state[field_name] = default
                elif not optional:
                    pass
                continue

            token = tokens[token_index]

            parsed_value = self._match_grammar(token, field_name, plugin)

            if parsed_value is None and field_name not in plugin.grammar:
                for other_plugin in self.registry.plugins:
                    if other_plugin != plugin and field_name in other_plugin.grammar:
                        parsed_value = self._match_grammar(
                            token, field_name, other_plugin
                        )
                        if parsed_value is not None:
                            break

            if parsed_value is None and token in selectors:
                parsed_value = token

            if parsed_value is not None:
                state[field_name] = parsed_value
                token_index += 1

        for exp in parsed_expectations:
            field_name = exp["field"]
            if field_name not in state and exp.get("default") is not None:
                state[field_name] = exp["default"]

        if token_index < len(tokens):
            leftover = tokens[token_index:]
            state["_parse_error"] = f"Unexpected tokens: {' '.join(leftover)}"

        return state

    def _match_grammar(
        self, token: str, field_name: str, plugin: Plugin
    ) -> Optional[Any]:
        """Match token against plugin grammar for field.

        Args:
            token: Token to match
            field_name: Field name to match against
            plugin: Plugin containing grammar rules

        Returns:
            Matched and transformed value or None
        """
        if field_name not in plugin.grammar:
            return None

        grammar = plugin.grammar[field_name]

        if "pattern" in grammar:
            if re.match(grammar["pattern"], token):
                if "transform" in grammar:
                    transform = grammar["transform"]
                    if transform == "lower":
                        return token.lower()
                    elif transform == "upper":
                        return token.upper()
                return token
            return None

        if "values" in grammar:
            values = grammar["values"]
            case_sensitive = grammar.get("case_sensitive", False)

            if case_sensitive:
                if token in values:
                    return token
            else:
                token_lower = token.lower()
                for value in values:
                    if token_lower == value.lower():
                        if "transform" in grammar:
                            if grammar["transform"] == "lower":
                                return token.lower()
                            elif grammar["transform"] == "upper":
                                return token.upper()
                            elif grammar["transform"] == "original":
                                return value
                        return token
            return None

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

        return None

    def _parse_expectations(self, expectations):
        """Parse expectations into normalized format."""
        result = []
        for exp in expectations:
            if isinstance(exp, str):
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
                result.append(exp)
        return result

    def _apply_inference(self, state: Dict[str, Any], plugin: Plugin) -> Dict[str, Any]:
        """Apply plugin inference rules to transform state."""
        for rule in plugin.inference:
            when = rule.get("when", {})

            if self._matches_conditions(state, when):
                if "transform" in rule:
                    for field, value in rule["transform"].items():
                        if field in state:
                            state[field] = value

                if "set" in rule:
                    for field, value in rule["set"].items():
                        state[field] = value

        return state

    def _matches_conditions(self, state: Dict, conditions: Dict) -> bool:
        """Check if state matches all conditions."""
        for key, expected in conditions.items():
            actual = state.get(key)

            if expected == "present":
                if key not in state or not state[key]:
                    return False
            elif expected is None or expected == "null":
                if actual is not None:
                    return False
            elif isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, str) and expected.startswith("^"):
                if actual is None or not re.match(expected, str(actual)):
                    return False
            else:
                if actual != expected:
                    return False

        return True

    def _find_command(self, state: Dict[str, Any], plugin: Plugin) -> Optional[Dict]:
        """Find command template matching current state."""
        for command in plugin.commands:
            match = command.get("match", {})
            if self._matches_conditions(state, match):
                return command
        return None
