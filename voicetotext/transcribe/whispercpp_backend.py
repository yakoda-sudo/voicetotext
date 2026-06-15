"""whisper.cpp backend via subprocess.

Calls a compiled whisper.cpp binary (e.g. ``whisper-cli`` / ``main``) with a
GGML model file and parses the produced text output. Useful when you want a
fast, dependency-light native transcriber.

Expects ``WHISPERCPP_BIN`` (binary) and ``WHISPERCPP_MODEL`` (path to a .bin
GGML model) to be configured.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ..config import CONFIG
from .base import Transcriber, TranscribeError

log = logging.getLogger(__name__)


class WhisperCppTranscriber(Transcriber):
    def __init__(self, binary: str | None = None, model_path: str | None = None,
                 language: str | None = None):
        self._binary = binary or CONFIG.transcribe.whispercpp_binary
        self._model_path = model_path or CONFIG.transcribe.whispercpp_model_path
        self._language = language or CONFIG.transcribe.language

    def transcribe(self, wav_path: Path) -> str:
        if not self._model_path:
            raise TranscribeError(
                "whisper.cpp model path not set (VTT_WHISPERCPP_MODEL)."
            )

        # -otxt writes <wav>.txt; -nt suppresses timestamps in stdout.
        cmd = [
            self._binary,
            "-m", self._model_path,
            "-f", str(wav_path),
            "-l", self._language or "auto",
            "-nt",
        ]
        log.info("running whisper.cpp: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
        except FileNotFoundError as exc:
            raise TranscribeError(
                f"whisper.cpp binary not found: {self._binary}"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise TranscribeError(
                f"whisper.cpp failed: {exc.stderr or exc}"
            ) from exc

        text = (proc.stdout or "").strip()
        if not text:
            # some builds only write the .txt sidecar
            sidecar = wav_path.with_suffix(wav_path.suffix + ".txt")
            if sidecar.exists():
                text = sidecar.read_text(encoding="utf-8").strip()
        log.info("transcribed %d chars", len(text))
        return text
