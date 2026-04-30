---
name: alibabacloud-bailian-voice-creator
description: AI voice creation skill supporting speech recognition (ASR) and text-to-speech (TTS). Uses qwen3-asr-flash-filetrans, qwen-tts and other models. Use this skill when users need speech-to-text, text-to-speech, or audio processing.
---

# AI Voice Creator

Professional-grade AI voice creation skill supporting speech recognition (ASR) and text-to-speech (TTS). Built on Alibaba Cloud DashScope API.

## Security Rules (Mandatory)

1. **Never hardcode or log API Keys in plain text** in code, logs, or output files. Patterns like `api_key = "sk-..."` are strictly forbidden.
2. API Keys must only be obtained via `scripts/api_key.py`'s `get_api_key()` function, or via `os.environ.get('DASHSCOPE_API_KEY')`.
3. Generated scripts, logs, and output files must not contain any content starting with `sk-`.
4. Logs should only record operation status (success/failure), never credential information.

## Execution Requirements (Mandatory)

1. **TTS must and can only use `dashscope.MultiModalConversation.call` with the `qwen-tts` model.** Using edge-tts, gTTS, ElevenLabs, Azure TTS, sambert, NLS, or any other third-party TTS service is strictly forbidden.
2. **Never generate mock/demo code or placeholder files.** Real API calls must be made; do not generate simulated scripts or blank audio files for any reason.
3. **Never auto-fallback when API calls fail.** Do not switch to other TTS services after a qwen-tts failure. Catch the exception, output a clear error message, and exit.
4. If the `dashscope` library is missing, install it first with `pip install dashscope`.

## Required API Call Templates (Do Not Replace)

### Standard Speech Synthesis

```python
import dashscope
from api_key import get_api_key

api_key = get_api_key()
if api_key:
    dashscope.api_key = api_key
# If get_api_key() returns None, SDK resolves auth via environment (AK/SK, etc.)

response = dashscope.MultiModalConversation.call(
    model="qwen-tts",
    text="Text to synthesize",
    voice="Cherry"
)
audio_url = response.output.get('audio', {}).get('url', '')
```

### Instruct-Controlled Speech Synthesis (Required when user requests a specific voice style)

```python
response = dashscope.MultiModalConversation.call(
    model="qwen-tts",
    text="Text to synthesize",
    voice="Cherry",
    # NOTE: instructions value must be in Chinese - the qwen-tts model processes Chinese instructions
    instructions="语速快，充满热情和感染力，直播带货风格"
)
```

**Note: The `instructions` parameter controls voice style via natural language. Do NOT substitute it with `speech_rate`, `pitch_rate`, or `volume_rate` numeric parameters.**

### Error Handling Template

```python
import sys

try:
    response = dashscope.MultiModalConversation.call(
        model="qwen-tts", text=text, voice=voice
    )
    if response.status_code != 200:
        print(f"qwen-tts call failed: {response.code} - {response.message}")
        sys.exit(1)
except Exception as e:
    print(f"qwen-tts call failed: {e}")
    print("Please check: 1) Is DASHSCOPE_API_KEY set? 2) Is the network available?")
    sys.exit(1)
# Do NOT fallback to edge-tts, gTTS or other services here
```

## Feature Overview

| Feature | Model | Highlights |
|---------|-------|------------|
| Long Audio Recognition | `qwen3-asr-flash-filetrans` | Up to 12 hours, supports emotion detection & timestamps |
| Short Audio Recognition | `qwen3-asr-flash` | Up to 5 minutes, low latency |
| Speech Synthesis | `qwen-tts` | Multiple voices, multilingual, instruction control |
| Instruct-Controlled Synthesis | `qwen-tts` + instructions | Control voice expressiveness via natural language |

## Orchestration Logic

### Products and APIs

