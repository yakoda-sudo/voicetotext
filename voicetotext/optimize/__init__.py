"""Text optimization (cleanup + compression) with pluggable backends."""

from .base import Optimizer, OptimizeError
from .factory import get_optimizer

__all__ = ["Optimizer", "OptimizeError", "get_optimizer"]
