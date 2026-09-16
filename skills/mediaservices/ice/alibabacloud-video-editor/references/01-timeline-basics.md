# Timeline Basic Structure

The Timeline of Alibaba Cloud ICE is the core configuration for video editing. This document explains how to build a multi-track timeline.

## Core Concepts

### Track

A Timeline consists of multiple types of tracks:

- **VideoTracks** - Video tracks, can have multiple (for picture-in-picture, overlays, etc.). Images can be placed directly on VideoTracks as `Type: "Image"` clips (the old `ImageTracks` is deprecated, do not use it for new timelines)
- **AudioTracks** - Audio tracks, can have multiple (for mixing)
- **SubtitleTracks** - Subtitle tracks, can have multiple (for multi-language subtitles)
- **EffectTracks** - Effect tracks, hold global effects (`EffectTrackItems`) that are not bound to any clip, e.g. global VFX/Filter applied to the whole output or a time range

Additionally, a Timeline may set:

- **FECanvas** - `{"FECanvas": {"Width": 720, "Height": 1280}}`. Sets a reference canvas so that the same `FontSize` occupies the same proportion of the frame regardless of the actual output resolution (e.g. keep subtitle size consistent between 480P and 720P outputs).

### Clip

Each track contains multiple clips, which define the position on the timeline and the material.

## Complete Timeline Example

```json
{
  "VideoTracks": [
    {
      "VideoTrackClips": [
        {
          "Type": "Video",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video1.mp4",
          "In": 0,
          "Out": 10,
          "TimelineIn": 0,
          "TimelineOut": 10
        }
      ]
    }
  ],
  "AudioTracks": [
    {
      "AudioTrackClips": [
        {
          "Type": "Audio",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/music.mp3",
          "In": 0,
          "Out": 30,
          "TimelineIn": 0,
          "TimelineOut": 30,
          "Effects": [
            {
              "Type": "Volume",
              "Gain": 0.5
            }
          ]
        }
      ]
    }
  ],
  "SubtitleTracks": []
}
```

## Simplified Timeline Example



```json
{
  "VideoTracks": [
    {
      "VideoTrackClips": [
        {
          "Type": "Video",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video1.mp4",
          "Effects": [
            {
              "Type": "Volume",
              "Gain": 0
            }
          ]
        },
        {
          "Type": "Video",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video2.mp4",
          "Effects": [
            {
              "Type": "Volume",
              "Gain": 0
            }
          ]
        }
      ]
    }
  ],
  "AudioTracks": [
    {
      "AudioTrackClips": [
        {
          "Type": "Audio",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/music.mp3",
          "Effects": [
            {
              "Type": "Volume",
              "Gain": 0.5
            }
          ]
        }
      ]
    }
  ],
  "SubtitleTracks": []
}
```

## Key Field Descriptions

| Field | Meaning | Description |
|------|------|------|
| `Type` | Material type | `"Video"`, `"Image"`, `"Audio"`, `"Text"`, `"Subtitle"` (external subtitle file, `FileURL` pointing to an `.srt`/`.ass` file), `"GlobalImage"` (image shown from 0s to the end of the video, used for global backgrounds and watermark logos; when the timeline also contains real video, the `GlobalImage` automatically spans the whole video duration and needs no `Duration` — but if the timeline only contains `GlobalImage` clips, you **must** set an explicit `Duration`, otherwise the image only appears on the first frame) |
| `MediaURL` | Material URL | OSS URL or HTTP URL |
| `MediaId` | Material ID | ICE media asset ID, alternative to `MediaURL` when the asset is registered in ICE |
| `In` | In point | Start using the material from the Nth second, default: 0 |
| `Out` | Out point | End the material at the Nth second, default is the material duration |
| `MaxOut` | Max out point | At most cut up to the Nth second: if the material is longer, cut the first N seconds; if shorter, cut to the end of the material |
| `TimelineIn` | Timeline in point | Start position of the clip in the output video, default is the end time of the previous clip |
| `TimelineOut` | Timeline out point | End position of the clip in the output video, default is TimelineIn + Out - In |
| `Duration` | Display duration | Duration in seconds; commonly used for `Image` clips instead of In/Out |
| `Speed` | Playback speed | E.g. `2` = 2x speed, `3` = 3x speed; works on both VideoTrackClips and AudioTrackClips |
| `AdaptMode` | Scaling mode | `Contain` (fit while keeping aspect ratio), `Cover` (fill the target area, cropping if needed), `Fill` (default, stretch to fill) |
| `X` / `Y` / `Width` / `Height` | Layout | Position and size of the clip in the canvas; values in [0,1] are relative to the canvas, values >1 are absolute pixels |
| `Opacity` | Opacity | 0-1, default 1 (opaque); used for overlays/watermarks |
| `ClipId` / `ReferenceClipId` | Clip alignment | Give a clip a `ClipId` and set `ReferenceClipId` on other clips to align their timing with it (e.g. align background image, BGM and subtitles with a scrolling subtitle) |
| `Comment` | Comment | Free-text annotation, ignored by the renderer |
| `Volume` effect | Volume gain | `Gain`: 0 = mute, 1 = original volume, (0,1) quieter, >1 louder; works on both video and audio clips |

