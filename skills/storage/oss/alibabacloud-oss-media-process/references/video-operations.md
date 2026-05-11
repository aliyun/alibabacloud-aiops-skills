# Video Operations Parameter Reference

Detailed parameter specifications for video processing operations. Video operations use slash notation (e.g., `video/convert`, `video/snapshot`). Only one video operation can be specified per request — no chaining with other video/audio/image operations.

## Table of Contents

- [video/convert — Video Transcoding](#videoconvert--video-transcoding)
- [video/snapshot — Single Frame Extraction](#videosnapshot--single-frame-extraction)
- [video/info — Video Metadata](#videoinfo--video-metadata)
- [video/animation — Animated Image Conversion](#videoanimation--animated-image-conversion)
- [video/snapshots — Multi-Frame Extraction](#videosnapshots--multi-frame-extraction)
- [video/sprite — Sprite Sheet Generation](#videosprite--sprite-sheet-generation)
- [video/concat — Video Concatenation](#videoconcat--video-concatenation)
- [hls/m3u8 — HLS Streaming Playlist](#hlsm3u8--hls-streaming-playlist)

---

## video/convert — Video Transcoding

Transcode video to a different format, codec, resolution, or bitrate. Supports both synchronous and asynchronous processing. Use async mode (`--async`) for large files or complex transcoding.

| Parameter | Type | Description |
|-----------|------|-------------|
| `f` | string | Output format: `mp4`, `mkv`, `mov`, `asf`, `avi`, `mxf`, `ts`, `flv`, `webm`, `mp3`, `aac`, `flac`, `oga`, `ac3`, `opus`, `amr` |
| `vcodec` | string | Video codec: `copy` (passthrough), `h264`, `h265`, `vp9` |
| `acodec` | string | Audio codec: `copy` (passthrough), `mp3`, `aac`, `flac`, `vorbis`, `ac3`, `opus`, `pcm`, `amr` |
| `s` | string | Resolution as `WxH` (e.g., `1920x1080`). Width and height must be 64-4096, even numbers |
| `fps` | int | Frame rate (0-240). 0 = use source frame rate |
| `vb` | int | Video bitrate in bps (10000-100000000) |
| `ab` | int | Audio bitrate in bps (1000-10000000) |
| `ss` | int | Start time in milliseconds |
| `t` | int | Duration in milliseconds |
| `vn` | int | Disable video: `1` = remove video stream |
| `an` | int | Disable audio: `1` = remove audio stream |
| `sn` | int | Disable subtitles: `1` = remove subtitle stream |
| `scaletype` | string | Scale type: `crop`, `stretch`, `fill`, `fit` |
| `videoslim` | int | Lightweight HD compression: `1` = enable |
| `crf` | int | Constant Rate Factor (0-51). Lower = better quality, larger file |
| `pixfmt` | string | Pixel format (e.g., `yuv420p`) |
| `ar` | int | Audio sample rate in Hz |
| `ac` | int | Audio channels (1-8) |
| `fpsopt` | int | Frame rate optimization: `0` = exact, `1` = lower, `2` = higher |
| `sopt` | int | Resolution optimization: `0` = exact, `1` = lower, `2` = higher |
| `vbopt` | int | Video bitrate optimization: `0` = exact, `1` = lower, `2` = higher |
| `abopt` | int | Audio bitrate optimization: `0` = exact, `1` = lower, `2` = higher |
| `arotate` | int | Auto-rotate: `0` = disable, `1` = enable (default) |

**Examples:**

```
video/convert:f=mp4,vcodec=h264,s=1920x1080,vb=2000000,fps=30,acodec=aac,ab=100000
video/convert:f=mp4,vcodec=h265,videoslim=1,s=1920x1080,vb=2000000,sn=1
video/convert:f=mp4,vcodec=h264,ss=5000,t=30000
video/convert:f=webm,vcodec=vp9,vb=1500000,acodec=vorbis,ab=128000
video/convert:f=mp3,vn=1,acodec=mp3,ab=192000
```

---

## video/snapshot — Single Frame Extraction

Extract a single frame from a video at a specified time. Supports synchronous processing.

| Parameter | Type | Description |
|-----------|------|-------------|
| `t` | int | Time position in milliseconds. `0` = first frame |
| `w` | int | Output width in pixels |
| `h` | int | Output height in pixels |
| `f` | string | Output format: `jpg`, `png` |
| `m` | string | Mode: `fast` = nearest keyframe (faster but less precise) |
| `ar` | string | Auto-rotate: `auto` (default), `h` (horizontal), `w` (vertical) |

**Examples:**

```
video/snapshot:t=17000,f=jpg,w=800,h=600
video/snapshot:t=0,f=png,w=1920,h=1080
video/snapshot:t=5000,f=jpg,m=fast
```

---

## video/info — Video Metadata

Extract video metadata including duration, resolution, codec, bitrate, stream information. Returns JSON. Synchronous processing. No parameters required.

> **Note**: Anonymous access is NOT supported for video/info.

**Example:**

```
video/info
```

**Sample response data:**

```json
{
  "Format": {
    "Duration": "120.5",
    "Size": "15728640",
    "FormatName": "mov,mp4,m4a,3gp,3g2,mj2"
  },
  "Streams": {
    "VideoStream": [{
      "CodecName": "h264",
      "Width": "1920",
      "Height": "1080",
      "FrameRate": "30.0",
      "BitRate": "2000000"
    }],
    "AudioStream": [{
      "CodecName": "aac",
      "SampleRate": "44100",
      "Channels": "2",
      "BitRate": "128000"
    }]
  }
}
```

---

## video/animation — Animated Image Conversion

Convert a video segment to an animated GIF or WebP image. **Asynchronous ONLY** — requires `--async` flag.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ss` | int | Start time in milliseconds |
| `f` | string | Output format: `gif`, `webp` (**required**) |
| `num` | int | Number of frames to extract |
| `inter` | int | Interval between frames in milliseconds |
| `fps` | int | Frame rate (0-240) |
| `w` | int | Output width (32-4096) |
| `h` | int | Output height (32-4096) |
| `scaletype` | string | Scale type: `crop`, `stretch`, `fill`, `fit` |

**Examples:**

```
video/animation:f=gif,w=480,h=320,inter=1000
video/animation:f=webp,w=320,h=240,fps=10,ss=5000
video/animation:f=gif,w=200,h=200,num=20,scaletype=crop
```

---

## video/snapshots — Multi-Frame Extraction

Extract multiple frames from a video at regular intervals or keyframes. **Asynchronous ONLY** — requires `--async` flag.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ss` | int | Start time in milliseconds |
| `f` | string | Output format: `jpg`, `png` (**required**) |
| `m` | string | Extraction mode: `inter` (interval), `key` (keyframes), `avg` (average), `dhash` (perceptual hash dedup) |
| `num` | int | Number of frames to extract |
| `inter` | int | Interval between frames in milliseconds |
| `w` | int | Output width (32-4096) |
| `h` | int | Output height (32-4096) |
| `pw` | int | Width scaling percentage (0-200) |
| `ph` | int | Height scaling percentage (0-200) |
| `scaletype` | string | Scale type: `crop`, `stretch`, `fill`, `fit` |
| `thr` | int | Threshold (0-100). Used with `dhash` mode for deduplication sensitivity |

**Examples:**

```
video/snapshots:f=jpg,w=640,h=360,scaletype=crop,inter=10000
video/snapshots:f=png,m=key,w=1920,h=1080
video/snapshots:f=jpg,m=dhash,thr=5,w=512,h=512,inter=5000
video/snapshots:f=jpg,num=10,w=320,h=240
```

---

## video/sprite — Sprite Sheet Generation

Generate a sprite sheet (contact sheet) from video frames. **Asynchronous ONLY** — requires `--async` flag.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ss` | int | Start time in milliseconds |
| `f` | string | Output format: `jpg`, `png` (**required**) |
| `m` | string | Extraction mode: `inter` (interval), `key` (keyframes), `avg` (average), `dhash` (dedup) |
| `thr` | int | Threshold (0-100) for dhash mode |
| `num` | int | Number of frames |
| `inter` | int | Interval between frames in milliseconds |
| `sw` | int | Sub-image width (32-4096) |
| `sh` | int | Sub-image height (32-4096) |
| `psw` | int | Sub-image width scaling percentage (0-200) |
| `psh` | int | Sub-image height scaling percentage (0-200) |
| `scaletype` | string | Scale type: `crop`, `stretch`, `fill`, `fit` |
| `tw` | int | Tiles per row (1-100, default 6) |
| `th` | int | Tiles per column (1-100, default 6) |
| `pad` | int | Padding between tiles (0-100, default 2) |
| `margin` | int | Margin around sprite (0-100, default 2) |

**Examples:**

```
video/sprite:f=jpg,sw=200,sh=150,inter=2000,tw=3,th=3,pad=0,margin=0
video/sprite:f=png,sw=320,sh=240,num=36,tw=6,th=6
video/sprite:f=jpg,sw=160,sh=120,m=key,tw=4,th=4,pad=2,margin=2
```

---

## video/concat — Video Concatenation

Concatenate multiple videos into one. **Asynchronous ONLY** — requires `--async` flag. Maximum 11 videos.

The first video is specified via `--source`. Additional videos are appended using `/pre` (before main) and `/sur` (after main) segments with their parameters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `f` | string | Output format (**required**): `mp4`, `mkv`, etc. |
| `vcodec` | string | Video codec (**required**): `h264`, `h265`, `vp9` |
| `acodec` | string | Audio codec (**required**): `aac`, `mp3`, etc. |
| `fps` | int | Frame rate |
| `vb` | int | Video bitrate (bps) |
| `ab` | int | Audio bitrate (bps) |
| `ar` | int | Audio sample rate (Hz) |
| `ac` | int | Audio channels |
| `s` | string | Resolution (`WxH`) |
| `align` | int | Alignment index (which video to use as baseline) |

**Segment syntax** (for additional videos):
- `/pre,o_<base64_key>,ss_<ms>,t_<ms>` — prepend segment
- `/sur,o_<base64_key>,ss_<ms>,t_<ms>` — append segment

Where `<base64_key>` is the URL-safe Base64-encoded OSS object key.

**Examples:**

```
video/concat:f=mp4,vcodec=h264,fps=25,vb=1000000,acodec=aac,ab=96000,ar=48000,ac=2,align=1
```

---

## hls/m3u8 — HLS Streaming Playlist

Generate an HLS (HTTP Live Streaming) M3U8 playlist for transcode-while-play. Synchronous processing.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ss` | int | Start time in milliseconds |
| `t` | int | Duration in milliseconds |
| `ta` | int | Pre-cache segment count |
| `st` | int | Segment duration in milliseconds |
| `initd` | int | Initial buffering duration in milliseconds |
| `vcodec` | string | Video codec: `h264`, `h265` |
| `fps` | int | Frame rate |
| `fpsopt` | int | Frame rate optimization: `0`/`1`/`2` |
| `pixfmt` | string | Pixel format |
| `s` | string | Resolution (`WxH`) |
| `sopt` | int | Resolution optimization: `0`/`1`/`2` |
| `scaletype` | string | Scale type: `stretch`, `crop`, `fill`, `fit` |
| `arotate` | int | Auto-rotate: `0`/`1` |
| `vb` | int | Video bitrate (bps) |
| `vbopt` | int | Video bitrate optimization: `0`/`1`/`2` |
| `crf` | int | Constant Rate Factor |
| `maxrate` | int | Maximum bitrate (bps) |
| `bufsize` | int | Buffer size |
| `an` | int | Disable audio: `0`/`1` |
| `acodec` | string | Audio codec |
| `ar` | int | Audio sample rate (Hz) |
| `ac` | int | Audio channels |
| `aq` | int | Audio quality (0-100) |
| `ab` | int | Audio bitrate (bps) |
| `abopt` | int | Audio bitrate optimization: `0`/`1`/`2` |

**Examples:**

```
hls/m3u8:ss=15000,t=1800000,vcodec=h264,fps=25,s=1280x720,vb=2000000,acodec=aac,ab=128000,st=10000,initd=30000
hls/m3u8:vcodec=h264,s=1920x1080,vb=4000000,acodec=aac,ab=256000
```

---

> Parameter specifications in this document are derived from the [Alibaba Cloud OSS Video Processing documentation](https://help.aliyun.com/zh/oss/user-guide/video-processing) and are reproduced here for quick reference.
