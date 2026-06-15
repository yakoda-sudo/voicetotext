"""Play a short notification sound (the "Tink"-style stop cue).

Best-effort and non-blocking where possible. On macOS we play the system Tink
sound; on Windows a system beep / MessageBeep; elsewhere a terminal bell.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading

log = logging.getLogger(__name__)

_MAC_TINK = "/System/Library/Sounds/Tink.aiff"


def _play_blocking() -> None:
    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", _MAC_TINK], check=False)
            return
        if sys.platform.startswith("win"):
            import winsound  # type: ignore

            winsound.MessageBeep(winsound.MB_OK)
            return
        # Linux / fallback: terminal bell
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception as exc:  # pragma: no cover
        log.debug("sound cue failed: %s", exc)


def play_tink() -> None:
    """Play the stop cue without blocking the caller."""
    threading.Thread(target=_play_blocking, daemon=True).start()
