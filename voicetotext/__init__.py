"""VoiceToText — local, offline voice-to-text desktop tool.

A lightweight floating-window utility that records mic audio, transcribes it
locally with Whisper, and optionally cleans/compresses the text with a local
LLM via Ollama. Drafts and final text are copied to the system clipboard.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
