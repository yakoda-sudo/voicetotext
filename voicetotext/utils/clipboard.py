"""Cross-platform clipboard writing.

Strategy: try the lightweight ``pyperclip`` package first (works on Windows and
macOS out of the box). If unavailable, fall back to native OS commands
(``pbcopy`` on macOS, ``clip`` on Windows). As a last resort, use a hidden
Tk root's clipboard. Never raise to the caller — copying is best-effort.
"""

from __future__ import annotations

import subprocess
import sys
import logging

log = logging.getLogger(__name__)


def _copy_pyperclip(text: str) -> bool:
    try:
        import pyperclip  # type: ignore

        pyperclip.copy(text)
        return True
    except Exception as exc:  # pragma: no cover - depends on env
        log.debug("pyperclip unavailable: %s", exc)
        return False


def _copy_native(text: str) -> bool:
    try:
        if sys.platform == "darwin":
            proc = subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            return proc.returncode == 0
        if sys.platform.startswith("win"):
            proc = subprocess.run(
                ["clip"], input=text.encode("utf-16-le"), check=True, shell=True
            )
            return proc.returncode == 0
        # Linux dev fallback
        for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"), check=True)
                return True
            except FileNotFoundError:
                continue
    except Exception as exc:  # pragma: no cover
        log.debug("native clipboard failed: %s", exc)
    return False


def _copy_tk(text: str) -> bool:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()  # keeps clipboard after destroy on most platforms
        root.destroy()
        return True
    except Exception as exc:  # pragma: no cover
        log.debug("tk clipboard failed: %s", exc)
        return False


def copy_to_clipboard(text: str) -> bool:
    """Copy ``text`` to the system clipboard. Returns True on success."""
    if text is None:
        return False
    for fn in (_copy_pyperclip, _copy_native, _copy_tk):
        if fn(text):
            log.debug("clipboard write via %s", fn.__name__)
            return True
    log.warning("all clipboard methods failed")
    return False
