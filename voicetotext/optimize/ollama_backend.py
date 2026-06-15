"""Ollama backend for local LLM text optimization.

Talks to a running Ollama server over HTTP (default http://localhost:11434).
Uses the ``/api/generate`` endpoint with streaming disabled for simplicity.
Only depends on the standard library (urllib) so there is no hard third-party
requirement just for this.

Error handling distinguishes the two common failure modes, which Ollama itself
signals differently (per its API docs):
  * connection refused  -> server not running
  * HTTP 404 + JSON body -> the requested model is not pulled
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from ..config import CONFIG
from .base import DEFAULT_SYSTEM_PROMPT, Optimizer, OptimizeError

log = logging.getLogger(__name__)


class OllamaOptimizer(Optimizer):
    def __init__(self, host: str | None = None, model: str | None = None,
                 timeout: int | None = None):
        self._host = (host or CONFIG.optimize.ollama_host).rstrip("/")
        self._model = model or CONFIG.optimize.ollama_model
        self._timeout = timeout or CONFIG.optimize.timeout

    # -- helpers -------------------------------------------------------------
    def _list_models(self) -> list[str]:
        """Return locally available model names (best-effort)."""
        try:
            with urllib.request.urlopen(
                f"{self._host}/api/tags", timeout=self._timeout
            ) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in body.get("models", [])]
        except Exception:  # pragma: no cover
            return []

    def _resolve_model(self, available: list[str]) -> str | None:
        """Match the configured model against what's installed.

        Ollama names carry a ``:tag`` (e.g. ``gemma4:latest``). We accept an
        exact match, or a match ignoring the tag so ``gemma4`` finds
        ``gemma4:latest``.
        """
        if not available:
            return self._model  # can't verify; try as-is
        if self._model in available:
            return self._model
        base = self._model.split(":", 1)[0]
        for name in available:
            if name == self._model or name.split(":", 1)[0] == base:
                return name
        return None

    # -- main ----------------------------------------------------------------
    def optimize(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        available = self._list_models()
        model = self._resolve_model(available)
        if model is None:
            have = ", ".join(available) or "none"
            raise OptimizeError(
                f"Model '{self._model}' is not installed in Ollama. "
                f"Installed models: {have}. "
                f"Either run `ollama pull {self._model}` or set "
                f"VTT_OLLAMA_MODEL to one you have."
            )

        url = f"{self._host}/api/generate"
        payload = {
            "model": model,
            "system": DEFAULT_SYSTEM_PROMPT,
            "prompt": text,
            "stream": False,
            "options": {"temperature": 0.2},
            # don't let reasoning models burn time "thinking" out loud
            "think": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Ollama returns a JSON {"error": "..."} body with the real reason
            detail = ""
            try:
                detail = json.loads(exc.read().decode("utf-8")).get("error", "")
            except Exception:
                pass
            raise OptimizeError(
                f"Ollama returned HTTP {exc.code} for model '{model}'"
                + (f": {detail}" if detail else "")
            ) from exc
        except urllib.error.URLError as exc:
            raise OptimizeError(
                f"Could not reach Ollama at {self._host}. Is it running? "
                f"Start it with `ollama serve`. ({exc.reason})"
            ) from exc
        except Exception as exc:
            raise OptimizeError(f"Ollama request failed: {exc}") from exc

        result = (body.get("response") or "").strip()
        if not result:
            raise OptimizeError("Ollama returned an empty response.")
        log.info("optimized %d -> %d chars via %s", len(text), len(result), model)
        return result
