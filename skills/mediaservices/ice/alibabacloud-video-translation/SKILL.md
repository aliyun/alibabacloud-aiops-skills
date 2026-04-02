---
name: alibabacloud-video-translation
description: |
  Alibaba Cloud IMS (Intelligent Media Services) based video translation Skill. Supports subtitle extraction (ASR/OCR), translation, and speech synthesis translation modes.
  Trigger words: "视频翻译", "translate video", "翻译视频", "字幕翻译", "video translation"
---

# Video Translation Skill

One-click video translation powered by Alibaba Cloud IMS, supporting subtitle-level and speech-level translation.

---

## Input Format Requirements

> **IMPORTANT**: Different APIs use different address formats!

### API Address Format Reference

| API | Address Format | Example |
|-----|----------------|---------|
| `SubmitIProductionJob` (subtitle extraction) | **`oss://` format** | `oss://my-bucket/videos/test.mp4` |
| `SubmitVideoTranslationJob` (video translation) | **HTTP URL format** | `https://my-bucket.oss-cn-shanghai.aliyuncs.com/videos/test.mp4` |

> **Key**: Subtitle extraction uses `oss://`, video translation uses HTTP URL!

### User Input Handling

| User Input Type | Processing Method |
|-----------------|-------------------|
| HTTP URL format | Use directly for video translation; convert to `oss://` if subtitle extraction needed |
| `oss://` format | Use directly for subtitle extraction; convert to HTTP URL for video translation |
| Local video | **MUST ask** for OSS upload path, save both formats after upload |

### Format Conversion Rules

```
oss:// format ⇄ HTTP URL format

oss://my-bucket/videos/test.mp4
    ⇄
https://my-bucket.oss-cn-shanghai.aliyuncs.com/videos/test.mp4
```

**Conversion Formula**:
- `oss://<bucket>/<path>` → `https://<bucket>.oss-<region>.aliyuncs.com/<path>`
- HTTP URL does not require signing, use Bucket domain format directly

### Local Video Processing Flow

```
User provides local video path
    │
    ├─ AskUserQuestion: "Please provide OSS upload path (format: oss://<bucket>/<path>/<filename>.mp4)"
    │
    ├─ User specifies upload path
    │   ├─ Check if Bucket exists
    │   ├─ Upload file: aliyun oss cp <local_path> <oss_path>
    │   ├─ Save oss:// format → for subtitle extraction
    │   └─ Save HTTP URL format → for video translation
    │
    └─ User does not specify path → STOP, user MUST provide upload path
```

**Upload Command**:
```bash
aliyun oss cp <local_path> oss://<bucket>/<path>/<filename>.mp4
```

**Save both formats after upload**:
```
Local: /Users/demo/videos/test.mp4
Uploaded to: oss://my-bucket/videos/test.mp4
    ├─ oss:// format: oss://my-bucket/videos/test.mp4 (for subtitle extraction)
    └─ HTTP URL: https://my-bucket.oss-cn-shanghai.aliyuncs.com/videos/test.mp4 (for video translation)
```

---

## Execution Gate Checklist

> **Strict Requirement**: Agent MUST execute in phase order, cannot proceed without passing current phase!

### Phase 0: Environment and Credential Check (HARD-GATE)

| Check Item | Command | Pass Condition | Failure Handling |
|------------|---------|----------------|------------------|
| CLI version | `aliyun version` | >= 3.3.1 | STOP, see [cli-installation-guide.md](references/cli-installation-guide.md) |
| Credential status | `aliyun configure list` | Valid status | STOP, guide configuration |
| Plugin installation | `aliyun configure set --auto-plugin-install true` | Set | Auto-set |

> **HARD-GATE**: Cannot proceed with any subsequent operations without passing!

---

### Phase 1: Translation Mode Confirmation (BLOCKING)

```
AskUserQuestion: "Do you need subtitle translation (translate subtitles only) or speech translation (translate subtitles + replace voiceover)?"

┌─ Subtitle translation → NeedSpeechTranslate: false
└─ Speech translation → NeedSpeechTranslate: true

⚠️ No reply received → STOP, cannot proceed!
```

> **DO NOT infer translation mode from input type!**

---

### Phase 2: Subtitle Processing Confirmation (BLOCKING)

```
AskUserQuestion: "Do you need to erase original subtitles from the video? Do you need to burn-in translated subtitles?"

⚠️ No reply received → STOP, cannot proceed!
```

**Parameter Mapping**:

| Feature | Parameter | Value |
|---------|-----------|-------|
| Erase original subtitles | `DetextArea` | `"Auto"` / coordinates / not set (no erasure) |
| Burn-in new subtitles | `SubtitleConfig` | config object / not set (no burn-in) |

---

### Phase 3: Output Path Confirmation (Non-blocking)

| Condition | Processing Method |
|-----------|-------------------|
| User explicitly specifies | Use user's path |
| User does not specify | Use default path and inform user |

**Default Output Rules**:
- Bucket: Same bucket as input video
- Directory: Same directory as input video
- Filename: `{source}_translated_{random8}.mp4`
- Example: `oss://bucket/videos/demo.mp4` → `oss://bucket/videos/demo_translated_a1b2c3d4.mp4`

