---
source: https://huggingface.co/rhasspy/piper-voices
additional_sources:
  - https://huggingface.co/campwill/HAL-9000-Piper-TTS
  - https://huggingface.co/DavesArmoury/GLaDOS_TTS
  - https://huggingface.co/jgkawell/jarvis
  - https://huggingface.co/systemofapwne/piper-de-glados
fetched: 2026-02-16
---

# Piper TTS Character Voices

Fictional character voices trained for Piper TTS, available on HuggingFace.

## Character Voices

| Character | Source | HuggingFace URL | Language | Use |
|-----------|--------|-----------------|----------|:---:|
| **HAL 9000** | 2001: A Space Odyssey | [campwill/HAL-9000-Piper-TTS](https://huggingface.co/campwill/HAL-9000-Piper-TTS) | English | ✓ |
| **GLaDOS** | Portal | [DavesArmoury/GLaDOS_TTS](https://huggingface.co/DavesArmoury/GLaDOS_TTS) | English | ✓ |
| **GLaDOS (German)** | Portal | [systemofapwne/piper-de-glados](https://huggingface.co/systemofapwne/piper-de-glados) | German | |
| **JARVIS** | Iron Man | [jgkawell/jarvis](https://huggingface.co/jgkawell/jarvis) | English | ✓ |

## Voice Collections

| Collection | URL | Description |
|------------|-----|-------------|
| Official Piper Voices | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) | 40+ languages, standard voices |
| OpenVoiceOS | [OpenVoiceOS/pipertts-voices](https://huggingface.co/collections/OpenVoiceOS/pipertts-voices) | Community collection |
| Training Checkpoints | [rhasspy/piper-checkpoints](https://huggingface.co/datasets/rhasspy/piper-checkpoints) | For training custom voices |

## Download & Install

```bash
# Download voice files
wget https://huggingface.co/campwill/HAL-9000-Piper-TTS/resolve/main/hal9000.onnx
wget https://huggingface.co/campwill/HAL-9000-Piper-TTS/resolve/main/hal9000.onnx.json

# Move to piper voices directory
mv hal9000.onnx* ~/.local/share/piper-tts/voices/

# Test
psn tts speak "I'm sorry Dave, I'm afraid I can't do that." --voice hal9000
```

## Usage with psn CLI

```bash
# List installed voices
psn tts voices

# Speak with specific voice
psn tts speak "The cake is a lie" --voice glados

# Download a voice
psn tts download en_US-lessac-medium
```

## Related Projects

- [GLaDOSify](https://github.com/giers10/GLaDOSify) - GUI that rewrites text in GLaDOS style + speaks with Piper
- [Home Assistant Piper](https://www.home-assistant.io/integrations/piper/) - Piper TTS integration

## Training Your Own

Requires ~20+ hours of clean audio. See [TRAINING.md](https://github.com/OHF-Voice/piper1-gpl/blob/main/TRAINING.md).
