"""Transcriber interface — implement ``transcribe(wav_path) -> str``."""

from __future__ import annotations

import abc
from pathlib import Path


class TranscribeError(RuntimeError):
    """Raised when transcription fails."""


class Transcriber(abc.ABC):
    @abc.abstractmethod
    def transcribe(self, wav_path: Path) -> str:
        """Return plain transcribed text for the given WAV file."""
        raise NotImplementedError
