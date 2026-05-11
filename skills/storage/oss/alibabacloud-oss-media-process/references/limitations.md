# Media Processing Limitations

Constraints and supported formats for Alibaba Cloud OSS media processing (image, video, audio).

## Image Processing Constraints

### Source Image Constraints

| Constraint | Limit |
|------------|-------|
| Maximum file size | 20 MB |
| Maximum single side length | 30,000 px |
| Maximum single side for rotation | 4,096 px |
| Maximum total pixels | 250,000,000 (2.5 billion) |

### Supported Image Source Formats

- JPG / JPEG
- PNG
- BMP
- GIF (animated)
- WebP
- TIFF
- HEIC
- AVIF

### Animated GIF Restrictions

When the source image is an animated GIF, only the following operations are supported:

- `resize`
- `crop`
- `rotate`
- `watermark` (image mode)

All other operations are not applicable to animated GIF images.

### Image Output Format Notes

- `circle` and `rounded-corners` require an output format that supports transparency (e.g., PNG or WebP). If the source is JPG, chain a `format:target=png` operation.
- `interlace` only applies to JPEG output.
- `quality` only applies to JPG and WebP output.

### Blind Watermark Constraints

| Constraint | Limit |
|------------|-------|
| Minimum image dimension | 80 px (both width and height) |
| Maximum image dimension | 10,000 px (both width and height) |
| Supported source formats | JPG, PNG, BMP, WebP, TIFF |
| Pure black/white images | Not supported (watermark may not embed/extract correctly) |

The watermark strength used for extraction (`s`) must match the strength used during embedding. Using a different strength level will result in extraction failure or garbled content.

### IMM Detection Constraints

- All AI detection operations (`faces`, `bodies`, `cars`, `codes`, `labels`, `score`) require IMM service activated and the OSS bucket bound to an IMM project.
- Detection operations are subject to IMM QPS (queries per second) limits. Default limits vary by region and service tier.
- Source images must be in a format supported by IMM (JPG, PNG, BMP, WebP, TIFF).

## Video Processing Constraints

### Source Video Constraints

| Constraint | Limit |
|------------|-------|
| Maximum file size (sync) | Depends on operation timeout |
| Resolution range | 64-4096 px per side (for output) |
| Frame rate range | 0-240 fps |
| Video bitrate range | 10,000-100,000,000 bps |
| Audio bitrate range | 1,000-10,000,000 bps |

### Supported Video Input Formats

avi, mpeg, mpg, dat, divx, xvid, rm, rmvb, mov, qt, asf, wmv, vob, 3gp, mp4, flv, avs, mkv, ts, ogm, nsv, swf, webm

### Supported Video Output Formats (Offline Transcoding)

mp4, mkv, mov, asf, avi, mxf, ts, flv, webm, mp3, aac, flac, oga, ac3, opus, amr

### Video Operation Constraints

| Operation | Mode | Notes |
|-----------|------|-------|
| `video/convert` | Sync / Async | Use async for large files |
| `video/snapshot` | Sync only | Single frame extraction |
| `video/info` | Sync only | Metadata, no anonymous access |
| `video/animation` | **Async ONLY** | GIF/WebP output, 32-4096 px |
| `video/snapshots` | **Async ONLY** | Multi-frame extraction |
| `video/sprite` | **Async ONLY** | Sprite sheet, max 100 tiles per row/column |
| `video/concat` | **Async ONLY** | Max 11 videos |

### Video Animation Constraints

- Output width and height: 32-4096 px
- Output format must be `gif` or `webp`

### Video Sprite Constraints

- Sub-image width and height: 32-4096 px
- Tiles per row: 1-100 (default 6)
- Tiles per column: 1-100 (default 6)
- Padding: 0-100 px (default 2)
- Margin: 0-100 px (default 2)

### Video Concat Constraints

- Maximum number of input videos: 11
- All input videos must be accessible in the same OSS bucket
- Output format, video codec, and audio codec are required parameters

## Audio Processing Constraints

### Supported Audio Input Formats

mp3, wav, aac, flac, ogg, wma, m4a, ac3, opus, amr, and other mainstream formats

### Supported Audio Output Formats

mp3, aac, flac, oga, ac3, opus, amr

### Audio Operation Constraints

| Operation | Mode | Notes |
|-----------|------|-------|
| `audio/convert` | **Async ONLY** | Requires output format (`f`) |
| `audio/concat` | **Async ONLY** | Requires output format (`f`) |
| `audio/info` | Sync only | Metadata, no anonymous access |

### Audio Parameter Constraints

- Audio channels: 1-8
- `aq` (quality) and `ab` (bitrate) are mutually exclusive
- `adepth` (bit depth: 16/24) only applies to FLAC output

## HLS Streaming Constraints

- `hls/m3u8` is synchronous and returns an M3U8 playlist
- Segment duration (`st`) is specified in milliseconds
- Only `h264` and `h265` video codecs are supported

## General Constraints

### Processing Mode Rules

- **Image operations** can be freely chained with each other (except detection/watermark restrictions).
- **Video/audio operations** cannot be chained with image operations.
- Only **one** video/audio operation per request (no chaining between media operations).
- **Async-only operations** will auto-upgrade to async mode even without the `--async` flag.

### Async Processing

- Maximum polling timeout: 600 seconds (10 minutes)
- Polling interval: 5 seconds
- Async operations require `--target-key` to specify the output location

---

> Technical specifications in this document are derived from the [Alibaba Cloud OSS documentation](https://help.aliyun.com/zh/oss/user-guide/overview-China-site) and are reproduced here for quick reference.