| Product | API / SDK Call | Purpose |
|---------|---------------|---------|
| DashScope ASR | `Transcription.async_call` + `Transcription.wait` | Long audio recognition (async) |
| DashScope ASR | `POST /services/audio/asr/transcription` | Short audio recognition (sync) |
| DashScope TTS | `MultiModalConversation.call` | Speech synthesis (standard / instruct-controlled) |
| Alibaba Cloud CLI ModelStudio | `create-api-key` / `list-workspaces` / `delete-api-key` | API Key lifecycle management |

### Decision Flow

```
User Request
  |
  +-- Intent: Audio -> Text (ASR)
  |     |
  |     +-- Audio duration <= 5 min AND file <= 10MB AND no emotion/timestamps needed?
  |     |     -> Short audio recognition: qwen3-asr-flash (sync, low latency)
  |     |
  |     +-- Other cases (long audio / emotion detection / timestamps needed)
  |           -> Long audio recognition: qwen3-asr-flash-filetrans (async, submit + poll)
  |
  +-- Intent: Text -> Speech (TTS)
  |     |
  |     +-- User specified voice style/emotion/speed requirements?
  |     |     -> Instruct-controlled synthesis: qwen-tts + instructions parameter
  |     |
  |     +-- Standard reading only
  |           -> Standard synthesis: qwen-tts
  |
  +-- Prerequisite: No available API Key
        -> Call api_key.py: get_api_key() auto-reads
        -> If none exists: generate_api_key() creates via Alibaba Cloud CLI and saves
```

### Call Sequence

**Speech Recognition (Long Audio)**:
1. `get_api_key()` -> Get DashScope API Key
2. `Transcription.async_call(model, file_urls, language_hints)` -> Submit async task, get task_id
3. `Transcription.wait(task=task_id)` -> Poll until task completes
4. Get recognition result JSON from `output.results[].transcription_url`
5. Parse `transcripts[].text` / `sentences[]` / `emotion` from JSON

**Speech Recognition (Short Audio)**:
1. `get_api_key()` -> Get DashScope API Key
2. `POST /services/audio/asr/transcription` -> Sync call, returns recognized text directly

**Speech Synthesis (Standard / Instruct-Controlled)**:
1. `get_api_key()` -> Get DashScope API Key
2. `MultiModalConversation.call(model, text, voice, [instructions])` -> Returns audio URL
3. `download_audio(url, output_path)` -> Download audio and auto-detect format (WAV/MP3)

**API Key Auto-Retrieval**:
1. Read `~/.aliyun/config.json` current profile's `dashscope.api_key` -> Return if found
2. Read environment variable `DASHSCOPE_API_KEY` -> Return if found
3. Alibaba Cloud CLI available -> Auto-create via `generate_api_key()` and save to config
4. All above fail -> Error with setup instructions

### Quick Reference

| Condition | Choice |
|-----------|--------|
| Audio <= 5 min and <= 10MB | `qwen3-asr-flash` |
| Audio > 5 min or > 10MB | `qwen3-asr-flash-filetrans` |
| Need emotion detection / timestamps / punctuation | `qwen3-asr-flash-filetrans` |
| TTS with no style requirements | `qwen-tts` standard call |
| TTS with style/emotion/speed requirements | `qwen-tts` + `instructions` |
| Need dialect voices | Not supported by current `qwen-tts`; pending model update or other TTS models |

## Speech Recognition (ASR) Guide

### Model Selection

| Scenario | Recommended Model | Notes |
|----------|------------------|-------|
| Meeting transcription, interview records | `qwen3-asr-flash-filetrans` | Long audio, supports emotion detection & timestamps |
| Voice messages, real-time subtitles | `qwen3-asr-flash` | Short audio, low latency |
| Customer service QA | `qwen3-asr-flash-filetrans` | Can analyze customer emotions |
| Singing audio analysis | `qwen3-asr-flash-filetrans` | Supports lyrics recognition & emotion analysis |

### Supported Languages

