# DashScope Voice API Documentation Reference

## API Endpoints

### Beijing Region
```
https://dashscope.aliyuncs.com/api/v1
```

### Singapore Region
```
https://dashscope-intl.aliyuncs.com/api/v1
```

**Note**: API Keys are not interchangeable between regions.

---

## Speech Recognition - Long Audio File Transcription

**Model**: `qwen3-asr-flash-filetrans`

**Endpoint**: `POST /services/audio/asr/filetrans`

**Request Example**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/services/audio/asr/filetrans' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "qwen3-asr-flash-filetrans",
    "input": {
        "file_urls": ["https://example.com/audio.mp3"]
    },
    "parameters": {
        "language_hints": ["zh", "en"],
        "disfluency_removal_enabled": true,
        "timestamp_alignment_enabled": true,
        "emotion_recognition_enabled": true,
        "punctuation_prediction_enabled": true
    }
}'
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file_urls | array | Yes | Audio file URL list (up to 100 per request) |
| language_hints | array | No | Language hints, e.g. ["zh", "en"] |
| disfluency_removal_enabled | boolean | No | Filter filler words ("um", "uh", etc.) |
| timestamp_alignment_enabled | boolean | No | Return sentence/word-level timestamps |
| emotion_recognition_enabled | boolean | No | Recognize emotions (surprise/neutral/happy/sad/disgust/angry/fear) |
| punctuation_prediction_enabled | boolean | No | Predict punctuation marks |

**Response Example**:
```json
{
    "request_id": "xxx",
    "output": {
        "task_id": "xxx",
        "task_status": "PENDING"
    }
}
```

**Task Result Query**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY"
```

**Result Response Example**:
```json
{
    "output": {
        "task_status": "SUCCEEDED",
        "results": [
            {
                "file_url": "https://example.com/audio.mp3",
                "transcription_url": "https://...",
                "transcription": {
                    "sentences": [
                        {
                            "text": "The weather is really nice today",
                            "emotion": "happy",
                            "begin_time": 0,
                            "end_time": 2500,
                            "words": [
                                {"text": "The", "begin_time": 0, "end_time": 200},
                                {"text": "weather", "begin_time": 200, "end_time": 600},
                                {"text": "is", "begin_time": 600, "end_time": 800},
                                {"text": "really", "begin_time": 800, "end_time": 1200},
                                {"text": "nice", "begin_time": 1200, "end_time": 1600},
                                {"text": "today", "begin_time": 1600, "end_time": 2500}
                            ]
                        }
                    ]
                }
            }
        ]
    }
}
```

**Official Documentation**: https://help.aliyun.com/zh/model-studio/qwen-asr-api-reference

---

## Speech Recognition - Short Audio Real-time Recognition

**Model**: `qwen3-asr-flash`

**Endpoint**: `POST /services/audio/asr/flash` (synchronous)

**Request Example**:
```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/services/audio/asr/flash' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "qwen3-asr-flash",
    "input": {
        "file_urls": ["https://example.com/short_audio.wav"]
    },
    "parameters": {}
}'
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file_urls | array | Yes | Audio file URL list |

**Response Example**:
```json
{
    "output": {
        "text": "Hello, how can I help you?"
    }
}
```

**Limitations**:
- Audio duration: up to 5 minutes
- File size: up to 10MB
- Returns results synchronously, no polling required

---

## Speech Synthesis - Standard Synthesis

**Model**: `qwen3-tts-flash`

**Endpoint**: `POST /services/audio/tts/` (WebSocket streaming)

**Request Example (Python SDK)**:
```python
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

dashscope.api_key = "sk-xxx"

synthesizer = SpeechSynthesizer(
    model="qwen3-tts-flash",
    voice="Cherry",
    speech_rate=1.0,
    format="wav"
)

audio = synthesizer.call("The weather is really nice today, bright and sunny.")

with open("output.wav", "wb") as f:
    f.write(audio)
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | Fixed as "qwen3-tts-flash" |
| voice | string | Yes | Voice name, e.g. "Cherry", "Ethan" |
| speech_rate | float | No | Speech rate multiplier [0.5, 2.0], default 1.0 |
| format | string | No | Output format: wav, mp3, pcm |
| sample_rate | int | No | Sample rate: 8000, 16000, 22050, 24000, 44100, 48000 |
| volume | int | No | Volume [0, 100], default 50 |
| pitch | float | No | Pitch [0.5, 2.0], default 1.0 |

**Official Documentation**: https://help.aliyun.com/zh/model-studio/qwen-tts-api-reference

---

## Speech Synthesis - Instruct-Controlled Synthesis

**Model**: `qwen3-tts-instruct-flash`

**Endpoint**: `POST /services/audio/tts/` (WebSocket streaming)

**Request Example (Python SDK)**:
```python
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