### ClipId / ReferenceClipId Alignment Rules

Cross-track duration alignment: a clip with `ReferenceClipId` automatically adjusts its duration to match the clip that carries the corresponding `ClipId`.

- If the referencing clip is **shorter** than the reference, it is automatically extended by speed-fill (slow-down/`AutoSpeed`) to cover the reference duration
- If it is **longer**, it is truncated to the reference duration
- Works only between clips on **different tracks** (video vs audio vs subtitle); it cannot align two clips on the same track
- Supported on VideoTrackClips, AudioTrackClips and SubtitleTrackClips
- If a clip sets both `TimelineIn`/`TimelineOut` and `ReferenceClipId`, `TimelineIn`/`TimelineOut` wins
- Do not combine `ReferenceClipId` with audio `LoopMode` or track-level `TrackShortenMode`/`TrackExpandMode` on the same clip

## Duration Control

Three mechanisms control the output duration when tracks do not match:

1. **MainTrack (primary track)** — set `"MainTrack": true` on one track (video or audio). The total output duration follows the main track: clips on other tracks are truncated if longer. Without a main track, do not infer the output duration from the longest track: normal-template renders have been observed to stop at the video track and truncate longer audio. Make the intended controlling track explicit and verify the rendered duration.
2. **TrackShortenMode / TrackExpandMode** — set on a non-main track to control how it adapts to the main track's duration:
   - `"TrackShortenMode": "AutoSpeed"` — if the track is longer, speed it up (clips play faster) to fit
   - `"TrackExpandMode": "AutoSpeed"` — if the track is shorter, slow clips down to fill the gap
   - These two settings are ineffective when audio `LoopMode` is set, and cannot be combined with `ClipId` alignment on the same clip
3. **MaxDuration** — set on the Timeline (or in `OutputMediaConfig`): hard cap on output duration, the output is truncated at this value. When both `MainTrack` and `MaxDuration` are set, `MaxDuration` wins.

Example — video track is primary, BGM track auto-adapts its length:

```json
{
  "VideoTracks": [{
    "MainTrack": true,
    "VideoTrackClips": [{ "MediaURL": "https://.../v1.mp4" }, { "MediaURL": "https://.../v2.mp4" }]
  }],
  "AudioTracks": [{
    "TrackShortenMode": "AutoSpeed",
    "TrackExpandMode": "AutoSpeed",
    "AudioTrackClips": [{ "MediaURL": "https://.../bgm.mp3" }]
  }]
}
```

## Multi-Track Rules

1. **At least one video or audio clip is required**: `VideoTracks` and `AudioTracks` cannot both be empty. A timeline containing only `SubtitleTracks` fails with `TimelineFormatError: Both video tracks and audio tracks are empty.` — subtitles are rendered on top of video/audio content, so **a text-only deliverable cannot be built**. What to add is the user's decision, not yours: ask for a background image or BGM, and if they explicitly ruled both out, tell them the request is impossible as stated and ask which constraint to relax (SKILL.md §2.1, §5-D). Never generate or upload an asset just to satisfy this rule.
2. **Video track overlay**: Video tracks with higher indices will overlay on top of tracks with lower indices
3. **Audio track mixing**: All audio tracks will be mixed and played, pay attention to volume control to avoid clipping
4. **Timeline alignment**: Ensure the TimelineIn/TimelineOut of each track are correctly aligned
5. **Sequential concatenation default**: If `TimelineIn`/`TimelineOut` are omitted, clips are placed back-to-back in array order
6. **Audio clip defaults**: If `TimelineIn` is omitted, the audio starts at second 0 of the output; if `TimelineOut` is omitted, the audio is mixed for its whole duration but truncated when it exceeds the total duration of the video tracks. AudioTrackClips may be pure audio files or video files with sound
7. **Audio overlap on one track**: Audio clips on the same track must not overlap in time (overlapping `TimelineIn`/`TimelineOut` ranges cause undefined mixing); to overlap sounds use separate audio tracks

## Suggestions for Generating Timeline

Let the LLM based on user requirements:
1. Determine which types of tracks are needed
2. Add appropriate clips for each track
3. Set correct In/Out/TimelineIn/TimelineOut
4. Add optional configurations such as effects and transitions
