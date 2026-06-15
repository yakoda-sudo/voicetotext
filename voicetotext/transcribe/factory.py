"""Factory that returns the configured transcriber backend."""

from __future__ import annotations

from ..config import CONFIG
from .base import Transcriber, TranscribeError


def get_transcriber(backend: str | None = None) -> Transcriber:
    backend = (backend or CONFIG.transcribe.backend).lower()
    if backend == "whisper":
        from .whisper_backend import WhisperTranscriber

        return WhisperTranscriber()
    if backend in ("whispercpp", "whisper.cpp", "whisper_cpp"):
        from .whispercpp_backend import WhisperCppTranscriber

        return WhisperCppTranscriber()
    raise TranscribeError(f"Unknown transcribe backend: {backend!r}")