dashscope.api_key = "sk-xxx"

synthesizer = SpeechSynthesizer(
    model="qwen3-tts-instruct-flash",
    voice="Cherry"
)

audio = synthesizer.call(
    text="The weather is really nice today, bright and sunny.",
    instruct="语速较快，充满活力，适合广告配音"  # NOTE: instruct value must be in Chinese
)

with open("output.wav", "wb") as f:
    f.write(audio)
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | Fixed as "qwen3-tts-instruct-flash" |
| voice | string | Yes | Voice name |
| text | string | Yes | Text to synthesize |
| instruct | string | No | Natural language instruction to control voice style (must be in Chinese) |

**Instruction Examples**:
```
语速较快，带有明显的上扬语调，适合介绍时尚产品
(Fast pace, with noticeable rising intonation, suitable for fashion product introductions)

音量由正常对话迅速增强至高喊，性格直率，情绪易激动
(Volume quickly rises from normal conversation to shouting, straightforward personality, easily excited)

哭腔导致发音略微含糊，略显沙哑，带有明显哭腔的紧张感
(Crying tone causes slightly slurred pronunciation, slightly hoarse, with noticeable tense sobbing)

音调偏高，语速中等，充满活力和感染力，适合广告配音
(Higher pitch, medium pace, full of energy and charisma, suitable for advertising voiceover)
```

---

## Voice List

### General Voices

| voice Parameter | Chinese Name (Pinyin) | Gender | Description |
|-----------------|----------------------|--------|-------------|
| Cherry | Qianyue | Female | Sunny, positive, naturally approachable young woman |
| Serena | Suyao | Female | Gentle and soft-spoken young woman |
| Ethan | Chenxu | Male | Sunny, warm, and energetic |
| Chelsie | Qianxue | Female | Anime-style virtual companion |
| Jennifer | Zhennifu | Female | Brand-level, cinematic American English female voice |
| Ryan | Tiancha | Male | Rhythm-packed, dramatic flair |
| Neil | Awen | Male | Professional news anchor |
| Elias | Mojiangshi | Female | Knowledge explainer, easy to understand |
| Olivia | Aoliweiya | Female | Gentle as water, clean and pure |
| Emily | Aimili | Female | Friendly and lively young woman |
| Holly | Heli | Female | Authentic Japanese broadcast |
| Angela | Anjila | Female | Authentic Korean broadcast |
| Bella | Beila | Female | Sweet but not cloying, natural and poised |

### Dialect Voices

| voice Parameter | Dialect | Gender | Description |
|-----------------|---------|--------|-------------|
| Jada | Shanghainese | Female | Energetic Shanghai lady |
| Dylan | Beijing dialect | Male | Young man from Beijing hutongs |
| Sunny | Sichuan dialect | Female | Sweet Sichuan girl |
| Rocky | Cantonese | Male | Humorous and witty |
| Peter | Tianjin dialect | Male | Tianjin crosstalk, professional straight man |

---

## Supported Audio Formats

**Input (ASR)**:
`aac`, `amr`, `avi`, `flac`, `flv`, `m4a`, `mkv`, `mov`, `mp3`, `mp4`, `mpeg`, `ogg`, `opus`, `wav`, `webm`, `wma`, `wmv`

**Output (TTS)**:
`wav`, `mp3`, `pcm`

---

## Supported Languages

**ASR Supported Languages**:
Chinese (Mandarin, Sichuan dialect, Hokkien, Wu dialect, Cantonese), English, Japanese, German, Korean, Russian, French, Portuguese, Arabic, Italian, Spanish, Hindi, Indonesian, Thai, Turkish, Ukrainian, Vietnamese, and 30+ more languages.

**TTS Supported Languages**:
Chinese (including dialects), English, Japanese, Korean, and other major languages.

---

## Pricing

| Service | Pricing |
|---------|---------|
| Speech Recognition (ASR) | China CNY 0.00022/second |
| Speech Synthesis (TTS) | China CNY 0.8/10K characters |

---

## Task Status

| Status | Description |
|--------|-------------|
| PENDING | Task is waiting |
| RUNNING | Task is running |
| SUCCEEDED | Task completed successfully |
| FAILED | Task failed |
| CANCELLED | Task cancelled |
