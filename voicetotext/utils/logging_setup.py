"""Logging setup.

Provides a configured root logger plus a dedicated conversation logger that
appends each session's draft/final text to a dated file under the log dir.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

from ..config import CONFIG

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_file = CONFIG.log_dir / "voicetotext.log"
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(fmt)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    root.addHandler(stream)

    _CONFIGURED = True


def log_conversation(draft: str, final: str | None = None) -> Path:
    """Append a conversation entry to a per-day JSONL file. Returns its path."""
    day = datetime.now().strftime("%Y-%m-%d")
    path = CONFIG.log_dir / f"conversation-{day}.jsonl"
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "draft": draft,
        "final": final,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path
