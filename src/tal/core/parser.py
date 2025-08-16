"""Ultra-dumb TAL parser - just tokenizes, plugins interpret everything."""

import re
from typing import Any, Dict, List, Optional


class TALParser:
    """Truly dumb TAL parser - just tokenizes commands."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize parser with optional context from environment."""
        self.context = context or {}

    def tokenize(self, command: str) -> List[str]:
        """Tokenize command string into parts."""
        # Pattern matches:
        # - Quoted strings (preserve spaces inside)
        # - Pane refs (.1, .2)
        # - Window refs (:1, :2)
        # - Visual selector (?)
        # - Words
        # - Numbers
        pattern = r"""
            "[^"]*"|           # Double quoted string
            '[^']*'|           # Single quoted string
            \.[a-zA-Z]\w*|     # Dot-prefixed words (.THIS, .current)
            \.\d+|             # Pane reference (.1, .2)
            :[a-zA-Z]\w*|      # Colon-prefixed words (:THIS, :current)
            :\d+|              # Window reference (:1, :2)
            \?|                # Visual selector
            [a-zA-Z][\w-]*|    # Words (can contain hyphen)
            \d+                # Numbers
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
    """Parse a TAL command string."""
    parser = TALParser(context)
    return parser.parse(command)
