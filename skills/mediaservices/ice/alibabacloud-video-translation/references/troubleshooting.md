# Troubleshooting Guide for Video Translation Skill

This document provides detailed error handling procedures for video translation task execution.

---

## 1. API Error Handling

### 1.1 Forbidden.SubscriptionRequired

**Error Meaning**: User has not enabled video translation service or has insufficient permissions.

**Handling Flow**:

```
Detect error → Output permission requirements → Guide user to activate service
```

**Required Permission List**:

| Service | Permission |
|---------|------------|
| ICE | `ice:RegisterMediaInfo` |
| ICE | `ice:SubmitIProductionJob` |
| ICE | `ice:QueryIProductionJob` |
| ICE | `ice:GetSmartHandleJob` |
| ICE | `ice:SubmitVideoTranslationJob` |
| OSS | `oss:GetObject` |
| OSS | `oss:PutObject` |
| OSS | `oss:ListObjects` |

**Standard Output**:

```markdown
## Insufficient Permissions

You need to enable the video translation service and configure the corresponding RAM permissions.

**Required Permissions**:
- ice:RegisterMediaInfo
- ice:SubmitIProductionJob
- ice:QueryIProductionJob
- ice:GetSmartHandleJob
- ice:SubmitVideoTranslationJob
- oss:GetObject
- oss:PutObject
- oss:ListObjects

**Solution**:
1. Login to [RAM Console](https://ram.console.aliyun.com/)
2. Create a custom permission policy with the above permissions
3. Grant the policy to the current RAM user or role

**Next Step**: Re-execute the task after configuration is complete
```

---

### 1.2 InvalidParameter

**Error Meaning**: API parameter format error.

**Handling Flow**:

```
Detect error → Parse error details → Output correction suggestions based on table below
```

**Common Parameter Errors**:

| Parameter | Common Error | Correction Method |
|-----------|--------------|-------------------|
| `InputConfig` | JSON format error | Ensure JSON string is properly escaped, use single quotes to wrap |
| `InputConfig.Media` | Used HTTP URL | SubmitIProductionJob uses `oss://` format |
| `OutputConfig.MediaURL` | Used `oss://` prefix | SubmitVideoTranslationJob uses HTTP URL format |
| `EditingConfig` | Missing required fields | Add SourceLanguage, TargetLanguage |
| `DetextArea` | Format error | Use string format: `"[[0, 0.9, 1, 0.1]]"` |
| `SubtitleConfig` | Missing configuration | Add Type, FontSize, FontColor fields |
| `CustomSrtType` | Not filled | Required for speech translation + SRT input: `SourceSrt` or `TargetSrt` |

**Standard Output**:

```markdown
## Parameter Format Error

**Error Message**: {original error}

**Possible Causes**:
- {cause 1}
- {cause 2}

**Correction Suggestions**:
- {suggestion 1}
- {suggestion 2}

**Next Step**: Re-execute after correcting parameters
```

---

### 1.3 InputConfig.Subtitle is invalid

**Error Meaning**: SRT subtitle file format is invalid, usually contains empty subtitle entries.

