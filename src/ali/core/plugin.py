"""Plugin base and YAML plugin implementation."""

from typing import Protocol
import yaml
from pathlib import Path
from .expansion import ExpansionEngine


class Plugin(Protocol):
    """Protocol for ALI plugins - minimal interface."""

    def can_handle(self, verb: str, obj: str) -> bool:
        """Check if this plugin handles the given verb/object combo."""
        ...

    def execute(self, cmd: dict) -> str:
        """Execute the command and return result."""
        ...


class YamlPlugin:
    """Plugin loaded from YAML configuration."""

    def parse_tokens(self, cmd: dict) -> dict:
        """Parse tokens based on plugin's declared vocabulary.

        This default implementation uses the plugin's vocabulary config.
        Plugins can override for custom parsing.
        """
        result = {"verb": cmd["verb"]}
        if "context" in cmd:
            result["context"] = cmd["context"]

        tokens = cmd.get("tokens", [])
        if not tokens:
            return result

        # Get vocabulary from plugin config
        vocabulary = self.config.get("vocabulary", {})
        objects = set(vocabulary.get("objects", []))
        directions = set(vocabulary.get("directions", []))
        clauses = set(vocabulary.get("clauses", []))
        targets = vocabulary.get("target_patterns", [])

        i = 0
        while i < len(tokens):
            token = tokens[i]
            token_upper = token.upper()
            token_lower = token.lower()

            # Check if it's a known object
            if i == 0 and token_upper in objects:
                result["object"] = token_upper
            # Check if it's a direction
            elif token_lower in directions:
                result["direction"] = token_lower
            # Check if it's a target pattern
            elif self._is_target(token, targets):
                if "target" not in result:
                    result["target"] = token
                else:
                    # Multiple targets
                    if "targets" not in result:
                        result["targets"] = [result["target"]]
                        del result["target"]
                    result["targets"].append(token)
            # Check if it's a clause
            elif token_upper in clauses and i + 1 < len(tokens):
                # Use lowercase for field name (WITH → with)
                result[token_lower] = tokens[i + 1]
                i += 1  # Skip next token
            # Everything else as args
            else:
                if "args" not in result:
                    result["args"] = []
                result["args"].append(token)

            i += 1

        return result

    def _is_target(self, token: str, patterns: list) -> bool:
        """Check if token matches any target pattern."""
        import re

        for pattern in patterns:
            if isinstance(pattern, str):
                # Simple string match
                if token == pattern:
                    return True
            elif isinstance(pattern, dict):
                # Pattern with regex
                regex = pattern.get("regex")
                if regex and re.match(regex, token):
                    return True
        return False

    def __init__(self, config_path: str | Path):
        """Load plugin from YAML file."""
        self.config_path = Path(config_path)

        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        self.name = self.config.get("name", "unknown")
        self.commands = self.config.get("commands", {})
        self.expansions = self.config.get("expansions", {})
        self.validations = self.config.get("validations", {})
        self.field_aliases = self.config.get("field_aliases", {})
        self.field_transformations = self.config.get("field_transformations", {})
        self.inference = self.config.get("inference", {})
        self.expansion_engine = ExpansionEngine()

    def can_handle(self, cmd: dict) -> bool:
        """Check if we have a command template for this verb/object."""
        # Handle both old format and new token format
        if isinstance(cmd, str):
            # Old interface - just verb passed
            verb = cmd
            obj = None
        elif isinstance(cmd, dict):
            if "tokens" in cmd:
                # Parse tokens to get object
                parsed = self.parse_tokens(cmd)
                verb = parsed.get("verb")
                obj = parsed.get("object")
            else:
                verb = cmd.get("verb")
                obj = cmd.get("object")
        else:
            return False

        # Direct match first
        for command in self.commands:
            match = command.get("match", {})
            if match.get("verb") == verb and match.get("object") == obj:
                return True

        # If no object but we might be able to infer, check verb only
        if not obj:
            for command in self.commands:
                match = command.get("match", {})
                if match.get("verb") == verb:
                    return True

        return False

    def validate(self, cmd: dict) -> tuple[bool, str]:
        """Validate command against plugin rules."""
        verb = cmd.get("verb", "")
        obj = cmd.get("object", "")
        command_key = f"{verb} {obj}" if obj else verb

        # Check allowed parameters for this command
        allowed_params_config = self.validations.get("allowed_params", {})
        if command_key in allowed_params_config:
            allowed = set(allowed_params_config[command_key])
            # Add standard fields that are always allowed
            allowed.update(["verb", "object", "context", "args"])

            # Check for unexpected parameters
            for param in cmd.keys():
                if param not in allowed:
                    return (
                        False,
                        f"'{command_key}' doesn't accept parameter '{param}'",
                    )

        # Check allowed directions
        allowed_dirs = self.validations.get("allowed_directions", {})
        if allowed_dirs and cmd.get("direction"):
            direction = cmd.get("direction")

            if obj in allowed_dirs:
                allowed = allowed_dirs[obj]
                if direction not in allowed:
                    return (
                        False,
                        f"{obj} does not support direction '{direction}'. Allowed: {', '.join(allowed)}",
                    )

        return (True, "")

    def execute(self, cmd: dict) -> str:
        """Execute command using template from config."""
        # If we got tokens, parse them first
        if "tokens" in cmd:
            cmd = self.parse_tokens(cmd)

        # Apply field aliases (e.g., from → target)
        for old_field, new_field in self.field_aliases.items():
            if old_field in cmd and new_field not in cmd:
                cmd[new_field] = cmd[old_field]

        # Handle SWAP command specially: first target is source, WITH value is target
        if cmd.get("verb") == "SWAP":
            if "target" in cmd and "with" in cmd:
                cmd["source"] = cmd["target"]
                cmd["target"] = cmd["with"]
                del cmd["with"]

        # Infer object from target if object is missing (BEFORE transformations!)
        if not cmd.get("object") and cmd.get("target"):
            import re

            target = cmd["target"]
            for pattern, obj_type in self.inference.get(
                "object_from_target", {}
            ).items():
                if re.match(pattern, target):
                    cmd["object"] = obj_type
                    break

        # Apply field transformations AFTER inference (e.g., .THIS → "")
        for field, transforms in self.field_transformations.items():
            if field in cmd and cmd[field] in transforms:
                cmd[field] = transforms[cmd[field]]

        # Validate first
        valid, error = self.validate(cmd)
        if not valid:
            return f"Error: {error}"

        verb = cmd.get("verb")
        obj = cmd.get("object")

        # Find matching command template
        for command in self.commands:
            match = command.get("match", {})
            if match.get("verb") == verb and match.get("object") == obj:
                template = command.get("exec", "")

                # Apply expansions
                expanded = self.expansion_engine.expand(cmd, self.expansions)

                # Merge original cmd with expanded values
                # Expanded values override original fields
                template_vars = {**cmd, **expanded}

                # Fill template - use defaults for missing values
                try:
                    result = template.format_map(DefaultDict(template_vars))
                except KeyError:
                    # If a key is still missing, return empty string for it
                    result = template

                return result

        return f"No command found for {verb} {obj}"


class DefaultDict(dict):
    """Dict that returns empty string for missing keys."""

    def __missing__(self, key):
        return ""
