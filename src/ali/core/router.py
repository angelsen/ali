"""Router for ALI - finds the right plugin for a command based on verb and context."""

from typing import List, Dict, Any, Optional
from pathlib import Path
from .plugin import YamlPlugin


class Router:
    """Routes commands to appropriate plugins based on verb and context."""

    def __init__(self):
        """Initialize empty router."""
        self.plugins: List[YamlPlugin] = []
        self.registry: Dict[str, List[YamlPlugin]] = {}  # verb → [plugins]

    def load_plugins(self, plugin_dir: str | Path) -> None:
        """Load all plugins from a directory."""
        plugin_dir = Path(plugin_dir)

        for plugin_path in plugin_dir.glob("*/plugin.yaml"):
            try:
                plugin = YamlPlugin(plugin_path)
                self.register(plugin)
            except Exception as e:
                print(f"Failed to load {plugin_path}: {e}")

    def register(self, plugin: YamlPlugin) -> None:
        """Register a plugin and index its verbs."""
        self.plugins.append(plugin)

        # Index verbs for fast routing
        vocabulary = plugin.config.get("vocabulary", {})
        verbs = vocabulary.get("verbs", [])

        for verb in verbs:
            if verb not in self.registry:
                self.registry[verb] = []
            self.registry[verb].append(plugin)

        # Also register verb aliases
        verb_aliases = vocabulary.get("verb_aliases", {})
        for alias, target_verb in verb_aliases.items():
            if alias not in self.registry:
                self.registry[alias] = []
            self.registry[alias].append(plugin)

    def route(self, parsed: Dict[str, Any]) -> Optional[YamlPlugin]:
        """Find the right plugin for a command."""
        verb = parsed.get("verb", "")
        context = parsed.get("context", {})

        # Get plugins that handle this verb
        candidates = self.registry.get(verb, [])

        if not candidates:
            return None

        if len(candidates) == 1:
            # Only one plugin handles this verb - easy!
            return candidates[0]

        # Multiple plugins - use context to disambiguate
        return self._select_by_context(candidates, context)

    def _select_by_context(
        self, plugins: List[YamlPlugin], context: Dict[str, Any]
    ) -> Optional[YamlPlugin]:
        """Select plugin based on context when multiple plugins handle the same verb."""
        env = context.get("env", {})
        caller = context.get("caller", "")

        for plugin in plugins:
            plugin_context = plugin.config.get("context", {})

            # Check environment requirements
            env_required = plugin_context.get("env_required")
            if env_required and env_required in env:
                return plugin

            # Check caller match
            caller_match = plugin_context.get("caller")
            if caller_match and caller == caller_match:
                return plugin

        # No context match - return first (or None)
        return plugins[0] if plugins else None

    def list_verbs(self) -> Dict[str, List[str]]:
        """List all available verbs and which plugins handle them."""
        result = {}
        for verb, plugins in self.registry.items():
            result[verb] = [p.name for p in plugins]
        return result

    def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Parse, route, and execute a command."""
        from .parser import parse

        # Parse command
        parsed = parse(command, context)

        # Find plugin
        plugin = self.route(parsed)
        if not plugin:
            verb = parsed.get("verb", "")
            available = list(self.registry.keys())
            if available:
                return f"Unknown command: {verb}. Available: {', '.join(sorted(available))}"
            else:
                return "No plugins loaded"

        # Execute
        return plugin.execute(parsed)
