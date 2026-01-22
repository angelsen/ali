"""Service Registry - Tracks plugin services and dependencies."""

from typing import Dict, List
from pathlib import Path
from .plugin import Plugin


class ServiceRegistry:
    """Tracks what services plugins provide and require."""

    def __init__(self, logger=None):
        self.plugins: List[Plugin] = []
        self.providers: Dict[str, List[Plugin]] = {}
        self.verb_index: Dict[str, List[Plugin]] = {}
        self.logger = logger

    def load_plugins(self, plugin_dir: Path) -> None:
        """Load all plugins from directory and build indices."""
        self.plugins = []
        self.providers = {}
        self.verb_index = {}

        for yaml_path in plugin_dir.glob("*/plugin.yaml"):
            try:
                plugin = Plugin(yaml_path)

                if plugin.is_active():
                    self.register(plugin)
                else:
                    if self.logger:
                        self.logger.debug(f"Skipped (inactive): {plugin.name}")

            except Exception as e:
                if self.logger:
                    self.logger.log_plugin_load(yaml_path.parent.name, False, str(e))

    def register(self, plugin: Plugin) -> None:
        """Register plugin and build service and verb indices."""
        self.plugins.append(plugin)

        if isinstance(plugin.provides, dict):
            for service_name in plugin.provides:
                if service_name not in self.providers:
                    self.providers[service_name] = []
                self.providers[service_name].append(plugin)
        elif isinstance(plugin.provides, list):
            for service_name in plugin.provides:
                if service_name not in self.providers:
                    self.providers[service_name] = []
                self.providers[service_name].append(plugin)

        for verb in plugin.verbs:
            if verb not in self.verb_index:
                self.verb_index[verb] = []
            self.verb_index[verb].append(plugin)

        if self.logger:
            self.logger.log_plugin_load(plugin.name, True)

    def get_plugins_for_verb(self, verb: str) -> List[Plugin]:
        """Get all plugins that handle the given verb."""
        return self.verb_index.get(verb.upper(), [])