> DO NOT use shell variables, use Python: `python3 -c "import random; print(''.join(random.choices('abcdefghijkmnpqrstuvwxyz23456789', k=8)))"`

---

### Phase 4: Subtitle Review Confirmation (Conditional Blocking)

| Trigger Condition | Processing Method |
|-------------------|-------------------|
| User chooses to review subtitles | BLOCKING, MUST wait for user confirmation of review result |
| User does not need review | Non-blocking, proceed |

> **CRITICAL**: After subtitle extraction, MUST output content as-is for user review, DO NOT change format!

---

## Scenario Entry Selector

> **Key Points**:
> 1. When user inputs local video, MUST first upload to OSS and get HTTP URL
> 2. When user does not provide subtitle, MUST ask if subtitle extraction and review is needed

```
User inputs video
    │
    ├─ Local video?
    │   └─ Yes → AskUserQuestion: "Please provide OSS upload path"
    │       ├─ User provides path → Upload to OSS → Convert to HTTP URL → Continue
    │       └─ User does not provide → STOP
    │
    ├─ oss:// format?
    │   └─ Yes → Inform user to convert to HTTP URL format
    │
    └─ HTTP URL format? → Continue
        │
        ├─ User provides SRT file?
        │   ├─ Yes → Input type = with_subtitle
        │   │   ├─ Translation mode = speech → 【Scenario 4】 ⚠️ MUST ask CustomSrtType
        │   │   └─ Translation mode = subtitle → 【Scenario 3】
        │   │
        │   └─ No → Input type = only_video ⚠️ MUST ask if review needed
        │       │
        │       ├─ AskUserQuestion: "Do you need to extract subtitles for review first, or translate directly?"
        │       │
        │       ├─ Need review → 【Scenario 2】 ⚠️ Phase 4 blocking
        │       │
        │       └─ Direct translation → 【Scenario 1】 (TextSource=OCR_ASR)
```

| Scenario | Name | Blocking Point | TextSource | Flow |
|----------|------|----------------|------------|------|
| 0 | Local video upload | **OSS upload path inquiry** | - | Upload→HTTP URL→Subsequent scenario |
| 1 | Direct translation | Phase 1, 2 | `OCR_ASR` | Submit translation directly |
| 2 | Subtitle review | Phase 1, 2, **Subtitle review inquiry**, Phase 4 | `SubtitleFile` | Extract subtitle→Review→Translate |
| 3 | Subtitle translation + user subtitle | Phase 1, 2 | `SubtitleFile` | Use user SRT to translate directly |
| 4 | Speech translation + user subtitle | Phase 1, 2 + **CustomSrtType confirmation** | `SubtitleFile` | Confirm subtitle language then translate |

> **Scenario 0 (Local video) detailed flow**:
> 1. AskUserQuestion: "Please provide OSS upload path (format: oss://<bucket>/<path>/<filename>.mp4)"
> 2. After user specifies path, execute `aliyun oss cp <local_path> <oss_path>`
> 3. Convert to HTTP URL: `https://<bucket>.oss-<region>.aliyuncs.com/<path>/<filename>.mp4`
> 4. Continue with subsequent scenario flow

> **Scenario 2 detailed flow**:
> 1. Ask for subtitle detection region (roi parameter)
> 2. Call `CaptionExtraction` to extract subtitles, input and output use oss:// format
> 3. **Output subtitle content as-is** for user review
> 4. After user confirmation, use reviewed SRT to submit translation

---

## Parameter Decision Table

> **Decision Rules**: Clearly define handling for each parameter, DO NOT assume arbitrarily!

| Parameter | Trigger Condition | Handling Method | Default Value | Prohibited Behavior |
|-----------|-------------------|-----------------|---------------|---------------------|
| `NeedSpeechTranslate` | Always | **MUST ask** | None | DO NOT infer from input |
| `NeedFaceTranslate` | Always | **Fixed value** | `false` | DO NOT set to true |
| `DetextArea` | User chooses erasure | **MUST ask** | None | DO NOT set to Auto arbitrarily |
| `SubtitleConfig` | User chooses burn-in | **Can use default** | Standard style | DO NOT skip confirmation |
| `TextSource` | Scenario decides | **Scenario rules** | See scenario mapping | DO NOT choose arbitrarily |
| `CustomSrtType` | Scenario 4 | **MUST ask** | None | DO NOT infer arbitrarily |
| `OutputConfig.MediaURL` | Output path | **Can use default** | Default rules | DO NOT use shell variables |
| `JobParams.roi` | Subtitle extraction | **MUST ask** | `[[0.5,1],[0,1]]` | DO NOT set default arbitrarily |
| `SourceLanguage` | User specifies or inferable | **Can use default** | Auto detect | Use zh for Chinese only |
| `TargetLanguage` | User specifies | **Can use default** | `en` | Ask for other languages |

**TextSource Scenario Mapping**:

