"""Application controller and UI string table.

The controller wires together recorder, transcriber and optimizer, and runs the
slow steps (transcription, optimization) on background threads so the Tk UI
never freezes. The UI subscribes via simple callbacks.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable

from .audio import Recorder, RecorderError
from .optimize import get_optimizer
from .transcribe import get_transcriber
from .utils.clipboard import copy_to_clipboard
from .utils.logging_setup import log_conversation
from .utils.sound import play_tink

log = logging.getLogger(__name__)


# --- UI strings (i18n-ready). v0.1 ships English only. -----------------------
STRINGS = {
    "en": {
        "record": "● Record",
        "stop": "■ Stop",
        "optimize": "✦ AI Optimize",
        "idle": "Ready",
        "recording": "🎙️ Recording…",
        "transcribing": "Transcribing…",
        "optimizing": "Optimizing…",
        "draft_copied": "Draft copied to clipboard",
        "final_copied": "Optimized & copied to clipboard",
        "no_text": "Nothing to optimize yet",
        "error": "Error: {msg}",
    }
}


def t(key: str, lang: str = "en", **kw) -> str:
    table = STRINGS.get(lang, STRINGS["en"])
    return table.get(key, key).format(**kw)


class Controller:
    """Mediates between the UI and the processing backends."""

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._recorder = Recorder()
        self._transcriber = None  # lazy
        self._optimizer = None  # lazy
        self._draft_text: str = ""
        self._final_text: str = ""

        # UI callbacks (set by the window). Each takes a single str/none arg.
        self.on_status: Callable[[str], None] = lambda s: None
        self.on_text: Callable[[str], None] = lambda s: None
        self.on_state: Callable[[str], None] = lambda s: None  # idle/recording/busy

    # -- recording -----------------------------------------------------------
    @property
    def is_recording(self) -> bool:
        return self._recorder.is_recording

    def start_recording(self) -> None:
        try:
            self._recorder.start()
            self.on_state("recording")
            self.on_status(t("recording", self.lang))
        except RecorderError as exc:
            self.on_status(t("error", self.lang, msg=str(exc)))
            self.on_state("idle")

    def stop_recording(self) -> None:
        try:
            wav_path = self._recorder.stop()
        except RecorderError as exc:
            self.on_status(t("error", self.lang, msg=str(exc)))
            self.on_state("idle")
            return
        play_tink()
        self.on_state("busy")
        self.on_status(t("transcribing", self.lang))
        threading.Thread(
            target=self._transcribe_worker, args=(wav_path,), daemon=True
        ).start()

    def _transcribe_worker(self, wav_path: Path) -> None:
        try:
            if self._transcriber is None:
                self._transcriber = get_transcriber()
            text = self._transcriber.transcribe(wav_path)
            self._draft_text = text
            self._final_text = ""
            copy_to_clipboard(text)  # draft → clipboard immediately
            log_conversation(draft=text)
            self.on_text(text)
            self.on_status(t("draft_copied", self.lang))
        except Exception as exc:  # noqa: BLE001
            log.exception("transcription error")
            self.on_status(t("error", self.lang, msg=str(exc)))
        finally:
            self.on_state("idle")

    # -- optimization --------------------------------------------------------
    def optimize(self) -> None:
        if not self._draft_text.strip():
            self.on_status(t("no_text", self.lang))
            return
        self.on_state("busy")
        self.on_status(t("optimizing", self.lang))
        threading.Thread(target=self._optimize_worker, daemon=True).start()

    def _optimize_worker(self) -> None:
        try:
            if self._optimizer is None:
                self._optimizer = get_optimizer()
            result = self._optimizer.optimize(self._draft_text)
            self._final_text = result
            copy_to_clipboard(result)
            log_conversation(draft=self._draft_text, final=result)
            self.on_text(result)
            self.on_status(t("final_copied", self.lang))
        except Exception as exc:  # noqa: BLE001
            log.exception("optimization error")
            self.on_status(t("error", self.lang, msg=str(exc)))
        finally:
            self.on_state("idle")

    # -- accessors -----------------------------------------------------------
    @property
    def draft_text(self) -> str:
        return self._draft_text

    @property
    def final_text(self) -> str:
        return self._final_text
