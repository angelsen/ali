"""ALI Core - Service-oriented plugin architecture."""

from .plugin import Plugin
from .registry import ServiceRegistry
from .resolver import resolve_command
from .router import Router

__all__ = [
    "Plugin",
    "ServiceRegistry",
    "resolve_command",
    "Router",
]
