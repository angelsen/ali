"""Service Registry - Tracks plugin services and dependencies."""

from typing import Dict, List, Optional
from pathlib import Path
from .plugin import Plugin


class ServiceRegistry:
    """Tracks what services plugins provide and require."""

    def __init__(self, logger=None):
        """Initialize empty registry."""
        self.plugins: List[Plugin] = []
        self.providers: Dict[str, List[Plugin]] = {}  # service -> [plugins]
        self.verb_index: Dict[str, Plugin] = {}  # verb -> plugin
        self.logger = logger

    def load_plugins(self, plugin_dir: Path) -> None:
        """Load all plugins from directory."""
        self.plugins = []
        self.providers = {}
        self.verb_index = {}

        # Find all plugin.yaml files
        for yaml_path in plugin_dir.glob("*/plugin.yaml"):
            try:
                plugin = Plugin(yaml_path)

                # Only register active plugins
                if plugin.is_active():
                    self.register(plugin)
                else:
                    if self.logger:
                        self.logger.debug(f"Skipped (inactive): {plugin.name}")

            except Exception as e:
                if self.logger:
                    self.logger.log_plugin_load(yaml_path.parent.name, False, str(e))

    def register(self, plugin: Plugin) -> None:
        """Register a plugin and index its services and verbs."""
        self.plugins.append(plugin)

        # Index services this plugin provides
        if isinstance(plugin.provides, dict):
            # New format: provides: {service_name: {...}}
            for service_name in plugin.provides:
                if service_name not in self.providers:
                    self.providers[service_name] = []
                self.providers[service_name].append(plugin)
        elif isinstance(plugin.provides, list):
            # Legacy format: provides: [service1, service2]
            for service_name in plugin.provides:
                if service_name not in self.providers:
                    self.providers[service_name] = []
                self.providers[service_name].append(plugin)

        # Index verbs this plugin handles
        for verb in plugin.verbs:
            if verb not in self.verb_index:
                self.verb_index[verb] = plugin
            # TODO: Handle multiple plugins with same verb

        if self.logger:
            self.logger.log_plugin_load(plugin.name, True)

    def get_plugin_for_verb(self, verb: str) -> Optional[Plugin]:
        """Get plugin that handles a verb."""
        return self.verb_index.get(verb.upper())
