"""Centralized logging for ALI - plugin-driven environment capture."""

import logging
import json
from pathlib import Path
from datetime import datetime
import os
import uuid


class ALILogger:
    """Structured logging for pattern analysis."""

    def __init__(self, verbose: bool = False, registry=None):
        self.session_id = self._generate_session_id()
        self.log_dir = Path.home() / ".local/share/ali/logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.registry = registry

        self._setup_python_logging(verbose)

    def _generate_session_id(self) -> str:
        """Generate unique session ID with timestamp and UUID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique}"

    def _setup_python_logging(self, verbose: bool):
        """Configure Python logging handlers and formatters."""
        self.logger = logging.getLogger("ali")
        self.logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(
            self.log_dir / f"debug_{self.session_id}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        if verbose:
            import sys

            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging.DEBUG)
            console_formatter = logging.Formatter("%(levelname)s: %(message)s")
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def _collect_plugin_env(self) -> dict:
        """Collect environment variables defined by plugins."""
        env = {}

        if not self.registry:
            return env

        for plugin in self.registry.plugins:
            metadata = plugin.config.get("metadata", {})
            env_config = metadata.get("environment", {})

            for var_list in ["requires", "optional", "captures"]:
                for var in env_config.get(var_list, []):
                    if var in os.environ:
                        env[var] = os.environ[var]

        return env

    def log_command(
        self,
        command_str: str,
        tokens: list | None = None,
        state: dict | None = None,
        result: str | None = None,
        error: str | None = None,
        success: bool = True,
    ):
        """Log command execution with context and results.

        Args:
            command_str: Raw command string
            tokens: Parsed command tokens
            state: Command state after parsing
            result: Command result if successful
            error: Error message if failed
            success: Whether command executed successfully
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "command_raw": command_str,
            "tokens": tokens,
            "state": state,
            "result": result,
            "error": error,
            "success": success,
            "env": self._collect_plugin_env(),
        }

        with open(self.log_dir / "commands.jsonl", "a") as f:
            f.write(json.dumps(event) + "\n")

        if success:
            self.logger.debug(f"Command: {command_str} -> {result}")
        else:
            self.logger.error(f"Command failed: {command_str} -> {error}")

    def log_plugin_load(
        self, plugin_name: str, success: bool, error: str | None = None
    ):
        """Log plugin loading success or failure.

        Args:
            plugin_name: Name of the plugin
            success: Whether plugin loaded successfully
            error: Error message if loading failed
        """
        if success:
            self.logger.debug(f"Loaded plugin: {plugin_name}")
        else:
            self.logger.warning(f"Failed to load plugin {plugin_name}: {error}")

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
