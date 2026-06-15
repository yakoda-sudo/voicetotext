"""Application entry point.

Run with:  python main.py
Or after install:  voicetotext
"""

from __future__ import annotations

import logging

from voicetotext.ui import run
from voicetotext.utils.logging_setup import setup_logging


def main() -> None:
    setup_logging(level=logging.INFO)
    run()


if __name__ == "__main__":
    main()