**Handling Flow**: See [SRT Format Repair Flow](#2-srt-format-repair-flow)

---

### 1.4 JobFailed

**Error Meaning**: Task execution failed.

**Handling Flow**:

```
Detect error → Record JobId → Analyze failure reason → Ask user to retry or switch mode
```

**Standard Output**:

```markdown
## Task Execution Failed

**JobId**: {JobId}
**Failure Reason**: {failure reason}

**Suggested Solutions**:
1. Retry task
2. Check input video format
3. Contact technical support

**Next Step**: Confirm whether to retry the task?
```

---

## 2. SRT Format Repair Flow

### 2.1 Problem Identification

Empty subtitle entry example:

```srt
1
00:00:00,000 --> 00:00:02,500
First sentence

2
00:00:02,500 --> 00:00:05,000
Second sentence

3
00:00:08,000 --> 00:00:10,600

4
00:00:10,600 --> 00:00:12,000
This is normal subtitle
```

**Problem**: Entry 3 has only sequence number and timeline, no subtitle content.

### 2.2 Repair Steps

```
Detect empty subtitle entries → Delete empty entries → Renumber → Upload repaired file → Inform user
```

### 2.3 Repair Command

Use Python script to auto-repair:

```python
import re

def fix_srt(content: str) -> tuple[str, int]:
    """
    Fix empty subtitle entries in SRT file.

    Args:
        content: SRT file content

    Returns:
        (repaired content, count of removed empty entries)
    """
    # Match SRT entries: sequence + timeline + content
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)

    # Filter out entries with empty content
    valid_entries = [(idx, timecode, text.strip())
                     for idx, timecode, text in matches
                     if text.strip()]

    # Renumber and build new content
    result = []
    for new_idx, (_, timecode, text) in enumerate(valid_entries, 1):
        result.append(f"{new_idx}\n{timecode}\n{text}\n")

    removed_count = len(matches) - len(valid_entries)
    return '\n'.join(result), removed_count
```

### 2.4 Standard Output

```markdown
## SRT File Repair

**Detection Result**: Found {count} empty subtitle entries

**Action Taken**: Auto-deleted empty entries and renumbered

**Repaired File**: {repaired OSS path}

**Next Step**: Continue task with repaired SRT file
```

---

## 3. Speech Translation Failed Handling

> **HARD-GATE**: After speech translation fails, **DO NOT auto-switch to subtitle translation mode**, must ask user first!

### 3.1 Handling Flow

```
Speech translation failed → Output error message → AskUserQuestion to ask about switching → Execute after user confirmation
```

### 3.2 Prohibited Actions

- DO NOT auto-switch to subtitle translation mode
- DO NOT assume user's choice
- DO NOT skip user confirmation

### 3.3 Standard Inquiry

Use AskUserQuestion tool:

```markdown
## Speech Translation Failed

**Error Message**: {original error}

**Available Options**:
1. Switch to subtitle translation mode (translate subtitles only, no voiceover replacement)
2. Retry speech translation
3. Terminate task

**Please Select**: How would you like to proceed?
```

### 3.4 User Choice Handling

| User Choice | Follow-up Action |
|-------------|------------------|
| Switch to subtitle translation | Set `NeedSpeechTranslate: false`, resubmit task |
| Retry speech translation | Resubmit task with same parameters |
| Terminate task | Output termination info, record completed steps |

---

## 4. AskUserQuestion No Response Handling

### 4.1 Timeout Handling Rules

| Timeout | Action |
|---------|--------|
| 30 seconds | Output waiting prompt, continue waiting |
| 60 seconds | Output pause info, retain step records |

### 4.2 30 Second Timeout Output

```markdown
## Waiting for Your Response

Waiting for your confirmation to continue the task...

**Current Status**: Waiting for user to confirm translation mode
**Time Waited**: 30 seconds

Please reply when ready.
```

### 4.3 60 Second Timeout Output

```markdown
## Task Paused

Task has been paused due to no response for an extended period.

**Completed Steps**:
- step 1: {step 1 description}
- step 2: {step 2 description}

**Waiting Confirmation**: {question waiting for confirmation}

**Resume**: Please reply to your question, I will continue from the current step.
```

---

## 5. Failure Message Output Template

### 5.1 General Template

```markdown
## Task Execution Failed

**Failure Phase**: {phase name}
**Failure Type**: {type: API call failed / User confirmation timeout / Parameter error / Other}
**JobId**: {if applicable}

**Error Message**:
```
{original error}
```

**Suggested Solutions**:
- {solution 1}
- {solution 2}

**Completed Steps**:
- step 1: {step 1 description}
- step 2: {step 2 description}

**Next Step**: Re-execute after confirmation
```

### 5.2 Phase Name Reference

| Phase | Name |
|-------|------|
| 0 | Environment and Credential Check |
| 1 | Translation Mode Confirmation |
| 2 | Subtitle Processing Confirmation |
| 3 | Output Path Confirmation |
| 4 | Subtitle Review Confirmation |
| 5 | Task Submission |
| 6 | Task Polling |
| 7 | Result Retrieval |

---

## 6. Common Issue Troubleshooting

### 6.1 Video Cannot Be Processed

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| Video format not supported | Non-standard format | Convert to mp4/mov format |
| Video too large | Exceeds 2GB | Compress or split video |
| Video duration too long | Exceeds 2 hours | Process in segments |

### 6.2 Subtitle Extraction Failed

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| No subtitles detected | Video has no subtitles or subtitles are blurry | Provide external SRT file |
| Language detection error | Mixed languages | Manually specify SourceLanguage |
| Empty extraction result | ROI area setting error | Adjust ROI parameter |

### 6.3 Translation Quality Issues

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| Inaccurate translation | Technical terms | Provide terminology list or use reviewed subtitles |
| Incorrect subtitle position | SubtitleConfig settings | Adjust Y value and TextWidth |
| Subtitles blocking image | Y value setting improper | Adjust subtitle position parameter |

---

## 7. Error Recovery Strategy

### 7.1 Retryable Errors

The following errors can be auto-retried:

| Error Type | Max Retries | Retry Interval |
|------------|-------------|----------------|
| Network timeout | 3 | 5 seconds |
| Service temporarily unavailable | 3 | 10 seconds |
| Resource quota exceeded (transient) | 1 | 30 seconds |

### 7.2 Non-Retryable Errors

The following errors require user intervention:

- Insufficient permissions (Forbidden.SubscriptionRequired)
- Parameter error (InvalidParameter)
- Video format not supported
- SRT format error

### 7.3 Retry Flow

```
Detect retryable error → Wait interval → Retry → Success/Failure
    ↓
Max retries reached → Output failure info → Ask user
```

---

*End of Document*