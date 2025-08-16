"""Ultra-dumb ALI parser - just tokenizes, plugins interpret everything."""

import re
from typing import Any, Dict, List, Optional


class ALIParser:
    """Truly dumb ALI parser - just tokenizes commands."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize parser with optional context from environment."""
        self.context = context or {}

    def tokenize(self, command: str) -> List[str]:
        """Tokenize command string into parts."""
        # Pattern matches (no domain knowledge):
        # - Quoted strings (preserve spaces)
        # - Special single chars (?, @, etc.)
        # - Identifiers (can contain letters, numbers, dots, colons, hyphens)
        # - Plain numbers
        pattern = r"""
            "[^"]*"|                          # Double quoted string
            '[^']*'|                          # Single quoted string
            \?|@|#|!|                         # Special single characters
            [a-zA-Z_][a-zA-Z0-9_:.\-]*|       # Identifiers (can have : . -)
            \.[a-zA-Z0-9_]+|                  # Dot-prefixed identifiers
            :[a-zA-Z0-9_]+|                   # Colon-prefixed identifiers
            \d+                               # Plain numbers
        """

        tokens = re.findall(pattern, command, re.VERBOSE | re.IGNORECASE)

        # Strip quotes from quoted strings
        cleaned = []
        for token in tokens:
            if token.startswith(("'", '"')):
                cleaned.append(token[1:-1])
            else:
                cleaned.append(token)

        return cleaned

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
