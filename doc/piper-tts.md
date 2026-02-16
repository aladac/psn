---
source: https://huggingface.co/rhasspy/piper-voices
additional_sources:
  - https://github.com/OHF-Voice/piper1-gpl
  - https://pypi.org/project/piper-tts/
  - https://huggingface.co/campwill/HAL-9000-Piper-TTS
fetched: 2026-02-16
---

# Piper TTS Voices

Piper is a fast, local neural text-to-speech engine that uses espeak-ng for phonemization. It runs entirely offline without cloud dependencies.

**Note**: The original `rhasspy/piper` repo was archived in October 2025. Development moved to [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl).

## Installation

```bash
pip install piper-tts
```

For GPU support, also install `onnxruntime-gpu`.

## Voice Models

Voices are hosted on Hugging Face: [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)

Each voice requires two files:
- `.onnx` - The model file
- `.onnx.json` - Configuration file

### Downloading Voices

```bash
# Download all available voices
python3 -m piper.download_voices

# Download a specific voice
python3 -m piper.download_voices en_US-lessac-medium

# Specify custom storage directory
python3 -m piper.download_voices --data-dir /path/to/voices
```

### Quality Levels

Voices come in different quality tiers:
- `low` - Fastest, lowest quality
- `medium` - Balanced (recommended)
- `high` - Best quality, slower

Example: `en_US-lessac-medium.onnx`

### Supported Languages (40+)

Arabic, Catalan, Czech, Welsh, Danish, German, Greek, English (UK/US), Spanish (Argentina/Spain/Mexico), Farsi, Finnish, French, Hungarian, Icelandic, Indonesian, Italian, Georgian, Kazakh, Luxembourgish, Latvian, Malayalam, Hindi, Nepali, Dutch, Norwegian, Polish, Portuguese (Brazil/Portugal), Romanian, Russian, Slovak, Slovenian, Serbian, Swedish, Swahili, Telugu, Turkish, Ukrainian, Vietnamese, Mandarin Chinese.

## Command Line Usage

### Basic Usage

```bash
# Generate audio file
python3 -m piper -m en_US-lessac-medium -f output.wav -- 'Hello, world!'

# Play directly (requires ffplay)
python3 -m piper -m en_US-lessac-medium -- 'Hello, world!'

# Read from file
python3 -m piper -m en_US-lessac-medium --input-file text.txt -f output.wav
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-m, --model` | Voice model name or path |
| `-f, --output-file` | Output WAV file path |
| `--cuda` | Enable GPU acceleration |
| `--input-file` | Read text from file(s) |
| `--sentence-silence` | Silence duration between sentences (seconds) |
| `--volume` | Output volume (default: 1.0) |
| `--no-normalize` | Disable automatic volume normalization |
| `--output-raw` | Output raw audio for streaming |
| `--data-dir` | Voice model directory |

### Phoneme Injection

Insert custom espeak-ng phonemes using `[[ ]]` syntax:

```bash
python3 -m piper -m en_US-lessac-medium -- 'I am [[ bˈætmæn ]]'
```

Get phonemes for a word:
```bash
espeak-ng -v en-us --ipa=3 -q batman
```

## Python API

The main class is `PiperVoice`. Load a model and synthesize:

### Basic Synthesis

```python
import wave
from piper import PiperVoice

# Load voice model
voice = PiperVoice.load("./en_US-lessac-medium.onnx")

# Synthesize to WAV file
with wave.open("output.wav", "wb") as wav_file:
    voice.synthesize_wav("Hello world!", wav_file)
```

### Streaming Audio (Real-Time)

```python
for chunk in voice.synthesize("This audio is streamed chunk by chunk."):
    # chunk.audio_int16_bytes contains raw 16-bit audio
    print(f"Received {len(chunk.audio_int16_bytes)} bytes")
```

### Customization with SynthesisConfig

```python
from piper import PiperVoice, SynthesisConfig

config = SynthesisConfig(
    volume=0.5,           # half volume
    length_scale=1.5,     # 50% slower
    noise_scale=0.667,    # audio variation
    noise_w_scale=0.8,    # speaking variation
    normalize_audio=True  # auto-normalize
)

voice.synthesize_wav(text, wav_file, syn_config=config)
```

### macOS Playback

```python
import subprocess
import tempfile

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    with wave.open(tmp.name, "wb") as wav_file:
        voice.synthesize_wav("Hello!", wav_file)
    subprocess.run(["afplay", tmp.name])
```

### Key Methods

| Method | Description |
|--------|-------------|
| `PiperVoice.load(model_path)` | Load ONNX model (static) |
| `voice.synthesize_wav(text, wav_file)` | Write to WAV file |
| `voice.synthesize(text)` | Stream audio chunks |

## Character Voices on HuggingFace

Community-trained fictional character voices:

- [campwill/HAL-9000-Piper-TTS](https://huggingface.co/campwill/HAL-9000-Piper-TTS) - HAL 9000 from 2001
- [OpenVoiceOS PiperTTS Collection](https://huggingface.co/collections/OpenVoiceOS/pipertts-voices) - Various voices
- [Thorsten-Voice/Piper](https://huggingface.co/Thorsten-Voice/Piper) - German voice

Training custom voices requires 20+ hours of audio data.

## Performance Note

The CLI reloads models on each invocation. For production use, consider the web server or Python API for better performance.

## Training Custom Voices

Training checkpoints available at: [rhasspy/piper-checkpoints](https://huggingface.co/datasets/rhasspy/piper-checkpoints)

Training guide: [TRAINING.md](https://github.com/OHF-Voice/piper1-gpl/blob/main/TRAINING.md)

## License

Piper itself is MIT licensed, but individual voice models may have different licenses. Check each voice's MODEL_CARD for licensing details.

## Resources

- Voice samples: https://rhasspy.github.io/piper-samples/
- Hugging Face models: https://huggingface.co/rhasspy/piper-voices
- GitHub: https://github.com/OHF-Voice/piper1-gpl
