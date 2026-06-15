"""Speech-to-text transcription with pluggable backends."""

from .base import Transcriber, TranscribeError
from .factory import get_transcriber

__all__ = ["Transcriber", "TranscribeError", "get_transcriber"]
