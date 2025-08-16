"""Plugin system for ALI - loads YAML configurations and delegates to rules engine."""

import yaml
from pathlib import Path
from .rules import RulesEngine


class YamlPlugin:
    """Plugin loaded from YAML configuration."""

    def __init__(self, config_path: str | Path):
        """Load plugin from YAML file."""
        self.config_path = Path(config_path)

        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        self.name = self.config.get("name", "unknown")
        self.rules_engine = RulesEngine()

        # Extract vocabulary for router registration
        vocabulary = self.config.get("vocabulary", {})
        self.verbs = set(vocabulary.get("verbs", []))
        self.verb_aliases = vocabulary.get("verb_aliases", {})

    def execute(self, cmd: dict) -> str:
        """Execute command using rules engine."""
        # Resolve verb aliases
        verb = cmd.get("verb", "")
        if verb in self.verb_aliases:
            cmd["verb"] = self.verb_aliases[verb]

        # Process through rules engine
        return self.rules_engine.process(cmd, self.config)
