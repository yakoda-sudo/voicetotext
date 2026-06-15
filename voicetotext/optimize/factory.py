"""Factory that returns the configured optimizer backend."""

from __future__ import annotations

from ..config import CONFIG
from .base import Optimizer


def get_optimizer(backend: str | None = None) -> Optimizer:
    backend = (backend or CONFIG.optimize.backend).lower()
    if backend == "ollama":
        from .ollama_backend import OllamaOptimizer

        return OllamaOptimizer()
    # "none" or anything unrecognized → safe pass-through
    from .noop_backend import NoopOptimizer

    return NoopOptimizer()
