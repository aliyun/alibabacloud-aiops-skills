# CLI Command Templates

This document provides ready-to-use CLI command templates.

---

## Environment Check

```bash
# Check CLI version
aliyun version

# Check credential configuration
aliyun sts GetCallerIdentity

# Check ICE plugin
aliyun ice help
```

---

## Media Registration

```bash
aliyun ice register-media-info \
  --input-url "oss://<bucket>/<object>" \
  --media-type video \
  --user-agent AlibabaCloud-Agent-Skills
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--input-url` | Yes | OSS address or VOD media address |
| `--media-type` | No | video/audio/image |
| `--title` | No | Title |
| `--overwrite` | No | Overwrite registered media |

**Returns**: `MediaId`

---

## Subtitle Extraction (CaptionExtraction)

> **CLI Format Key**: Use command name `submit-iproduction-job` + `--force`

### Method 1: Using OSS Path

```bash
aliyun ice submit-iproduction-job \
  --function-name CaptionExtraction \
  --input "Media=oss://<bucket>/<object> Type=OSS" \
  --biz-output "Media=oss://<bucket>/<output>.srt Type=OSS" \
  --job-params '{"lang":"ch","roi":[[0.5,1],[0,1]]}' \
  --name "<task_name>" \
  --force \
  --user-agent AlibabaCloud-Agent-Skills
```

### Method 2: Using MediaId (Registered Media)

```bash
aliyun ice submit-iproduction-job \
  --function-name CaptionExtraction \
  --input "Media=<mediaId> Type=MediaId" \
  --biz-output "Media=oss://<bucket>/<output>.srt Type=OSS" \
  --job-params '{"lang":"ch","roi":[[0.5,1],[0,1]]}' \
  --name "<task_name>" \
  --force \
  --user-agent AlibabaCloud-Agent-Skills
```

**CLI Format Notes**:
- Use command name: `submit-iproduction-job` (lowercase, `-` separator)
- Use lowercase parameter names: `--function-name`, `--input`, `--biz-output`, `--job-params`
- **`--input` and `--biz-output` format**: space-separated string `"Media=... Type=OSS"`, NOT JSON
- **`--job-params` format**: JSON string
- Add `--force` to skip plugin parameter validation
- **`--job-params` is required**, must include `roi` parameter

**JobParams Parameters**:
```json
{
  "fps": 5,
  "roi": [[0.5, 1], [0, 1]],
  "lang": "ch",
  "track": "main"
}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `roi` | **Yes** | Subtitle detection region `[[top,bottom],[left,right]]` |
| `lang` | No | `ch`(Chinese) / `en`(English) / `ch_ml`(Chinese-English mixed) |
| `fps` | No | Sampling frame rate [2,10], default 5 |
| `track` | No | `"main"` extract main subtitle track only |

---

## Query Subtitle Extraction Task

```bash
aliyun ice QueryIProductionJob \
  --JobId "<job_id>" \
  --force \
  --user-agent AlibabaCloud-Agent-Skills
```

| Status | Description |
|--------|-------------|
| Init | Initializing |
| Queuing | In queue |
| Analysing | Analyzing |
| Processing | Processing |
| Success | Success |
| Fail | Failed |

---

## Submit Video Translation Task

> **CLI Format Key**: JSON format parameters + `--region` to specify service region

### Mode 1: Subtitle-level Translation

```bash
aliyun ice submit-video-translation-job \
  --input-config '{"Type":"Video","Video":"https://<bucket>.oss-<region>.aliyuncs.com/<object>.mp4"}' \
  --output-config '{"MediaURL":"https://<bucket>.oss-<region>.aliyuncs.com/<output>.mp4"}' \
  --editing-config '{"SourceLanguage":"zh","TargetLanguage":"en","NeedSpeechTranslate":false,"NeedFaceTranslate":false,"TextSource":"OCR_ASR","SubtitleTranslate":{"OcrArea":"Auto","SubtitleConfig":{"Type":"Text","FontSize":48,"FontColor":"#ffffff","Font":"STHeiti","Y":0.15}}}' \
  --title "<task_title>" \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Mode 2: Speech-level Translation

```bash
aliyun ice submit-video-translation-job \
  --input-config '{"Type":"Video","Video":"https://<bucket>.oss-<region>.aliyuncs.com/<object>.mp4"}' \
  --output-config '{"MediaURL":"https://<bucket>.oss-<region>.aliyuncs.com/<output>.mp4"}' \
  --editing-config '{"SourceLanguage":"zh","TargetLanguage":"en","NeedSpeechTranslate":true,"NeedFaceTranslate":false,"SpeechTranslate":{"VoiceConfig":{"Voice":"zhiyan_emo"}}}' \
  --title "<task_title>" \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Mode 3: Using External SRT File

> **Key**: `InputConfig.Subtitle` must use HTTPS format, `oss://` prefix is prohibited