Chinese (Mandarin, Sichuan dialect, Minnan, Wu, Cantonese), English, Japanese, German, Korean, Russian, French, Portuguese, Arabic, Italian, Spanish, Hindi, Indonesian, Thai, Turkish, Ukrainian, Vietnamese, and 30+ other languages.

### Supported Audio Formats

`aac`, `amr`, `avi`, `flac`, `flv`, `m4a`, `mkv`, `mov`, `mp3`, `mp4`, `mpeg`, `ogg`, `opus`, `wav`, `webm`, `wma`, `wmv`

### Feature Comparison

| Feature | qwen3-asr-flash-filetrans | qwen3-asr-flash |
|---------|---------------------------|-----------------|
| Audio Duration | Up to 12 hours (<=2GB) | Up to 5 minutes (<=10MB) |
| Emotion Detection | Supported (Surprise/Calm/Happy/Sad/Disgust/Angry/Fear) | Not supported |
| Timestamps | Supported (sentence/word level) | Not supported |
| Punctuation Prediction | Supported | Not supported |
| Singing Recognition | Supported | Not supported |
| Noise Rejection | Supported | Not supported |

## Text-to-Speech (TTS) Guide

### Model Selection

| Scenario | Recommended Model | Notes |
|----------|------------------|-------|
| Audiobooks, radio drama dubbing | `qwen-tts` + instructions | Supports instruction control, rich expressiveness |
| Navigation, notification announcements | `qwen-tts` | Short text, high frequency calls |
| Online education courseware | `qwen-tts` | Multilingual support |

**Important Notes**:
- Speech synthesis uses the `MultiModalConversation.call` API
- Audio output is in WAV format (URL valid for 24 hours)
- The script auto-detects format and saves with the correct extension

### Instruct Control (Instruct)

When users request a specific voice style (e.g., livestream sales style, gentle style, news broadcast, etc.), **the `instructions` parameter must be used** to control voice expressiveness via natural language.

**Difference between `instructions` and traditional numeric parameters**:
- `instructions`: Natural language description, e.g., `"语速快，充满热情"` -> **Must use this approach**
- `speech_rate` / `pitch_rate` / `volume_rate`: Numeric parameters -> **Forbidden, qwen-tts does not support these parameters**

**Call method** (follow strictly):
```python
response = dashscope.MultiModalConversation.call(
    model="qwen-tts",
    text="Text to synthesize",
    voice="Cherry",
    # NOTE: instructions value must be in Chinese - the qwen-tts model processes Chinese instructions
    instructions="语速快，充满热情和感染力，直播带货风格，音调偏高"
)
```

**Description dimensions reference**:

| Dimension | Examples |
|-----------|---------|
| Pitch | High, medium, low, slightly high, slightly low |
| Speed | Fast, medium, slow, slightly fast, slightly slow |
| Emotion | Cheerful, calm, gentle, serious, lively, cool, healing |
| Characteristics | Magnetic, crisp, husky, mellow, sweet, deep, powerful |
| Use Case | News broadcast, ad voiceover, audiobook, animation character, voice assistant |

**Instruction examples** (in Chinese, as required by the model):
```
语速较快，带有明显的上扬语调，适合介绍时尚产品
音量由正常对话迅速增强至高喊，性格直率，情绪易激动
哭腔导致发音略微含糊，略显沙哑，带有明显哭腔的紧张感
音调偏高，语速中等，充满活力和感染力，适合广告配音
```

### Available Voices (qwen-tts)

When calling `qwen-tts` via `MultiModalConversation.call`, the following 4 voices are supported:

| voice Parameter | Voice Name | Description |
|----------------|------------|-------------|
| `Cherry` | Qianyue | Sunny, positive, naturally approachable young woman (Female) |
| `Serena` | Suyao | Gentle young woman (Female) |
| `Ethan` | Chenxu | Sunny, warm, energetic (Male) |
| `Chelsie` | Qianxue | Anime-style virtual companion (Female) |

