# Audio Operations Parameter Reference

Detailed parameter specifications for audio processing operations. Audio operations use slash notation (e.g., `audio/convert`, `audio/concat`). Only one audio operation can be specified per request — no chaining with other video/audio/image operations.

## Table of Contents

- [audio/convert — Audio Transcoding](#audioconvert--audio-transcoding)
- [audio/concat — Audio Concatenation](#audioconcat--audio-concatenation)
- [audio/info — Audio Metadata](#audioinfo--audio-metadata)

---

## audio/convert — Audio Transcoding

Transcode audio to a different format, bitrate, or sample rate. **Asynchronous ONLY** — requires `--async` flag.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ss` | int | Start time in milliseconds |
| `t` | int | Duration in milliseconds |
| `f` | string | Output format (**required**): `mp3`, `aac`, `flac`, `oga`, `ac3`, `opus`, `amr` |
| `ar` | int | Audio sample rate in Hz (e.g., 44100, 48000) |
| `ac` | int | Audio channels (1-8) |
| `aq` | int | Audio quality (0-100). Mutually exclusive with `ab` |
| `ab` | int | Audio bitrate in bps (e.g., 128000, 192000). Mutually exclusive with `aq` |
| `abopt` | int | Audio bitrate optimization: `0` = exact, `1` = lower, `2` = higher |
| `adepth` | int | Audio bit depth: `16` or `24`. FLAC output only |

> **Note**: `aq` and `ab` are mutually exclusive. Use `aq` for quality-based encoding or `ab` for bitrate-based encoding.

**Examples:**

```
audio/convert:f=aac,ab=96000,ar=48000,ac=2
audio/convert:f=mp3,ab=192000,ar=44100,ac=2
audio/convert:f=mp3,aq=90,ar=44100,ac=2
audio/convert:f=flac,ar=48000,ac=2,adepth=24
audio/convert:f=opus,ab=64000,ar=48000,ac=1
audio/convert:f=aac,ss=5000,t=30000,ab=128000
```

---

## audio/concat — Audio Concatenation

Concatenate multiple audio files into one. **Asynchronous ONLY** — requires `--async` flag.

The first audio file is specified via `--source`. Additional audio files are appended using `/pre` (before main) and `/sur` (after main) segments with their parameters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `f` | string | Output format (**required**): `mp3`, `aac`, `flac`, `oga`, `ac3`, `opus`, `amr` |
| `ar` | int | Audio sample rate in Hz |
| `ac` | int | Audio channels (1-8) |
| `aq` | int | Audio quality (0-100) |
| `ab` | int | Audio bitrate in bps |
| `abopt` | int | Audio bitrate optimization: `0`/`1`/`2` |
| `align` | int | Alignment index |
| `adepth` | int | Audio bit depth: `16` or `24`. FLAC output only |

**Segment syntax** (for additional audio files):
- `/pre,o_<base64_key>,ss_<ms>,t_<ms>` — prepend segment
- `/sur,o_<base64_key>,ss_<ms>,t_<ms>` — append segment

Where `<base64_key>` is the URL-safe Base64-encoded OSS object key.

**Examples:**

```
audio/concat:f=mp3,ab=192000,ar=44100,ac=2,align=0
audio/concat:f=aac,ab=128000,ar=48000,ac=2
audio/concat:f=flac,ar=48000,ac=2,adepth=24
```

---

## audio/info — Audio Metadata

Extract audio metadata including duration, format, bitrate, stream information. Returns JSON. Synchronous processing. No parameters required.

> **Note**: Anonymous access is NOT supported for audio/info.

**Example:**

```
audio/info
```

**Sample response data:**

```json
{
  "Format": {
    "Duration": "245.3",
    "Size": "3920000",
    "FormatName": "mp3",
    "BitRate": "128000"
  },
  "Streams": {
    "AudioStream": [{
      "CodecName": "mp3",
      "SampleRate": "44100",
      "Channels": "2",
      "BitRate": "128000"
    }]
  }
}
```

---

> Parameter specifications in this document are derived from the [Alibaba Cloud OSS Audio Processing documentation](https://help.aliyun.com/zh/oss/user-guide/audio-and-video-processing) and are reproduced here for quick reference.
