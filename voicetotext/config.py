"""Central configuration.

All tunable knobs live here so the rest of the codebase imports from one place.
Values can be overridden via environment variables (prefix ``VTT_``) without
touching the source, e.g. ``VTT_WHISPER_MODEL=small.en``.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(f"VTT_{name}", default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(f"VTT_{name}", default))
    except (TypeError, ValueError):
        return default


# Application directories ----------------------------------------------------
APP_NAME = "VoiceToText"
HOME_DIR = Path.home() / ".voicetotext"
LOG_DIR = HOME_DIR / "logs"
TMP_DIR = Path(tempfile.gettempdir()) / "voicetotext"

for _d in (HOME_DIR, LOG_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class AudioConfig:
    samplerate: int = _env_int("SAMPLERATE", 16000)
    channels: int = 1
    dtype: str = "int16"
    # max recording length in seconds, a safety cap
    max_seconds: int = _env_int("MAX_SECONDS", 600)


@dataclass(frozen=True)
class TranscribeConfig:
    # backend: "whisper" (openai-whisper, pip) or "whispercpp" (subprocess)
    backend: str = _env("TRANSCRIBE_BACKEND", "whisper")
    # openai-whisper model name (tiny/base/small/medium/large, optionally .en)
    whisper_model: str = _env("WHISPER_MODEL", "base.en")
    language: str = _env("LANGUAGE", "en")
    # whisper.cpp specifics (only used when backend == "whispercpp")
    whispercpp_binary: str = _env("WHISPERCPP_BIN", "whisper-cli")
    whispercpp_model_path: str = _env("WHISPERCPP_MODEL", "")


@dataclass(frozen=True)
class OptimizeConfig:
    # backend: "ollama" or "none"
    backend: str = _env("OPTIMIZE_BACKEND", "ollama")
    ollama_host: str = _env("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = _env("OLLAMA_MODEL", "gemma4")
    # request timeout in seconds — keep modest so UI stays responsive
    timeout: int = _env_int("OPTIMIZE_TIMEOUT", 60)


@dataclass(frozen=True)
class UIConfig:
    title: str = APP_NAME
    topmost: bool = True
    borderless: bool = True
    # initial language of the GUI strings (only "en" shipped in v0.1)
    language: str = _env("UI_LANGUAGE", "en")


@dataclass(frozen=True)
class Config:
    audio: AudioConfig = field(default_factory=AudioConfig)
    transcribe: TranscribeConfig = field(default_factory=TranscribeConfig)
    optimize: OptimizeConfig = field(default_factory=OptimizeConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    log_dir: Path = LOG_DIR
    tmp_dir: Path = TMP_DIR


CONFIG = Config()
