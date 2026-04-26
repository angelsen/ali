"""ALI Core - Service-oriented plugin architecture."""

from .registry import ServiceRegistry
from .router import Router

__all__ = [
    "ServiceRegistry",
    "Router",
]
