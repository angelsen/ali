"""Service Registry - Tracks plugin services and dependencies."""

from pathlib import Path

from .plugin import Plugin
from .resolver import PluginError, validate_templates


class ServiceRegistry:
    """Tracks what services plugins provide and require."""

    def __init__(self, logger=None):
        self.plugins: list[Plugin] = []
        self.providers: dict[str, list[Plugin]] = {}
        self.verb_index: dict[str, list[Plugin]] = {}
        self.logger = logger

    def load_plugins(self, plugin_dir: Path) -> None:
        """Load all plugins from directory and build indices."""
        self.plugins = []
        self.providers = {}
        self.verb_index = {}

        plugins = []
        for yaml_path in plugin_dir.glob("*/plugin.yaml"):
            try:
                plugins.append(Plugin(yaml_path))
            except Exception as e:  # noqa: BLE001 - one broken plugin must not stop the rest loading
                if self.logger:
                    self.logger.log_plugin_load(yaml_path.parent.name, False, str(e))

        # Inactive plugins count too: outside tmux, broot's `{split}` still names a tmux service.
        errors = validate_templates(plugins)
        if errors:
            raise PluginError("\n".join(errors))

        for plugin in plugins:
            if plugin.is_active():
                self.register(plugin)
            elif self.logger:
                self.logger.debug(f"Skipped (inactive): {plugin.name}")

    def register(self, plugin: Plugin) -> None:
        """Register plugin and build service and verb indices."""
        self.plugins.append(plugin)

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

    def get_plugins_for_verb(self, verb: str) -> list[Plugin]:
        """Get all plugins that handle the given verb."""
        return self.verb_index.get(verb.upper(), [])
