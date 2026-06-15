"""openai-whisper backend (pure-Python, pip-installable).

Loads the model lazily on first use and caches it. Model name and language
come from config.

We read the WAV file ourselves with the stdlib ``wave`` module and feed Whisper
a float32 numpy array directly. This avoids Whisper's default code path, which
shells out to an external ``ffmpeg`` binary to decode audio — keeping the tool
genuinely dependency-light and offline-friendly. Our recorder already produces
16 kHz mono int16 WAV, exactly what Whisper expects.
"""

from __future__ import annotations

import logging
import wave
from pathlib import Path

from ..config import CONFIG
from .base import Transcriber, TranscribeError

log = logging.getLogger(__name__)

# Whisper operates at 16 kHz internally.
WHISPER_SR = 16000


class WhisperTranscriber(Transcriber):
    def __init__(self, model_name: str | None = None, language: str | None = None):
        self._model_name = model_name or CONFIG.transcribe.whisper_model
        self._language = language or CONFIG.transcribe.language
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            import whisper  # type: ignore
        except Exception as exc:
            raise TranscribeError(
                "openai-whisper is not installed. Install it with "
                "`pip install openai-whisper`."
            ) from exc
        log.info("loading whisper model: %s", self._model_name)
        self._model = whisper.load_model(self._model_name)

    def _load_wav(self, wav_path: Path):
        """Read a WAV file into a float32 mono numpy array at 16 kHz.

        Avoids ffmpeg entirely. Handles 16-bit PCM (what our recorder writes),
        converts stereo to mono, and resamples if the file isn't already 16 kHz.
        """
        try:
            import numpy as np
        except Exception as exc:  # numpy ships with openai-whisper, so this is unlikely
            raise TranscribeError(
                "numpy is required but not installed (`pip install numpy`)."
            ) from exc

        with wave.open(str(wav_path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        if sampwidth != 2:
            raise TranscribeError(
                f"Unsupported sample width {sampwidth * 8}-bit; expected 16-bit PCM."
            )

        # int16 -> float32 in [-1, 1]
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

        # stereo (or more) -> mono by averaging channels
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)

        # resample to 16 kHz if needed (linear interpolation; inputs are already
        # 16 kHz from our recorder, so this is just a safety net)
        if framerate != WHISPER_SR and audio.size:
            duration = audio.size / float(framerate)
            tgt_len = int(round(duration * WHISPER_SR))
            if tgt_len > 0:
                x_old = np.linspace(0.0, 1.0, num=audio.size, endpoint=False)
                x_new = np.linspace(0.0, 1.0, num=tgt_len, endpoint=False)
                audio = np.interp(x_new, x_old, audio).astype(np.float32)

        return np.ascontiguousarray(audio, dtype=np.float32)

    def transcribe(self, wav_path: Path) -> str:
        self._ensure_model()
        try:
            audio = self._load_wav(wav_path)
            # language=None lets whisper auto-detect; we pass configured language
            lang = None if self._language in ("", "auto") else self._language
            result = self._model.transcribe(audio, language=lang, fp16=False)
        except TranscribeError:
            raise
        except Exception as exc:
            raise TranscribeError(f"Transcription failed: {exc}") from exc
        text = (result.get("text") or "").strip()
        log.info("transcribed %d chars", len(text))
        return text
