"""Plugin - Loads and holds plugin YAML configuration."""

import yaml
from pathlib import Path


class Plugin:
    """A plugin loaded from YAML. Just data, no logic."""

    def __init__(self, yaml_path: Path):
        """Load plugin from YAML file."""
        self.path = yaml_path
        self.name = yaml_path.parent.name  # Directory name

        with open(yaml_path) as f:
            self.config = yaml.safe_load(f)

        # Extract common fields for convenience
        self.version = self.config.get("version", "1.0")
        self.description = self.config.get("description", "")

        # Services
        self.provides = self.config.get("provides", {})
        self.requires = self.config.get("requires", [])

        # Vocabulary
        vocab = self.config.get("vocabulary", {})
        self.verbs = set(vocab.get("verbs", []))
        self.objects = set(vocab.get("objects", []))
        self.directions = set(vocab.get("directions", []))

        # Patterns for token recognition
        self.patterns = self.config.get("patterns", [])

        # Expectations for verb parsing
        self.expectations = self.config.get("expectations", {})

        # Inference rules
        self.inference = self.config.get("inference", [])

        # Commands
        self.commands = self.config.get("commands", [])

        # Service handlers (how this plugin provides services)
        self.service_handlers = self.config.get("service_handlers", {})

        # Context requirements (e.g., requires TMUX env)
        self.context = self.config.get("context", {})

    def is_active(self) -> bool:
        """Check if plugin should be active based on context."""
        if not self.context:
            return True

        # Check environment variables
        if "requires_env" in self.context:
            import os

            required = self.context["requires_env"]
            if isinstance(required, str):
                required = [required]
            for env_var in required:
                if env_var not in os.environ:
                    return False

        return True

    def __repr__(self):
        return f"Plugin({self.name} v{self.version})"