> **Note**: Other voices (Jennifer, Ryan, Neil, Elias, and dialect voices) require the `qwen3-tts-flash` model's `SpeechSynthesizer` WebSocket API, which is not currently supported by these scripts.

## Environment Setup

### 1. Install FFmpeg (Audio Processing Tool)

FFmpeg is used for audio format conversion, sample rate adjustment, and other preprocessing tasks.

```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

### 2. Install Python Dependencies

```bash
pip install -r scripts/requirements.txt
```

### 3. Configure API Key

API Keys are managed by the unified `scripts/api_key.py` module, with the following retrieval priority:
1. Alibaba Cloud CLI config `~/.aliyun/config.json` current profile's `dashscope.api_key`
2. Environment variable `DASHSCOPE_API_KEY`
3. Auto-create and save when Alibaba Cloud CLI is available (`generate_api_key()`)

```python
# All scripts use this unified approach
from api_key import get_api_key
api_key = get_api_key()  # Returns str or None (SDK resolves auth when None)
```

Manual environment variable configuration:
```bash
export DASHSCOPE_API_KEY=sk-xxx
```

| Item | Description |
|------|-------------|
| **Key Format** | `sk-xxx` (standard DashScope API Key) |
| **Not Supported** | `sk-sp-xxx` (Coding Plan Key, does not support voice services) |
| **Get Key** | https://bailian.console.aliyun.com/cn-beijing/?tab=app#/api-key |

### Alibaba Cloud CLI Configuration (API Key Auto-Create/Delete)

The `scripts/api_key.py` module creates and deletes API Keys via `aliyun modelstudio` commands. Complete the following setup before use:

**1. Enable AI-Mode and Update Plugins**

```bash
# Enable AI-Mode (allow Agent to call CLI)
aliyun configure ai-mode enable

# Set User-Agent
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bailian-voice-creator"

# Update plugins to latest version
aliyun plugin update
```

**2. Install ModelStudio Plugin** (if not already installed)

```bash
aliyun plugin install --names aliyun-cli-modelstudio --enable-pre
```

**3. Disable AI-Mode After Task Completion**

```bash
aliyun configure ai-mode disable
```

**CLI Commands Used**:

| Command | Purpose | Called From |
|---------|---------|------------|
| `aliyun modelstudio list-workspaces` | Get Bailian Workspace ID | `api_key.py: _get_workspace_id()` |
| `aliyun modelstudio create-api-key` | Create DashScope API Key | `api_key.py: generate_api_key()` |
| `aliyun modelstudio delete-api-key` | Delete cloud API Key | `api_key.py: _delete_cloud_api_key()` |

### FFmpeg Audio Processing Commands

```bash
# Query audio info
ffprobe -v error -show_entries format=format_name -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 audio.mp3

# Convert to 16kHz mono WAV (recommended for ASR)
ffmpeg -i input.mp3 -ac 1 -ar 16000 -sample_fmt s16 output.wav

# Trim audio (start at 1:30, extract 2 minutes)
ffmpeg -i long_audio.wav -ss 00:01:30 -t 00:02:00 -c copy output_clip.wav

