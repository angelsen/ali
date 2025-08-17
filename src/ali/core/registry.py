"""Service Registry - Tracks plugin services and dependencies."""

from typing import Dict, List, Optional
from pathlib import Path
from .plugin import Plugin


class ServiceRegistry:
    """Tracks what services plugins provide and require."""

    def __init__(self):
        """Initialize empty registry."""
        self.plugins: List[Plugin] = []
        self.providers: Dict[str, List[Plugin]] = {}  # service -> [plugins]
        self.verb_index: Dict[str, Plugin] = {}  # verb -> plugin

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
                    print(f"Skipped (inactive): {plugin.name}")

            except Exception as e:
                print(f"Failed to load {yaml_path}: {e}")

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

        print(f"Registered: {plugin}")

    def get_provider(self, service: str) -> Optional[Plugin]:
        """Get first plugin that provides a service."""
        providers = self.providers.get(service, [])
        return providers[0] if providers else None

    def get_all_providers(self, service: str) -> List[Plugin]:
        """Get all plugins that provide a service."""
        return self.providers.get(service, [])

    def get_plugin_for_verb(self, verb: str) -> Optional[Plugin]:
        """Get plugin that handles a verb."""
        return self.verb_index.get(verb.upper())

    def check_dependencies(self) -> List[str]:
        """Check for missing dependencies, return warnings."""
        warnings = []

        for plugin in self.plugins:
            for required in plugin.requires:
                if required not in self.providers:
                    warnings.append(
                        f"{plugin.name} requires '{required}' but no plugin provides it"
                    )

        return warnings

    def get_service_chain(self, plugin: Plugin, command: Dict) -> List[str]:
        """Get the chain of services needed for a command.

        Returns list of services in dependency order.
        """
        chain = []
        needs = command.get("needs", [])

        # Normalize to list
        if isinstance(needs, str):
            needs = [needs]

        # For each needed service, check if provider also needs services
        for service in needs:
            provider = self.get_provider(service)
            if provider and provider.requires:
                # Recursively get provider's requirements
                for required in provider.requires:
                    if required not in chain:
                        chain.append(required)

            if service not in chain:
                chain.append(service)

        return chain
