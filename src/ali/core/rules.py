"""Unified rules engine for ALI - processes all parsing, inference, validation, and expansion."""

import re
import os
import subprocess
import importlib
from typing import List, Optional, Dict, Any


class RulesEngine:
    """Executes all types of rules defined in plugin YAML."""

    def process(self, cmd: dict, config: dict) -> str:
        """Process command through all rule stages."""
        # Initialize state with verb and tokens
        state = {"verb": cmd["verb"], "context": cmd.get("context", {})}

        # Stage 1: Parse tokens into fields
        state = self.parse_tokens(cmd.get("tokens", []), state, config)

        # Stage 2: Apply inference rules
        state = self.apply_inference(state, config.get("inference", {}))

        # Stage 3: Apply transformations
        state = self.apply_transformations(state, config.get("transformations", {}))

        # Stage 4: Validate
        error = self.validate(state, config.get("validation", {}))
        if error:
            return f"Error: {error}"

        # Stage 5: Match and execute command (expansions happen INSIDE)
        return self.execute_command(state, config)

    def parse_tokens(self, tokens: List[str], state: dict, config: dict) -> dict:
        """Parse tokens using rules from config."""
        # Get parsing config
        parsing = config.get("parsing", {})

        # If no parsing rules, use simple legacy approach
        if not parsing:
            return self._legacy_parse(tokens, state, config)

        # Get token rules
        token_rules = parsing.get("token_rules", [])

        # Get vocabulary for matching
        vocabulary = config.get("vocabulary", {})
        objects = set(vocabulary.get("objects", []))
        directions = set(vocabulary.get("directions", []))
        clauses = set(vocabulary.get("clauses", []))
        target_patterns = vocabulary.get("target_patterns", [])

        # Process each token
        i = 0
        while i < len(tokens):
            token = tokens[i]
            token_upper = token.upper()
            token_lower = token.lower()

            # Apply token rules
            matched = False
            for rule in token_rules:
                if self._match_token_rule(
                    rule,
                    i,
                    token,
                    token_upper,
                    token_lower,
                    objects,
                    directions,
                    clauses,
                    target_patterns,
                ):
                    matched = True
                    action = rule.get("action")

                    if action == "set":
                        field = rule["field"]
                        transform = rule.get("transform")
                        value = self._apply_transform(token, transform)
                        state[field] = value

                    elif action == "accumulate":
                        field = rule["field"]
                        if field not in state:
                            state[field] = []
                        state[field].append(token)

                    elif action == "consume_next":
                        if i + 1 < len(tokens):
                            field = rule.get("field", token_lower)
                            field = field.replace("{token_lower}", token_lower)
                            state[field] = tokens[i + 1]
                            i += 1  # Skip next token

                    break

            # If no rule matched, add to args
            if not matched:
                if "args" not in state:
                    state["args"] = []
                state["args"].append(token)

            i += 1

        return state

    def _match_token_rule(
        self,
        rule,
        position,
        token,
        token_upper,
        token_lower,
        objects,
        directions,
        clauses,
        target_patterns,
    ):
        """Check if a token rule matches."""
        match = rule.get("match", {})

        # Check position
        if "position" in match and position != match["position"]:
            return False

        # Check if in set
        if "in_set" in match:
            set_name = match["in_set"]
            if set_name == "objects" and token_upper not in objects:
                return False
            elif set_name == "directions" and token_lower not in directions:
                return False
            elif set_name == "clauses" and token_upper not in clauses:
                return False

        # Check if matches pattern
        if "matches_patterns" in match and match["matches_patterns"]:
            if not self._matches_any_pattern(token, target_patterns):
                return False

        # Check regex
        if "regex" in match:
            if not re.match(match["regex"], token):
                return False

        # Default/else rule
        if match.get("else"):
            return True

        # If we got here and have at least one condition, it matched
        return len(match) > 0

    def _matches_any_pattern(self, token, patterns):
        """Check if token matches any pattern."""
        for pattern in patterns:
            if isinstance(pattern, str):
                if token == pattern:
                    return True
            elif isinstance(pattern, dict):
                regex = pattern.get("regex")
                if regex and re.match(regex, token):
                    return True
        return False

    def _apply_transform(self, value, transform):
        """Apply transformation to a value."""
        if not transform:
            return value
        if transform == "upper":
            return value.upper()
        elif transform == "lower":
            return value.lower()
        return value

    def _legacy_parse(self, tokens, state, config):
        """Legacy parsing for backwards compatibility."""
        # Simple approach: first token might be object, rest are targets/args
        vocabulary = config.get("vocabulary", {})
        objects = set(vocabulary.get("objects", []))

        for i, token in enumerate(tokens):
            if i == 0 and token.upper() in objects:
                state["object"] = token.upper()
            else:
                if "target" not in state:
                    state["target"] = token
                else:
                    if "args" not in state:
                        state["args"] = []
                    state["args"].append(token)

        return state

    def apply_inference(self, state: dict, inference_config: dict) -> dict:
        """Apply inference rules to deduce missing fields."""
        rules = inference_config.get("rules", [])

        for rule in rules:
            when = rule.get("when", {})

            # Check if rule conditions match
            if self._matches_conditions(state, when):
                # Apply the rule
                if "set" in rule:
                    for field, value in rule["set"].items():
                        state[field] = value

                if "transform" in rule:
                    for field, value in rule["transform"].items():
                        if field in state:
                            state[field] = value

        return state

    def _matches_conditions(self, state, conditions):
        """Check if state matches all conditions."""
        for field, expected in conditions.items():
            actual = state.get(field)

            # Handle special "else" condition (matches anything)
            if field == "else" and expected is True:
                continue  # else condition always matches

            # Handle "present" condition (field must exist and not be None)
            elif expected == "present":
                if field not in state or state[field] is None:
                    return False

            # Handle "absent" condition (field must not exist or be None)
            elif expected == "absent":
                if field in state and state[field] is not None:
                    return False

            # Handle regex patterns
            elif isinstance(expected, str) and expected.startswith("^"):
                if not actual or not re.match(expected, actual):
                    return False

            # Handle None/null checks
            elif expected is None:
                if actual is not None:
                    return False

            # Direct comparison
            else:
                if actual != expected:
                    return False

        return True

    def apply_transformations(self, state: dict, transform_config: dict) -> dict:
        """Apply field transformations."""
        # Handle field aliases
        aliases = transform_config.get("field_aliases", {})
        for old_field, new_field in aliases.items():
            if old_field in state and new_field not in state:
                state[new_field] = state[old_field]

        # Handle field transformations (e.g., .THIS -> "")
        transformations = transform_config.get("field_transformations", {})
        for field, transforms in transformations.items():
            if field in state and state[field] in transforms:
                state[field] = transforms[state[field]]

        return state

    def validate(self, state: dict, validation_config: dict) -> Optional[str]:
        """Validate the command state."""
        # Check allowed parameters
        allowed_params = validation_config.get("allowed_params", {})
        verb = state.get("verb", "")
        obj = state.get("object", "")
        command_key = f"{verb} {obj}" if obj else verb

        if command_key in allowed_params:
            allowed = set(allowed_params[command_key])
            # Always allow these standard fields
            allowed.update(["verb", "object", "context", "args"])

            for param in state.keys():
                if param not in allowed:
                    return f"'{command_key}' doesn't accept parameter '{param}'"

        # Check allowed directions
        allowed_dirs = validation_config.get("allowed_directions", {})
        if allowed_dirs and state.get("direction"):
            direction = state.get("direction")
            if obj in allowed_dirs:
                allowed = allowed_dirs[obj]
                if direction not in allowed:
                    return f"{obj} does not support direction '{direction}'. Allowed: {', '.join(allowed)}"

        return None

    def expand_fields(
        self, state: dict, expansions: dict, config: dict | None = None
    ) -> dict:
        """Expand fields using expansion rules."""
        for field_name, rule in expansions.items():
            rule_type = rule.get("type", "map")

            if rule_type == "map":
                state[field_name] = self._expand_map(state, rule)
            elif rule_type == "format":
                state[field_name] = self._expand_format(state, rule)
            elif rule_type == "env":
                state[field_name] = self._expand_env(rule)
            elif rule_type == "command":
                state[field_name] = self._expand_command(rule)
            elif rule_type == "plugin" and config:
                state[field_name] = self._expand_plugin(state, rule, config)

        return state

    def _expand_map(self, state: dict, rule: dict) -> str:
        """Map field value using lookup table."""
        field = rule.get("field")
        value = state.get(field)

        if not value:
            return rule.get("default", "")

        mappings = rule.get("mappings", {})
        obj = state.get("object")

        # Try object-specific mapping first
        if obj and obj in mappings:
            return mappings[obj].get(value, rule.get("default", ""))

        # Try direct mapping
        return mappings.get(value, rule.get("default", ""))

    def _expand_format(self, state: dict, rule: dict) -> str:
        """Format string with state fields."""
        template = rule.get("template", "")

        # Check if required fields are present and non-empty
        import re

        fields = re.findall(r"\{(\w+)\}", template)
        for field in fields:
            if field not in state or not state[field]:
                return rule.get("default", "")

        try:
            return template.format(**state)
        except KeyError:
            return rule.get("default", "")

    def _expand_env(self, rule: dict) -> str:
        """Get value from environment variable."""
        var = rule.get("var")
        if not var:
            return rule.get("default", "")
        return os.environ.get(var, rule.get("default", ""))

    def _expand_command(self, rule: dict) -> str:
        """Execute command and return output."""
        cmd = rule.get("cmd")
        if not cmd:
            return rule.get("default", "")
        try:
            result = subprocess.check_output(cmd, shell=True, text=True)
            return result.strip()
        except subprocess.SubprocessError:
            return rule.get("default", "")

    def _expand_plugin(
        self, state: Dict[str, Any], rule: Dict[str, Any], config: Dict[str, Any]
    ) -> str:
        """Call plugin-specific expansion function."""
        plugin_name = config.get("name", "unknown")
        function_name = rule.get("function")

        if not function_name:
            return rule.get("default", "")

        try:
            # Import plugin module
            module = importlib.import_module(f"ali.plugins.{plugin_name}.plugin")
            func = getattr(module, function_name)
            return func(state)
        except (ImportError, AttributeError) as e:
            print(
                f"Warning: Plugin function {plugin_name}.{function_name} not found: {e}"
            )
            return rule.get("default", "")

    def execute_command(self, state: dict, config: dict) -> str:
        """Match state against commands and execute."""
        commands = config.get("commands", [])
        expansions = config.get("expansions", {})

        for i, command in enumerate(commands):
            match = command.get("match", {})

            # Check if all match criteria are met
            if self._matches_conditions(state, match):
                # Check if this is a plugin command
                if command.get("type") == "plugin":
                    function_name = command.get("function")
                    if function_name:
                        plugin_name = config.get("name", "unknown")
                        try:
                            # Import plugin module
                            module = importlib.import_module(
                                f"ali.plugins.{plugin_name}.plugin"
                            )
                            func = getattr(module, function_name)
                            result = func(state)
                            if result:
                                return result
                        except (ImportError, AttributeError) as e:
                            print(
                                f"Warning: Plugin function {plugin_name}.{function_name} not found: {e}"
                            )
                    continue

                # Regular template-based command
                template = command.get("exec", "")

                # Apply expansions AFTER matching
                expanded_state = self.expand_fields(state.copy(), expansions, config)

                # Fill template with expanded state values
                try:
                    # Use a defaultdict that returns empty string for missing keys
                    from collections import defaultdict

                    safe_state = defaultdict(str, expanded_state)
                    result = template.format_map(safe_state)
                    return result
                except Exception as e:
                    return f"Error executing template: {e}"

        # No matching command found
        verb = state.get("verb", "")
        obj = state.get("object", "")
        return f"No command found for {verb} {obj}"
