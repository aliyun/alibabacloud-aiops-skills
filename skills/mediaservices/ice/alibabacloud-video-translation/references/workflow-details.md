# Workflow Details

This document provides detailed execution flow and timing for 4 scenarios.

---

## Scenario Overview

| Scenario | Name | Entry Condition | TextSource |
|----------|------|-----------------|------------|
| 1 | Direct Translation | User provides video only, no review needed | `OCR_ASR` |
| 2 | Subtitle Review | User provides video only, needs subtitle review first | `SubtitleFile` |
| 3 | Subtitle Translation + User Subtitle | User provides video + SRT, subtitle translation mode | `SubtitleFile` |
| 4 | Speech Translation + User Subtitle | User provides video + SRT, speech translation mode | `SubtitleFile` |

---

## Scenario 1: Direct Translation

### Execution Flow

```
Phase 0: Environment Check → Phase 1: Translation Mode Confirmation → Phase 2: Subtitle Processing Confirmation →
Phase 3: Output Path Confirmation → Phase 5: Task Submission → Phase 6: Task Polling → Phase 7: Result Retrieval
```

### Detailed Steps

#### Step 1: Environment Check (Phase 0)

- Check CLI version >= 3.3.1
- Check credential status (aliyun configure list)
- Check input video OSS file exists

**Duration**: ~10 seconds

#### Step 2: Register Media

```bash
aliyun ice register-media-info --input-url "oss://<bucket>/<object>" --media-type video
```

**Duration**: ~3-5 seconds (async task)

#### Step 3: Translation Mode Confirmation (Phase 1) ⚠️ BLOCKING

Use AskUserQuestion to ask:
- "Do you need subtitle translation (translate subtitles only) or speech translation (translate subtitles + replace voiceover)?"

**Must wait for user response!**

#### Step 4: Subtitle Processing Confirmation (Phase 2) ⚠️ BLOCKING

Use AskUserQuestion to ask:
- "Do you need to erase original subtitles from the video?"
- "Do you need to burn-in translated subtitles?"

**Must wait for user response!**

#### Step 5: Output Path Confirmation (Phase 3)

- User specifies path → Use user's path
- User does not specify → Use default path and inform user

**Default Path Rule**: `{source}_translated_{random8}.mp4`

#### Step 6: Task Submission (Phase 5)

```bash
aliyun ice submit-video-translation-job \
  --input-config '{"Type":"Video","Video":"<mediaId>"}' \
  --output-config '{"MediaURL":"https://<output_url>"}' \
  --editing-config '{"TextSource":"OCR_ASR",...}'
```

**Duration**: ~2 seconds

#### Step 7: Task Polling (Phase 6)

Query every 30 seconds until task completes or fails.

**Expected Duration**:
- Subtitle-level translation: 3-5 minutes
- Speech-level translation: 10-20 minutes

#### Step 8: Result Retrieval (Phase 7)

- Get output video URL
- Generate signed URL (private Bucket)
- Output result to user

---

## Scenario 2: Subtitle Review

> **Key**: When user does not provide subtitle, MUST ask if subtitle extraction and review is needed!

### Execution Flow

```
Phase 0 → Phase 1 → Phase 2 → 【MUST ASK】 Need subtitle review? →
User chooses review → Phase 4: Subtitle Review Confirmation → Phase 5 → Phase 6 → Phase 7
```

### Detailed Steps

#### Step 1-5: Same as Scenario 1

Execute Phase 0-3, same flow.

#### Step 6: Need Subtitle Review? ⚠️ BLOCKING

> **Must Ask**: When user does not provide subtitle, must confirm if extraction and review is needed!

Use AskUserQuestion to ask:
- "Do you need to extract subtitles for review first, or translate directly?"

| User Answer | Follow-up Action |
|-------------|------------------|
| Need review | Enter subtitle extraction flow |
| Direct translation | Switch to Scenario 1 (TextSource=OCR_ASR) |

#### Step 7: Subtitle Detection Region Confirmation ⚠️ BLOCKING

After user chooses review, ask subtitle detection region:

Use AskUserQuestion to ask:
- "Where are the subtitles roughly located in the video? Bottom 1/4, bottom 1/2?"

**ROI Mapping Table**:

| User Answer | ROI Parameter |
|-------------|---------------|
| Bottom 1/4 | `[[0.75, 1], [0, 1]]` |
| Bottom 1/2 | `[[0.5, 1], [0, 1]]` |
| Bottom 1/3 | `[[0.67, 1], [0, 1]]` |
| Full screen detection | `[[0, 1], [0, 1]]` |

#### Step 8: Subtitle Extraction (CaptionExtraction)

> **CLI Format Key**: `--Input`, `--Output`, `--JobParams` must use JSON string format!

