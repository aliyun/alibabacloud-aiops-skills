# API Parameters for Video Translation

This document provides detailed parameter configuration for video translation related APIs.

---

## SubmitIProductionJob (Subtitle Extraction)

### Basic Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| FunctionName | String | Yes | Fixed as `CaptionExtraction` |
| Name | String | No | Task name |
| Input | Object | Yes | Input configuration, OSS address only |
| Output | Object | Yes | Output configuration, OSS address only |
| JobParams | String | No | Algorithm parameters JSON |

### Input Configuration

```json
{
  "Type": "OSS",
  "Media": "oss://<bucket>/<object>"
}
```

| Field | Description |
|-------|-------------|
| Type | Media type: OSS or Media |
| Media | OSS address or Media ID |

### Output Configuration

```json
{
  "Type": "OSS",
  "Media": "oss://<bucket>/{source}-{timestamp}-{sequenceId}.srt"
}
```

**Output Format**: SRT subtitle file

**Supported Placeholders**:
- `{source}`: Input filename
- `{timestamp}`: Unix timestamp
- `{sequenceId}`: Sequence number

### JobParams (CaptionExtraction)

```json
{
  "fps": 5,
  "roi": [[0.5, 1], [0, 1]],
  "lang": "ch",
  "track": "main"
}
```

**All parameters are optional**:

| Parameter | Type | Description |
|-----------|------|-------------|
| fps | Integer | Sampling frame rate, range [2,10], default 5 |
| roi | Array | Subtitle detection region `[[top, bottom], [left, right]]`, normalized values, **default bottom 1/4 of video** |
| lang | String | Recognition language: `ch`(Chinese) / `en`(English) / `ch_ml`(Chinese-English mixed) |
| track | String | `"main"` extract main subtitle track only |

---

## SubmitVideoTranslationJob Parameters

### InputConfig

Input parameters for video translation task, JSON format.

