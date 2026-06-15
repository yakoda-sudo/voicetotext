"""Optimizer interface.

An optimizer takes raw transcribed text and returns a cleaned, compressed
version suitable for pasting into a chat/LLM window as a prompt. Implement
``optimize(text) -> str``. This abstraction is the seam for future plugins
(GPT-4, Claude, etc.).
"""

from __future__ import annotations

import abc

# Shared instruction used by LLM-backed optimizers. Kept here so all backends
# behave consistently and it is easy to tune in one place.
DEFAULT_SYSTEM_PROMPT = (
    "You clean up raw speech-to-text transcripts. Your tasks: (1) fix grammar, "
    "punctuation and capitalization; (2) correct words the speech recognizer "
    "likely misheard, using surrounding context to choose the word the speaker "
    "actually meant — pay special attention to similar-sounding words and "
    "homophones (e.g. fox/box, their/there/they're, to/too/two, write/right, "
    "affect/effect), picking whichever fits the sentence's meaning; (3) remove "
    "filler words and repetition; (4) keep the speaker's original meaning and "
    "intent — do not add new information or change the message. Output ONLY the "
    "corrected text, with no preamble, explanation, notes, or quotation marks."
)


class OptimizeError(RuntimeError):
    """Raised when optimization fails."""


class Optimizer(abc.ABC):
    @abc.abstractmethod
    def optimize(self, text: str) -> str:
        """Return cleaned/compressed text."""
        raise NotImplementedError