```bash
# Using MediaId (registered media)
aliyun ice SubmitIProductionJob \
  --FunctionName CaptionExtraction \
  --Input '{"Type":"MediaId","Media":"<mediaId>"}' \
  --Output '{"Type":"OSS","Media":"oss://<bucket>/<output>.srt"}' \
  --JobParams '{"lang":"ch","roi":[[0.5,1],[0,1]]}' \
  --force

# Or using OSS path
aliyun ice SubmitIProductionJob \
  --FunctionName CaptionExtraction \
  --Input '{"Type":"OSS","Media":"oss://<bucket>/<object>"}' \
  --Output '{"Type":"OSS","Media":"oss://<bucket>/<output>.srt"}' \
  --JobParams '{"lang":"ch","roi":[[0.5,1],[0,1]]}' \
  --force
```

**Duration**: 1-2 minutes

#### Step 9: Query Subtitle Extraction Result

Query every 30 seconds until Success or Fail.

#### Step 10: Subtitle Review Confirmation (Phase 4) ⚠️ BLOCKING

> **CRITICAL**: Must execute strictly!

1. Get extracted subtitle content
2. **Output subtitle content as-is** to user (DO NOT change format)
3. AskUserQuestion: "Subtitle extraction complete, please check if content is correct, need modifications?"
4. **Must wait for user confirmation**

#### Step 11: Task Submission (Phase 5)

After user confirmation, submit translation task using reviewed SRT file:

```bash
aliyun ice submit-video-translation-job \
  --input-config '{"Type":"Video","Video":"<mediaId>","Subtitle":"<srt_https_url>"}' \
  --output-config '{"MediaURL":"https://<output_url>"}' \
  --editing-config '{"TextSource":"SubtitleFile",...}'
```

#### Step 12-13: Same as Scenario 1 Phase 6-7

---

## Scenario 3: Subtitle Translation + User Subtitle

### Execution Flow

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 5 → Phase 6 → Phase 7
```

### Detailed Steps

#### Step 1-3: Same as Scenario 1

Execute Phase 0-2.

#### Step 4: Check Subtitle File

- Check user-provided SRT file OSS exists
- Validate SRT format (fix empty subtitle entries)

#### Step 5: Task Submission

```bash
aliyun ice submit-video-translation-job \
  --input-config '{"Type":"Video","Video":"<mediaId>","Subtitle":"<srt_https_url>"}' \
  --output-config '{"MediaURL":"https://<output_url>"}' \
  --editing-config '{"TextSource":"SubtitleFile","NeedSpeechTranslate":false,...}'
```

> **Key**: `NeedSpeechTranslate: false` (subtitle translation mode)

---

## Scenario 4: Speech Translation + User Subtitle

### Execution Flow

```
Phase 0 → Phase 1 → Phase 2 → CustomSrtType Confirmation ⚠️ BLOCKING →
Phase 3 → Phase 5 → Phase 6 → Phase 7
```

### Detailed Steps

#### Step 1-3: Same as Scenario 1

Execute Phase 0-2.

#### Step 4: CustomSrtType Confirmation ⚠️ BLOCKING

> **Must Ask**: For speech translation + user subtitle, must confirm subtitle language type!

Use AskUserQuestion to ask:
- "Is the subtitle file you provided in source language or target language?"

| User Answer | CustomSrtType |
|-------------|---------------|
| Source language | `SourceSrt` |
| Target language (already translated) | `TargetSrt` |

#### Step 5: Task Submission

```bash
aliyun ice submit-video-translation-job \
  --input-config '{"Type":"Video","Video":"<mediaId>","Subtitle":"<srt_https_url>"}' \
  --output-config '{"MediaURL":"https://<output_url>"}' \
  --editing-config '{"TextSource":"SubtitleFile","NeedSpeechTranslate":true,"SpeechTranslate":{"CustomSrtType":"SourceSrt",...},...}'
```

> **Key**: `NeedSpeechTranslate: true` + `SpeechTranslate.CustomSrtType`

---

## Blocking Point Summary

| Phase | Blocking Type | Trigger Condition |
|-------|---------------|-------------------|
| 0 | HARD-GATE | CLI version or credential not passed |
| 1 | BLOCKING | Translation mode not confirmed |
| 2 | BLOCKING | Subtitle processing not confirmed |
| 3 | Non-blocking | Output path not specified (default available) |
| Need subtitle review? | BLOCKING | User does not provide subtitle, must ask |
| 4 | BLOCKING | Subtitle review not confirmed (when user chooses review) |
| CustomSrtType | BLOCKING | Speech translation + user subtitle |

---

## Polling Strategy

### Subtitle Extraction Task

- Interval: 30 seconds
- Timeout: 5 minutes
- States: Init → Queuing → Analysing → Processing → Success/Fail

### Video Translation Task

- Interval: 30 seconds
- Timeout: 30 minutes
- States: Created → Executing → Finished/Failed

---

## Time Estimation

| Task Type | 3-minute Video | 10-minute Video |
|-----------|----------------|-----------------|
| Subtitle extraction | 1-2 minutes | 3-5 minutes |
| Subtitle-level translation | 3-5 minutes | 8-12 minutes |
| Speech-level translation | 10-20 minutes | 30-50 minutes |

---

*End of Document*