```json
{
  "Type": "Video",
  "Video": "<mediaId_or_ossUrl>",
  "Subtitle": "<srt_url_or_content>"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Type | String | Yes | Input type, fixed as "Video" |
| Video | String | Yes | Video media ID or OSS URL |
| Subtitle | String | No | SRT subtitle file URL or content |

### OutputConfig

Output parameters for video translation task, JSON format.

```json
{
  "MediaURL": "https://<bucket>.oss-<region>.aliyuncs.com/<object>.mp4",
  "Width": null,
  "Height": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| MediaURL | String | Yes | OSS URL for output video (must use https:// format) |
| Width | Integer | No | Output video width, null means same as source |
| Height | Integer | No | Output video height, null means same as source |

> **Default Output Path Rules**:
>
> If user does not specify output path, use the following defaults:
> - **Bucket**: Same bucket as input video
> - **Path**: Same directory as input video
> - **Filename**: `{source}_translated_{timestamp}.mp4`
>
> Example:
> - Input: `oss://my-bucket/videos/demo.mp4`
> - Default output: `https://my-bucket.oss-cn-shanghai.aliyuncs.com/videos/demo_translated_1711440000.mp4`

### EditingConfig

Configuration parameters for video translation task, JSON format.

```json
{
  "SourceLanguage": "zh",
  "TargetLanguage": "en",
  "NeedSpeechTranslate": false,
  "NeedFaceTranslate": false,
  "BilingualSubtitle": false,
  "SupportEditing": true,
  "TextSource": "OCR_ASR",
  "DetextArea": null,
  "SubtitleTranslate": {
    "OcrArea": "Auto",
    "SubtitleConfig": {
      "Type": "Text",
      "FontSize": 95,
      "FontColor": "#ffffff",
      "Font": "Alibaba PuHuiTi",
      "Y": 0.15,
      "TextWidth": 0.9,
      "Alignment": "Center",
      "BorderStyle": 1
    }
  }
}
```

#### Main Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| SourceLanguage | String | Yes | Source language code |
| TargetLanguage | String | Yes | Target language code |
| NeedSpeechTranslate | Boolean | No | Whether to use speech-level translation, must be false for subtitle-level |
| NeedFaceTranslate | Boolean | No | **Must be set to false**, this Skill does not enable face translation |
| BilingualSubtitle | Boolean | No | Whether to use bilingual subtitles |
| SupportEditing | Boolean | No | Whether to support editing |
| TextSource | String | No | Subtitle source, see TextSource details below |
| CustomSrtType | String | Conditionally Required | External subtitle type, required when TextSource=SubtitleFile |
| DetextArea | String | No | Subtitle erasure area, see DetextArea details below |
| SubtitleTranslate | Object | Conditionally Required | Subtitle-level translation config (required when NeedSpeechTranslate=false) |
| SpeechTranslate | Object | Conditionally Required | Speech-level translation config (required when NeedSpeechTranslate=true) |

#### DetextArea Parameter Details

Used to erase original subtitles from video.

| Value | Description |
|-------|-------------|
| Not set/null | No subtitle erasure |
| `Auto` | Auto-detect erasure area |
| `[[x, y, width, height]]` | Custom erasure range, supports multiple areas |

**Custom Erasure Area Parameters**:
- `x`: Horizontal distance ratio of subtitle box top-left corner from video top-left, range [0, 1]
- `y`: Vertical distance ratio of subtitle box top-left corner from video top-left, range [0, 1]
- `width`: Subtitle box width ratio relative to video width, range [0, 1]
- `height`: Subtitle box height ratio relative to video height, range [0, 1]

**Example** (erase bottom 10% of video):
```json
"DetextArea": "[[0, 0.9, 1, 0.1]]"
```

#### TextSource Parameter Details

| Value | Applicable Scenario | Description |
|-------|---------------------|-------------|
| `OCR_ASR` | User does not need subtitle review | OCR preferred, fallback to ASR if failed (default value) |
| `SubtitleFile` | User provides SRT / reviewed SRT | Subtitle source is external SRT file, requires InputConfig.Subtitle |
| `ASR` | ASR only | Recognize subtitles via speech only |
| `OCR` | OCR only | Recognize subtitles via image only |
| `ALL` | ASR+OCR fusion | ASR primary, OCR correction (subtitle-level only) |

#### CustomSrtType Parameter Details

> Valid only when `TextSource=SubtitleFile`

| Value | Description |
|-------|-------------|
| `SourceSrt` | Subtitle is in source language, needs translation |
| `TargetSrt` | Subtitle is in target language (already translated), burn-in directly |

#### SubtitleConfig Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Type | String | Subtitle type | "Text" |
| FontSize | Integer | Font size | 60/95/130 |
| FontColor | String | Font color | "#ffffff" |
| Font | String | Font name | "Alibaba PuHuiTi" |
| Y | Float | Vertical position (0=bottom, 1=top) | 0.15 (bottom) |
| TextWidth | Float | Text width ratio | 0.9 |
| Alignment | String | Alignment | "Center" |
| BorderStyle | Integer | Border style | 1 |

---

## Translation Mode Configuration

> **Important Constraints**:
> - This Skill only supports subtitle-level and speech-level translation, **NeedFaceTranslate must be set to false**
> - **SpeechTranslate and SubtitleTranslate cannot be set simultaneously**, choose one based on translation mode
> - **When speech-level translation uses SRT input, must fill `SpeechTranslate.CustomSrtType`**

| Mode | NeedSpeechTranslate | NeedFaceTranslate | Config Parameter | Description |
|------|---------------------|-------------------|------------------|-------------|
| Subtitle-level (subtitle) | `false` | `false` | `SubtitleTranslate` | Translate and replace subtitles in video |
| Speech-level (speech) | `true` | `false` | `SpeechTranslate` | Speech synthesis of translated content |

### Speech-level Translation CustomSrtType Required Rules

> **Mandatory**: When speech-level translation (`NeedSpeechTranslate=true`) uses SRT file as input, **must fill `SpeechTranslate.CustomSrtType`**.
>
> Reference: https://help.aliyun.com/zh/ims/use-cases/introduction-and-examples-of-video-translation-parameters

| SRT Source | CustomSrtType | Description |
|------------|---------------|-------------|
| CaptionExtraction extracted | `SourceSrt` | Default, subtitle is in source language, needs translation |
| User provided | **Must confirm** | Ask user whether subtitle is source or target language |

---

## Subtitle Style Mapping

### Font Size

| User Option | FontSize Value |
|-------------|----------------|
| small | 60 |
| medium | 95 |
| large | 130 |

### Subtitle Position

| User Option | Y Value |
|-------------|---------|
| top | 0.15 |
| center | 0.5 |
| bottom | 0.85 |

---

## Language Codes

### Common Languages

| Language | Code |
|----------|------|
| Chinese | zh |
| English | en |
| Japanese | ja |
| Korean | ko |
| French | fr |
| German | de |
| Spanish | es |
| Russian | ru |
| Portuguese | pt |
| Arabic | ar |

For complete language list, see: [Alibaba Cloud Video Translation Supported Languages](https://help.aliyun.com/zh/ims/use-cases/introduction-and-examples-of-video-translation-parameters)

---

## Complete Examples

### Scenario A: Direct Translation - Subtitle-level Translation (TextSource=OCR_ASR)

```json
{
  "InputConfig": "{\"Type\":\"Video\",\"Video\":\"oss://my-bucket.oss-cn-shanghai.aliyuncs.com/input.mp4\"}",
  "OutputConfig": "{\"MediaURL\":\"https://my-bucket.oss-cn-shanghai.aliyuncs.com/output.mp4\"}",
  "EditingConfig": "{\"SourceLanguage\":\"zh\",\"TargetLanguage\":\"en\",\"NeedSpeechTranslate\":false,\"NeedFaceTranslate\":false,\"TextSource\":\"OCR_ASR\",\"SubtitleTranslate\":{\"OcrArea\":\"Auto\",\"SubtitleConfig\":{\"Type\":\"Text\",\"FontSize\":95,\"FontColor\":\"#ffffff\",\"Font\":\"Alibaba PuHuiTi\",\"Y\":0.15}}}"
}
```

### Scenario B: Using External SRT File (TextSource=SubtitleFile)

```json
{
  "InputConfig": "{\"Type\":\"Video\",\"Video\":\"oss://my-bucket.oss-cn-shanghai.aliyuncs.com/input.mp4\",\"Subtitle\":\"https://my-bucket.oss-cn-shanghai.aliyuncs.com/subtitle.srt\"}",
  "OutputConfig": "{\"MediaURL\":\"https://my-bucket.oss-cn-shanghai.aliyuncs.com/output.mp4\"}",
  "EditingConfig": "{\"SourceLanguage\":\"zh\",\"TargetLanguage\":\"en\",\"NeedSpeechTranslate\":false,\"NeedFaceTranslate\":false,\"TextSource\":\"SubtitleFile\",\"CustomSrtType\":\"SourceSrt\",\"SubtitleTranslate\":{\"OcrArea\":\"Auto\",\"SubtitleConfig\":{\"Type\":\"Text\",\"FontSize\":95,\"FontColor\":\"#ffffff\",\"Font\":\"Alibaba PuHuiTi\",\"Y\":0.15}}}"
}
```

### Speech-level Translation

```json
{
  "InputConfig": "{\"Type\":\"Video\",\"Video\":\"oss://my-bucket.oss-cn-shanghai.aliyuncs.com/input.mp4\"}",
  "OutputConfig": "{\"MediaURL\":\"https://my-bucket.oss-cn-shanghai.aliyuncs.com/output.mp4\"}",
  "EditingConfig": "{\"SourceLanguage\":\"zh\",\"TargetLanguage\":\"en\",\"NeedSpeechTranslate\":true,\"NeedFaceTranslate\":false,\"SpeechTranslate\":{\"VoiceConfig\":{\"Voice\":\"zhiyan_emo\"}}}"
}
```

### Speech-level Translation + SRT Input (Must fill CustomSrtType)

```json
{
  "InputConfig": "{\"Type\":\"Video\",\"Video\":\"oss://my-bucket.oss-cn-shanghai.aliyuncs.com/input.mp4\",\"Subtitle\":\"https://my-bucket.oss-cn-shanghai.aliyuncs.com/subtitle.srt\"}",
  "OutputConfig": "{\"MediaURL\":\"https://my-bucket.oss-cn-shanghai.aliyuncs.com/output.mp4\"}",
  "EditingConfig": "{\"SourceLanguage\":\"zh\",\"TargetLanguage\":\"en\",\"NeedSpeechTranslate\":true,\"NeedFaceTranslate\":false,\"TextSource\":\"SubtitleFile\",\"SpeechTranslate\":{\"CustomSrtType\":\"SourceSrt\",\"VoiceConfig\":{\"Voice\":\"zhiyan_emo\"}}}"
}
```

> **Note**:
> - All modes must set `NeedFaceTranslate: false`
> - When using `TextSource=SubtitleFile`, must specify `Subtitle` field in InputConfig
> - **`InputConfig.Subtitle` must use HTTPS format, `oss://` prefix is prohibited**: `https://<bucket>.oss-<region>.aliyuncs.com/<object>`
> - **Speech-level translation + SRT input requires filling `SpeechTranslate.CustomSrtType`**

---

## Subtitle Extraction Result Format

Subtitle extraction task outputs SRT format file directly to specified OSS path.

### SRT Format Example

```
1
00:00:00,000 --> 00:00:02,500
First sentence

2
00:00:02,500 --> 00:00:05,000
Second sentence
```

### SRT Format Validation and Auto Repair

> **Mandatory**: Before submitting speech translation task, **must check and fix empty subtitle entries in SRT file**!

**Problem Cause**: `InputConfig.Subtitle is invalid` error is usually caused by SRT containing empty subtitle entries:

```srt
3
00:00:08,000 --> 00:00:10,600

4
00:00:10,600 --> 00:00:12,000
This is a normal subtitle
```

Entry 3 above has only sequence number and timeline, no content, does not conform to SRT specification.

**Processing Flow**:
1. Check SRT file, find all empty subtitle entries
2. Auto-delete empty subtitle entries, renumber
3. **Inform user**: "Detected X empty subtitle entries, auto-deleted and renumbered"
4. Upload repaired SRT file

---

## Error Handling

### Common Error Codes

| ErrorCode | Description | Solution |
|-----------|-------------|----------|
| `InvalidParameter` | Parameter format error | Check parameter format |
| `Forbidden` | Insufficient permissions | Check RAM permissions |
| `QuotaExceeded` | Resource quota exceeded | Contact customer service to increase quota |
| `InputConfig.Subtitle is invalid` | SRT format error | **Check if contains empty subtitle entries** |

### Subtitle Extraction Failed

```
Extraction failed → Request user to provide SRT file
```

### Language Detection Failed

```
Analyze extracted result characters:
- Contains Chinese characters → zh
- Contains Japanese characters → ja
- Contains Korean characters → ko
- Mainly English → en
- Cannot determine → Ask user
```

### Speech Translation Failed Handling

> **Mandatory**: After speech translation fails, **DO NOT auto-switch to subtitle translation**, must confirm with user first!
>
> Use `AskUserQuestion` tool to ask user:
> - "Speech translation failed, error message: {ErrorMessage}. Do you want to try switching to subtitle translation mode?"

---

## Limits and Constraints

| Limit Item | Description |
|------------|-------------|
| Video size | Recommended not to exceed 2GB |
| Video duration | Recommended not to exceed 2 hours |
| Supported formats | mp4, mov, avi and other common formats |