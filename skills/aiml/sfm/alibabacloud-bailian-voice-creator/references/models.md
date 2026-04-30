# DashScope Voice Model List

## Speech Recognition Models (ASR)

| Model | Description | Max Duration | File Size | Features |
|-------|-------------|-------------|-----------|----------|
| qwen3-asr-flash-filetrans | Long audio file transcription | 12 hours | <=2GB | Emotion recognition, timestamps, punctuation prediction, singing recognition |
| qwen3-asr-flash | Short audio real-time recognition | 5 minutes | <=10MB | Low latency, synchronous response |

## Speech Synthesis Models (TTS)

| Model | Description | Voice Count | Features |
|-------|-------------|-------------|----------|
| qwen3-tts-flash | Standard speech synthesis | 40+ | Multi-language, multi-dialect, streaming output |
| qwen3-tts-instruct-flash | Instruct-controlled synthesis | 40+ | Natural language control of voice expressiveness |

---

## Model Selection Guide

### Speech Recognition - Long Audio (qwen3-asr-flash-filetrans)

**Use Cases**:
- Meeting transcription
- Interview/conversation processing
- Customer service call quality inspection
- Podcast/livestream content extraction
- Course/lecture subtitle generation
- Song lyrics recognition

**Features**:
- Supports audio up to 12 hours
- Sentence/word-level timestamp alignment
- Emotion recognition (7 emotion types)
- Intelligent punctuation prediction
- Filler word filtering ("um", "uh", etc.)
- Noise speech rejection
- Singing content recognition

**Tips**:
- Set `language_hints` to improve recognition accuracy
- Enable `disfluency_removal_enabled` to filter filler words
- Enable `timestamp_alignment_enabled` when timestamps are needed
- Enable `emotion_recognition_enabled` for customer service QA scenarios

### Speech Recognition - Short Audio (qwen3-asr-flash)

**Use Cases**:
- Voice message to text
- Real-time subtitles
- Voice search
- Voice command recognition
- Short video/audio content extraction

**Features**:
- Synchronous response, low latency
- Up to 5 minutes
- Lightweight API call

**Tips**:
- Suitable for scenarios requiring fast responses
- Does not support emotion recognition or timestamps
- Use the long audio model for audio exceeding 5 minutes

### Speech Synthesis - Standard (qwen3-tts-flash)

**Use Cases**:
- Navigation/notification announcements
- Online education courseware
- News article reading
- System notification sounds
- Batch text-to-speech conversion

**Features**:
- 40+ preset voices
- Multi-language/dialect support
- Streaming output
- Adjustable speech rate, volume, and pitch

**Tips**:
- `speech_rate` adjusts speech speed (0.5-2.0)
- `pitch` adjusts voice pitch (0.5-2.0)
- `volume` adjusts volume (0-100)
- Choose appropriate `sample_rate` to balance quality and file size

### Speech Synthesis - Instruct Control (qwen3-tts-instruct-flash)

**Use Cases**:
- Audiobook narration
- Radio drama characters
- Advertisement voiceover
- Game/animation characters
- Emotionally expressive voice assistants

**Features**:
- Natural language control of voice style
- Fine-grained emotional expression
- Character role-playing capability
- Dynamic intonation variation

**Tips**:
- Instructions should be specific and clear (speed, emotion, purpose)
- Multiple descriptive dimensions can be combined
- Suitable for scenarios requiring rich expressiveness

---

## Feature Comparison

### ASR Feature Matrix

| Feature | qwen3-asr-flash-filetrans | qwen3-asr-flash |
|---------|---------------------------|-----------------|
| Audio Duration | Up to 12 hours | Up to 5 minutes |
| File Size | <=2GB | <=10MB |
| Emotion Recognition | Supported | Not supported |
| Timestamps | Supported (sentence/word level) | Not supported |
| Punctuation Prediction | Supported | Not supported |
| Singing Recognition | Supported | Not supported |
| Noise Rejection | Supported | Not supported |
| Filler Word Filtering | Supported | Not supported |
| Call Method | Asynchronous (polling required) | Synchronous (instant response) |

### TTS Feature Matrix

| Feature | qwen3-tts-flash | qwen3-tts-instruct-flash |
|---------|-----------------|--------------------------|
| Voice Count | 40+ | 40+ |
| Speed Control | Supported (parameter) | Supported (instruction) |
| Pitch Control | Supported (parameter) | Supported (instruction) |
| Volume Control | Supported (parameter) | Supported (instruction) |
| Emotion Control | Not supported | Supported (instruction) |
| Character Role-playing | Not supported | Supported (instruction) |
| Streaming Output | Supported | Supported |

---

## Emotion Recognition Types

Long audio recognition (qwen3-asr-flash-filetrans) supports the following emotion types:

| Emotion (Chinese) | English | Description |
|-------------------|---------|-------------|
| surprise | surprise | Unexpected, shocked |
| neutral | neutral | Neutral, calm |
| happy | happy | Joyful, satisfied |
| sad | sad | Sorrowful, down |
| disgust | disgust | Aversion, dissatisfied |
| angry | angry | Angry, agitated |
| fear | fear | Afraid, anxious |

---

## Model Limitations

### ASR Limitations

| Limitation | qwen3-asr-flash-filetrans | qwen3-asr-flash |
|------------|---------------------------|-----------------|
| Max Duration | 12 hours | 5 minutes |
| Max File Size | 2GB | 10MB |
| Files per Request | 100 | 1 |
| Supported Formats | 17 types | 17 types |

### TTS Limitations

| Limitation | Value |
|------------|-------|
| Max Characters per Request | 10,000 |
| Supported Output Formats | wav, mp3, pcm |
| Sample Rate Range | 8kHz - 48kHz |

---

## Changelog

- 2026-03-10: Initial version, includes qwen3-asr-flash, qwen3-asr-flash-filetrans, qwen3-tts-flash, qwen3-tts-instruct-flash model information
