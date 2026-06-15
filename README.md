# VoiceToText

A lightweight, **fully offline** voice-to-text desktop tool for **Windows and macOS**.
A small borderless floating window with three buttons — **Record**, **Stop**,
**AI Optimize** — records your microphone, transcribes it locally with Whisper,
and (optionally) cleans + compresses the text with a local LLM via Ollama.
Both the raw draft and the optimized result are copied to your clipboard
automatically.

<img width="1672" height="210" alt="image" src="https://github.com/user-attachments/assets/56aa07ff-5765-4f4a-ad9a-59b0f97538ab" />

## Features (v0.1)

- **Tiny floating window** (Tkinter, borderless, always-on-top, draggable). No
  nested menus — just three buttons.
- **Fully offline** — Whisper for transcription, Ollama for optimization.
- **Auto clipboard** — draft is copied the moment transcription finishes; the
  optimized version is copied when you press *AI Optimize*.
- **Modular design** — `audio`, `transcribe`, `optimize`, `ui`, `utils`
  subpackages with pluggable backends, so it's easy to extend.
- **Stop cue** — plays a short "Tink"-style sound on stop.
- **Conversation log** — every session is appended to `~/.voicetotext/logs/`.

## Architecture

```
voicetotext/
  config.py            # all settings (overridable via VTT_* env vars)
  controller.py        # orchestrates record → transcribe → optimize (+ i18n strings)
  audio/               # sounddevice mic capture → 16 kHz mono WAV
  transcribe/          # base + factory; whisper_backend, whispercpp_backend
  optimize/            # base + factory; ollama_backend, noop_backend
  ui/                  # tkinter floating window
  utils/               # clipboard, logging, sound cue
main.py                # entry point
```

The slow steps (transcription, optimization) run on background threads, so the
UI never freezes; results are marshaled back to the Tk main loop.

## Setup

1. **Python 3.9+**.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   - The default transcription backend (`openai-whisper`) decodes the WAV
     itself via Python's stdlib, so **no ffmpeg is required**.
3. **Ollama** (for AI Optimize): install from https://ollama.com, then:
   ```bash
   ollama pull llama3.2
   ollama serve        # usually runs automatically
   ```

## Run

```bash
python main.py
```

- **Record** → starts capture, status shows `🎙️ Recording…`
- **Stop** → ends capture, plays the Tink cue, transcribes, copies the draft.
- **AI Optimize** → cleans/compresses the draft with the local LLM and copies it.

## Configuration

Everything is configurable via environment variables (prefix `VTT_`):

| Variable | Default | Meaning |
|---|---|---|
| `VTT_TRANSCRIBE_BACKEND` | `whisper` | `whisper` or `whispercpp` |
| `VTT_WHISPER_MODEL` | `base.en` | openai-whisper model name |
| `VTT_LANGUAGE` | `en` | transcription language (`auto` to detect) |
| `VTT_WHISPERCPP_BIN` | `whisper-cli` | whisper.cpp binary |
| `VTT_WHISPERCPP_MODEL` | – | path to GGML `.bin` model |
| `VTT_OPTIMIZE_BACKEND` | `ollama` | `ollama` or `none` |
| `VTT_OLLAMA_MODEL` | `gemma4` | local LLM model (matched against `ollama list`; tag optional) |
| `VTT_OLLAMA_HOST` | `http://localhost:11434` | Ollama server |
| `VTT_SAMPLERATE` | `16000` | mic sample rate |

## Packaging (offline distribution)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name VoiceToText main.py
```
Produces `dist/VoiceToText.exe` (Windows) or `dist/VoiceToText.app` (macOS).

Optional: Core ML / Apple Neural Engine (advanced, extra perf gain for apple M chip)
Core ML runs the encoder on the ANE for a further ~2–3× on small models, but it's fiddly and not needed for good performance. Only do this if you want maximum speed:
bash# use an isolated conda env so it doesn't break your system Python
conda create -n coreml python=3.11 -y
conda activate coreml
pip install torch openai-whisper ane_transformers coremltools
cd /Users/you/Downloads/whisper.cpp
./models/generate-coreml-model.sh base.en   # -> models/ggml-base.en-encoder.mlmodelc
conda deactivate

# then rebuild whisper.cpp WITH Core ML support:
rm -rf build
cmake -B build -DWHISPER_COREML=1
cmake --build build -j --config Release
The .mlmodelc must sit next to the .bin. The first run is slow while macOS compiles the model for your chip; subsequent runs are fast. Important: only build with -DWHISPER_COREML=1 after the .mlmodelc exists, or the binary will refuse to start.

## Roadmap (later versions)

- Multi-language GUI + Whisper language models.
- Live volume meter (progress bar of recording amplitude).
- Plugin system: swap the optimizer for GPT-4 / Claude (the `Optimizer`
  interface is the seam for this).
- Conversation log viewer.

## License

MIT
