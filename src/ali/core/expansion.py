"""Expansion engine for transforming parsed commands to CLI arguments."""

import os
import subprocess


class ExpansionEngine:
    """Transform parsed command fields into CLI arguments."""

    def expand(self, cmd: dict, rules: dict) -> dict:
        """
        Apply expansion rules to command fields.

        Args:
            cmd: Parsed command dict with verb, object, direction, etc.
            rules: Expansion rules from plugin config

        Returns:
            Dict of expanded values ready for template substitution
        """
        result = {}

        for rule_name, rule in rules.items():
            rule_type = rule.get("type", "map")

            if rule_type == "map":
                result[rule_name] = self._expand_map(cmd, rule)
            elif rule_type == "env":
                result[rule_name] = self._expand_env(rule)
            elif rule_type == "command":
                result[rule_name] = self._expand_command(rule)
            elif rule_type == "format":
                result[rule_name] = self._expand_format(cmd, rule)

        return result

    def _expand_map(self, cmd: dict, rule: dict) -> str:
        """Map field value to output using lookup table."""
        field = rule.get("field")  # e.g., "direction"
        value = cmd.get(field)

        if not value:
            return rule.get("default", "")

        # Check if mapping is object-specific
        mappings = rule.get("mappings", {})
        obj = cmd.get("object")

        # Try object-specific mapping first
        if obj and obj in mappings:
            return mappings[obj].get(value, rule.get("default", ""))

        # Try generic mapping
        if "default" in mappings:
            return mappings["default"].get(value, rule.get("default", ""))

        # Direct mapping (no object nesting)
        return mappings.get(value, rule.get("default", ""))

    def _expand_env(self, rule: dict) -> str:
        """Get value from environment variable."""
        var = rule.get("var")
        if not var:
            return rule.get("default", "")
        default = rule.get("default", "")
        return os.environ.get(var, default)

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

    def _expand_format(self, cmd: dict, rule: dict) -> str:
        """Format string with command fields."""
        template = rule.get("template", "")

        # If template contains a field that's empty, return default
        # This prevents "-t " with no value
        import re

        fields = re.findall(r"\{(\w+)\}", template)
        for field in fields:
            if field in cmd and not cmd[field]:
                return rule.get("default", "")

        try:
            return template.format(**cmd)
        except KeyError:
            return rule.get("default", "")