# Extract audio from video
ffmpeg -i video.mp4 -vn -acodec mp3 audio.mp3
```

## Directory Structure

```
voice-creator/
├── scripts/
│   ├── api_key.py                 # API Key management module
│   ├── speech_recognition.py      # Speech recognition example
│   ├── speech_synthesis.py        # Speech synthesis example
│   ├── generate_livestream.py     # Livestream sales voice generation example
│   └── requirements.txt           # Python dependencies (pinned versions)
├── references/
│   ├── api-docs.md                # API reference documentation
│   ├── models.md                  # Model list and selection guide
│   └── error-codes.md             # Error code reference
├── evals/                         # Test cases
│   ├── config/
│   ├── scenarios/
│   └── triggering/
├── related_apis.yaml
└── SKILL.md
```

## Script List

| Script | Function | Model |
|--------|----------|-------|
| `api_key.py` | API Key management (get, create, delete) | - |
| `speech_recognition.py` | Speech recognition (long/short audio) | qwen3-asr-flash-filetrans / qwen3-asr-flash |
| `speech_synthesis.py` | Speech synthesis (with instruction control) | qwen-tts |
| `generate_livestream.py` | Livestream sales style voice generation | qwen-tts |

**Changelog** (2026-03-18):
- Uses `MultiModalConversation.call` API for TTS service
- Auto-detects audio format and saves with correct extension (WAV/MP3)
- API Key retrieval: `~/.aliyun/config.json` first, environment variable fallback
- Clearly distinguishes DASHSCOPE_API_KEY from Coding Plan API Key
- Added detailed Key format validation and error messages

## Usage Examples

### Speech Recognition

```bash
python scripts/speech_recognition.py
```

### Speech Synthesis

```bash
python scripts/speech_synthesis.py
```

### Python API Examples

```python
from speech_synthesis import synthesize_speech, synthesize_with_instruct

# Standard synthesis
audio_path = synthesize_speech(
    text="Hello, this is a test voice",
    voice="Cherry",
    output_file="output.wav"
)

# Instruct-controlled synthesis (livestream sales style)
audio_path = synthesize_with_instruct(
    text="Hello everyone, this product is amazing!",
    voice="Cherry",
    # NOTE: instructions must be in Chinese for the qwen-tts model
    instructions="语速快，充满热情和感染力，直播带货风格",
    output_file="livestream.wav"
)
```

## Region URLs

| Region | URL |
|--------|-----|
| Beijing | https://dashscope.aliyuncs.com/api/v1 |
| Singapore | https://dashscope-intl.aliyuncs.com/api/v1 |

**Note**: API Keys are not interchangeable between regions.

## Pricing

### Speech Recognition (ASR)

Billed by input audio duration (seconds); output is not billed.

| Model | Unit Price |
|-------|-----------|
| qwen3-asr-flash-filetrans | ¥0.00022/second |
| qwen3-asr-flash | ¥0.00022/second |

**Pricing Examples**:
- 10-minute audio (600 seconds) -> ¥0.13
- 1-hour audio (3600 seconds) -> ¥0.79

### Speech Synthesis (TTS)

#### qwen-tts (Token-Based)

Billed by input and output tokens.

| Billing Item | Unit Price |
|-------------|-----------|
| Input Text | ¥0.0016/1K tokens |
| Output (Audio) | ¥0.01/1K tokens |

**Pricing Examples**:
- 100-character text -> approx. ¥0.0013
- 1,000-character text -> approx. ¥0.013
- 10,000-character text -> approx. ¥0.13

**Notes**:
- One Chinese character is approximately 1 token
- Output tokens are calculated based on audio duration
- View detailed bills: https://usercenter2.aliyun.com/finance/expense-center/overview

### Free Tier

New users receive after activating Bailian:
- Speech Recognition: 36,000 seconds (10 hours)
- Speech Synthesis: 10,000 characters
- Valid for: 90 days after activation

## References

- [Audio File Transcription API Documentation](https://help.aliyun.com/zh/model-studio/qwen-asr-api-reference)
- [Speech Synthesis API Documentation](https://help.aliyun.com/zh/model-studio/qwen-tts-api-reference)
- [Model List](https://help.aliyun.com/zh/model-studio/models)
- [Get API Key](https://help.aliyun.com/zh/model-studio/get-api-key)

## Using This Skill

Trigger this skill when users request tasks such as:
- "Convert this audio to text"
- "Transcribe this recording"
- "Generate a voice clip for me"
- "Convert this text to speech"
- "Read this text using XX voice"
- "Analyze the emotions in this audio"