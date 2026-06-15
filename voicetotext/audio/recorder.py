"""Microphone recorder.

Captures audio from the default input device via ``sounddevice`` into an
in-memory buffer, then writes a temporary 16 kHz mono WAV file on stop.

Recording runs on sounddevice's own callback thread, so ``start``/``stop`` are
quick and safe to call from the UI thread.
"""

from __future__ import annotations

import logging
import queue
import wave
from pathlib import Path

from ..config import CONFIG

log = logging.getLogger(__name__)


class RecorderError(RuntimeError):
    """Raised when recording cannot start or produces no audio."""


class Recorder:
    def __init__(self, config=CONFIG.audio):
        self._cfg = config
        self._q: "queue.Queue" = queue.Queue()
        self._stream = None
        self._frames: list[bytes] = []
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _callback(self, indata, frames, time_info, status):  # noqa: ANN001
        if status:
            log.debug("audio status: %s", status)
        # copy bytes out of the buffer immediately
        self._q.put(bytes(indata))

    def start(self) -> None:
        if self._recording:
            return
        try:
            import sounddevice as sd  # imported lazily so import errors are friendly
        except Exception as exc:  # pragma: no cover
            raise RecorderError(
                "sounddevice is not available. Install it with "
                "`pip install sounddevice`."
            ) from exc

        self._frames = []
        while not self._q.empty():
            self._q.get_nowait()

        try:
            self._stream = sd.RawInputStream(
                samplerate=self._cfg.samplerate,
                channels=self._cfg.channels,
                dtype=self._cfg.dtype,
                callback=self._callback,
            )
            self._stream.start()
        except Exception as exc:
            raise RecorderError(f"Could not open microphone: {exc}") from exc

        self._recording = True
        log.info("recording started @ %d Hz", self._cfg.samplerate)

    def stop(self) -> Path:
        """Stop recording and write a temporary WAV file. Returns its path."""
        if not self._recording:
            raise RecorderError("Not currently recording.")

        self._recording = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None

        # drain queue
        while not self._q.empty():
            self._frames.append(self._q.get_nowait())

        data = b"".join(self._frames)
        if not data:
            raise RecorderError("No audio captured — is a microphone connected?")

        self._log_levels(data)
        out_path = CONFIG.tmp_dir / "recording.wav"
        self._write_wav(out_path, data)
        log.info("recording saved: %s (%d bytes)", out_path, len(data))
        return out_path

    def _log_levels(self, data: bytes) -> None:
        """Log RMS/peak so a silent capture (mic permission, wrong device) is
        obvious in the logs rather than silently producing garbage transcripts."""
        try:
            import numpy as np

            a = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            if a.size:
                rms = float(np.sqrt(np.mean(a ** 2)))
                peak = float(np.max(np.abs(a)))
                log.info("audio level — rms=%.5f peak=%.4f", rms, peak)
                if peak < 0.0005:
                    log.warning(
                        "audio appears silent (peak=%.5f). Check macOS mic "
                        "permission for your terminal/app and the selected "
                        "input device.", peak
                    )
        except Exception as exc:  # diagnostics must never break recording
            log.debug("level check skipped: %s", exc)

    def _write_wav(self, path: Path, data: bytes) -> None:
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(self._cfg.channels)
            wf.setsampwidth(2)  # int16 == 2 bytes
            wf.setframerate(self._cfg.samplerate)
            wf.writeframes(data)
