"""Ultra-dumb ALI parser - just tokenizes, plugins interpret everything."""

import shlex
from typing import Any, Dict, List, Optional


class ALIParser:
    """Truly dumb ALI parser - just tokenizes commands."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize parser with optional context from environment."""
        self.context = context or {}

    def tokenize(self, command: str) -> List[str]:
        """Tokenize command string into parts using shlex."""
        try:
            # Use shlex for proper quote handling
            return shlex.split(command)
        except ValueError:
            # Unclosed quote - fall back to simple split
            return command.split()

    def parse(self, command: str) -> dict:
        """Pure tokenizer - no domain knowledge, just verb + tokens."""
        tokens = self.tokenize(command.strip())

        if not tokens:
            return {"error": "Empty command"}

        # First token is verb, everything else is tokens
        result = {"verb": tokens[0].upper(), "tokens": tokens[1:]}

        # Add context if available
        if self.context:
            result["context"] = self.context

        return result


# Convenience function
def parse(command: str, context: Optional[Dict[str, Any]] = None) -> dict:
    """Parse a ALI command string."""
    parser = ALIParser(context)
    return parser.parse(command)