| Scenario | Value | Description |
|----------|-------|-------------|
| 1 | `OCR_ASR` | Auto-detect subtitles |
| 2 | `SubtitleFile` | Reviewed SRT |
| 3, 4 | `SubtitleFile` | User-provided SRT |

**CustomSrtType Trigger Rules**:

| Condition | Value |
|-----------|-------|
| CaptionExtraction extracted | `SourceSrt` |
| User provides subtitle (Scenario 4) | **MUST ask**: SourceSrt / TargetSrt |

---

## Failure Protection Mechanism

> **HARD-GATE**: After speech translation fails, DO NOT auto-switch to subtitle translation!

### API Error Handling

| ErrorCode | Handling Action |
|-----------|-----------------|
| `Forbidden.SubscriptionRequired` | See [ram-policies.md](references/ram-policies.md) |
| `InvalidParameter` | See [api-parameters.md](references/api-parameters.md) |
| `InputConfig.Subtitle is invalid` | See [troubleshooting.md](references/troubleshooting.md#srt-format-repair) |
| `JobFailed` | Record JobId, ask user if retry needed |

### SRT Format Repair Flow

```
Detect empty subtitle entries → Delete empty entries → Renumber → Upload repaired file → Inform user
```

See [troubleshooting.md](references/troubleshooting.md) for details.

---

## CLI Command Templates

> **IMPORTANT**: Before submitting API, **MUST reference [api-parameters.md](references/api-parameters.md) to confirm parameter format**!

See [cli-commands.md](references/cli-commands.md) for details.

**Core Commands**:

```bash
# Register media asset
aliyun ice register-media-info --input-url "oss://<bucket>/<object>" --media-type video --user-agent AlibabaCloud-Agent-Skills

# Submit subtitle extraction (use OSS path)
aliyun ice submit-iproduction-job \
  --function-name CaptionExtraction \
  --input "Media=oss://<bucket>/<object> Type=OSS" \
  --biz-output "Media=oss://<bucket>/<output>.srt Type=OSS" \
  --job-params '{"lang":"ch","roi":[[0.5,1],[0,1]]}' \
  --force \
  --user-agent AlibabaCloud-Agent-Skills

# Submit video translation
aliyun ice submit-video-translation-job \
  --user-agent AlibabaCloud-Agent-Skills
```

> **CLI Format Key Points**:
> - Subtitle extraction uses command name `submit-iproduction-job` (lowercase, `-` separator)
> - `--input` and `--biz-output` format: space-separated string `"Media=... Type=OSS"`, NOT JSON
> - `--job-params` format: JSON string
> - MUST add `--force` to skip plugin parameter validation
> - **All ICE commands MUST add `--user-agent AlibabaCloud-Agent-Skills`**

---

## Documentation Reference

| Document | Content |
|----------|---------|
| [workflow-details.md](references/workflow-details.md) | Detailed execution flow for 4 scenarios |
| [cli-commands.md](references/cli-commands.md) | CLI command template library |
| [troubleshooting.md](references/troubleshooting.md) | Error handling details |
| [api-parameters.md](references/api-parameters.md) | Complete API parameter documentation |
| [ram-policies.md](references/ram-policies.md) | RAM permission requirements |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |

---

## Key Constraints

- **Before submitting API, MUST reference [api-parameters.md](references/api-parameters.md) to confirm parameter format**
- **All ICE CLI commands MUST add `--user-agent AlibabaCloud-Agent-Skills`**
- **Subtitle extraction (SubmitIProductionJob) uses `oss://` format**
- **Video translation (SubmitVideoTranslationJob) uses HTTP URL format**, no signing needed
- **Local videos MUST first be uploaded to OSS**, user MUST provide upload path
- `NeedFaceTranslate` MUST be `false`
- `SpeechTranslate` and `SubtitleTranslate` are mutually exclusive
- `InputConfig.Subtitle` MUST use HTTPS format, DO NOT use `oss://`
- Speech translation + SRT input requires `SpeechTranslate.CustomSrtType`
- DO NOT infer translation mode from input type

---

## Task Polling

> **Mandatory**: MUST continuously poll task status until completion (`State=Finished`) or failure (`State=Failed`), **DO NOT exit early**!

| Task Type | Query Command | Interval | Timeout |
|-----------|---------------|----------|---------|
| Subtitle extraction | `QueryIProductionJob` | 30 seconds | 5 minutes |
| Video translation | `get-smart-handle-job` | 30 seconds | 30 minutes |

**Polling Logic**:
```
Loop polling until:
  - State == "Finished" → Return result
  - State == "Failed" → Report error
  - Exceeds 30 minutes → Report TimeoutError

Prohibited: Return after single query / Skip polling and return JobId directly
```

**Time Reference** (3-minute video):
- Subtitle-level translation: 3-5 minutes
- Speech-level translation: 10-20 minutes

---

## Result Retrieval

```bash
# Get media asset info
aliyun ice get-media-info --media-id "<MediaId>"

# Generate signed URL (for private Bucket)
aliyun oss sign oss://<bucket>/<object> --timeout 3600
```

---

*End of Document*