"""Plugin base and YAML plugin implementation."""

from typing import Protocol, Any
import yaml
import subprocess
from pathlib import Path
from .expansion import ExpansionEngine


class Plugin(Protocol):
    """Protocol for TAL plugins - minimal interface."""
    
    def can_handle(self, verb: str, obj: str) -> bool:
        """Check if this plugin handles the given verb/object combo."""
        ...
    
    def execute(self, cmd: dict) -> str:
        """Execute the command and return result."""
        ...


class YamlPlugin:
    """Plugin loaded from YAML configuration."""
    
    def __init__(self, config_path: str | Path):
        """Load plugin from YAML file."""
        self.config_path = Path(config_path)
        
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.name = self.config.get("name", "unknown")
        self.commands = self.config.get("commands", {})
        self.expansions = self.config.get("expansions", {})
        self.validations = self.config.get("validations", {})
        self.expansion_engine = ExpansionEngine()
        
    def can_handle(self, verb: str, obj: str) -> bool:
        """Check if we have a command template for this verb/object."""
        # Check if we have a matching command
        for command in self.commands:
            match = command.get("match", {})
            if match.get("verb") == verb and match.get("object") == obj:
                return True
        return False
    
    def validate(self, cmd: dict) -> tuple[bool, str]:
        """Validate command against plugin rules."""
        # Check allowed directions
        allowed_dirs = self.validations.get("allowed_directions", {})
        if allowed_dirs and cmd.get("direction"):
            obj = cmd.get("object")
            direction = cmd.get("direction")
            
            if obj in allowed_dirs:
                allowed = allowed_dirs[obj]
                if direction not in allowed:
                    return (False, f"{obj} does not support direction '{direction}'. Allowed: {', '.join(allowed)}")
        
        return (True, "")
    
    def execute(self, cmd: dict) -> str:
        """Execute command using template from config."""
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
                except KeyError as e:
                    # If a key is still missing, return empty string for it
                    result = template
                
                return result
        
        return f"No command found for {verb} {obj}"


class DefaultDict(dict):
    """Dict that returns empty string for missing keys."""
    def __missing__(self, key):
        return ""