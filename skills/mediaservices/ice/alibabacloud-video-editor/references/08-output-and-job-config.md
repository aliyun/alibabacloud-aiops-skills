# Output and Job Configuration

This document explains the parameters outside the Timeline that control the producing job: `OutputMediaConfig`, `EditingProduceConfig`, `MediaMetadata`, `UserData` callbacks, and supported file formats.

## OutputMediaConfig

Defines where and how the output media is written.

### Output to OSS

```json
{
  "MediaURL": "https://{your-bucket}.oss-cn-shanghai.aliyuncs.com/output/result.mp4",
  "Width": 1080,
  "Height": 1920
}
```

- `MediaURL` must be an `http(s)://` OSS address — **`oss://bucket/object` is rejected** (`submit` fails validation before the API call: "OutputMediaConfig.MediaURL must be a valid HTTP/HTTPS URL"). The `oss://` form is IProduction's, not this one.
- The bucket in `MediaURL` must be in the **same region** as the job: a mismatch is rejected at submit with `400 InvalidParameter` — before authentication, so a region typo masquerades as a permission-free parameter error. (IProduction behaves differently and fails *after* the run — `13-intelligent-production.md` §2.)
- If output resolution is not specified, common defaults are 1080×1920 (portrait) or 1920×1080 (landscape).
- `MediaURL` is a **literal** path: a `{timestamp}` placeholder is *not* expanded here and ends up in the object name. Placeholders only work in IProduction's `Output` template (`13-intelligent-production.md` §2). Use a fixed filename and iterate by overwriting the same object.

### Output to VOD (video-on-demand)

```json
{
  "StorageLocation": "your-vod-domain.oss-cn-shanghai.aliyuncs.com",
  "FileName": "output/result.mp4",
  "VodTemplateGroupId": "VOD_NO_TRANSCODE"
}
```

- `StorageLocation` + `FileName` replace `MediaURL` for VOD output.
- `VodTemplateGroupId`: VOD transcoding template group; `"VOD_NO_TRANSCODE"` stores the produced file without further VOD transcoding.

### Common Fields

| Field | Meaning |
|------|------|
| `Width` / `Height` | Output resolution (128-8192 px) |
| `Bitrate` | Target bitrate (bps) |
| `MaxDuration` | Hard cap on output duration (seconds); truncated beyond this |
| `Video` | Video encoding sub-config |

`Video` sub-config:

| Field | Meaning |
|------|------|
| `Codec` | Video codec |
| `Fps` | Output frame rate |
| `Profile` | Codec profile |
| `Crf` | Constant rate factor (quality-based encoding) |
| `Preset` | Encoding speed/quality preset |

Supported output formats: video `MP4`, `M3U8`, `WebM`; audio-only output `MP3`.

## Output to S3-Compatible Storage

Set `OutputMediaTarget: "S3"` and provide the S3 connection info (service endpoint, bucket, object key, and an AccessKey pair) instead of an OSS `MediaURL`:

```json
{
  "OutputMediaTarget": "S3",
  "Endpoint": "s3.ap-southeast-1.amazonaws.com",
  "Bucket": "your-bucket",
  "ObjectKey": "output/result.mp4",
  "AccessKeyId": "<ak>",
  "AccessKeySecret": "<sk>"
}
```

## EditingProduceConfig

Fine-tunes the producing behavior:

| Field | Meaning |
|------|------|
| `CoverConfig.StartTime` | Generate the output cover image from this second |
| `MaxBitrate` | Cap the output bitrate |
| `KeepOriginMaxBitrate` | Keep the original max bitrate (do not raise it) |
| `AudioChannelCopy` | Copy the source audio channels without re-encoding |

## MediaMetadata

Sets metadata (e.g. `Title`, `Description`) written to the output media file.

## UserData / Callbacks

Pass `"UserData": "{\"NotifyAddress\": \"<callback-url>\"}"` to receive a completion callback instead of (or in addition to) polling. The address can be an HTTP(S) endpoint or an MNS queue; the service posts the job result when the job finishes.

## Input File Formats

Input materials commonly include video (MP4, MOV, etc.), audio (MP3, WAV, AAC, etc.) and images (JPG, PNG, GIF, etc.); the producing service handles transcoding, so mixed-format stitching works directly in one timeline.

## Recommendations

- Prefer same-region OSS output with `MediaURL`.
- Always set `Width`/`Height` explicitly when the user mentions resolution; otherwise fall back to 1080×1920 / 1920×1080 based on orientation.
- Use `MaxDuration` when the user asks to "limit the video to N seconds".
- For long jobs, set `UserData.NotifyAddress` to avoid busy-polling.