```bash
aliyun ice submit-video-translation-job \
  --input-config '{"Type":"Video","Video":"https://<bucket>.oss-<region>.aliyuncs.com/<object>.mp4","Subtitle":"https://<bucket>.oss-<region>.aliyuncs.com/<subtitle>.srt"}' \
  --output-config '{"MediaURL":"https://<bucket>.oss-<region>.aliyuncs.com/<output>.mp4"}' \
  --editing-config '{"SourceLanguage":"zh","TargetLanguage":"en","NeedSpeechTranslate":false,"NeedFaceTranslate":false,"TextSource":"SubtitleFile","CustomSrtType":"SourceSrt","SubtitleConfig":{"Type":"Text","FontSize":48,"FontColor":"#ffffff","Font":"STHeiti","Y":0.15}}' \
  --title "<task_title>" \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**EditingConfig Core Fields**:

| Field | Description |
|-------|-------------|
| `NeedSpeechTranslate` | `false`=subtitle-level, `true`=speech-level |
| `NeedFaceTranslate` | **Must be false** |
| `TextSource` | `OCR_ASR`(default) / `SubtitleFile`(use SRT) |
| `CustomSrtType` | Required when using SRT: `SourceSrt`(source language) / `TargetSrt`(already translated) |

---

## Query Video Translation Task

```bash
aliyun ice get-smart-handle-job \
  --job-id "<job_id>" \
  --user-agent AlibabaCloud-Agent-Skills
```

| State | Description |
|-------|-------------|
| Created | Created |
| Executing | Executing |
| Finished | Completed |
| Failed | Failed |

**Polling Recommendation**: Query every 30 seconds, timeout 30 minutes

---

## OSS Commands

> **Note**: OSS commands do not support `--user-agent`

### Local Video Upload

```bash
# Upload local video to OSS
aliyun oss cp <local_path> oss://<bucket>/<path>/<filename>.mp4

# Example
aliyun oss cp /Users/demo/videos/test.mp4 oss://my-bucket/videos/test.mp4
```

### OSS URL Format Reference

> **Important**: Different APIs use different address formats!

| API | Address Format | Example |
|-----|----------------|---------|
| `SubmitIProductionJob` (subtitle extraction) | **`oss://` format** | `oss://my-bucket/videos/test.mp4` |
| `SubmitVideoTranslationJob` (video translation) | **HTTP URL format** | `https://my-bucket.oss-cn-shanghai.aliyuncs.com/videos/test.mp4` |

> **Key**: Subtitle extraction uses `oss://`, video translation uses HTTP URL!

### Format Conversion Rules

```
oss:// format ⇄ HTTP URL format

oss://my-bucket/videos/test.mp4
    ⇄
https://my-bucket.oss-cn-shanghai.aliyuncs.com/videos/test.mp4
```

**Conversion Formula**: `oss://<bucket>/<path>` → `https://<bucket>.oss-<region>.aliyuncs.com/<path>`

| Parameter | Description |
|-----------|-------------|
| `<bucket>` | OSS Bucket name |
| `<region>` | Region, e.g., cn-shanghai, cn-beijing |
| `<path>` | File path |

### Other OSS Commands

```bash
# List files
aliyun oss ls oss://<bucket>/<prefix>

# Download file
aliyun oss cp oss://<bucket>/<object> <local_path>

# Generate signed URL (for result sharing, required for private Bucket)
aliyun oss sign oss://<bucket>/<object> --timeout 3600
```

---

## Command Quick Reference

| Purpose | Command |
|---------|---------|
| Environment check | `aliyun version` |
| Credential check | `aliyun sts GetCallerIdentity` |
| Register media | `aliyun ice register-media-info` |
| Submit subtitle extraction | `aliyun ice SubmitIProductionJob --FunctionName CaptionExtraction --force` |
| Query subtitle extraction | `aliyun ice QueryIProductionJob --force` |
| Submit video translation | `aliyun ice submit-video-translation-job` |
| Query video translation | `aliyun ice get-smart-handle-job` |
| Query media info | `aliyun ice get-media-info` |
| List OSS | `aliyun oss ls` |
| Download from OSS | `aliyun oss cp` (from oss) |
| Upload to OSS | `aliyun oss cp` (to oss) |
| Sign URL | `aliyun oss sign` |