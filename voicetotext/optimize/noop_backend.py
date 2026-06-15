"""A pass-through optimizer used when no LLM backend is configured."""

from __future__ import annotations

from .base import Optimizer


class NoopOptimizer(Optimizer):
    def optimize(self, text: str) -> str:
        return (text or "").strip()
