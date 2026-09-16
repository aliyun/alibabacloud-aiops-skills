# Multi-Clip Video Editing

Splice multiple video/image materials into a complete video according to the timeline.

## Typical Scenarios

- Vlog multi-clip splicing
- Event multi-camera editing
- Tutorial multi-step demonstration
- Product multi-angle display

## Basic Structure

```
Video Track 1: Video clip 1 → Video clip 2 → Video clip 3 → ...
Audio Track 1: (Optional) Unified background music
```

## Timeline Example: Three Video Clips Spliced

```json
{
  "VideoTracks": [
    {
      "VideoTrackClips": [
        {
          "Type": "Video",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/clip1.mp4",
          "In": 0,
          "Out": 15,
          "TimelineIn": 0,
          "TimelineOut": 15,
          "Effects": [
            {
              "Type": "Transition",
              "SubType": "linearblur",
              "Duration":0.3
            }
          ]
        },
        {
          "Type": "Video",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/clip2.mp4",
          "In": 0,
          "Out": 20,
          "TimelineIn": 15,
          "TimelineOut": 35,
          "Effects": [
            {
              "Type": "Transition",
              "SubType": "linearblur",
              "Duration":0.3
            }
          ]
        },
        {
          "Type": "Video",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/clip3.mp4",
          "In": 0,
          "Out": 10,
          "TimelineIn": 35,
          "TimelineOut": 45
        }
      ]
    }
  ],
  "AudioTracks": [],
  "SubtitleTracks": []
}
```

## Key Configuration Instructions

### Timeline Alignment

Ensure clips are seamlessly connected:
- Clip 1: TimelineOut = 15
- Clip 2: TimelineIn = 15, TimelineOut = 35
- Clip 3: TimelineIn = 35

### Transition Usage

- The first clip does not need a transition (can add an `AFade` In effect if needed)
- Add transitions to middle clips for smooth transitions
- The last clip usually does not have a transition (or only an `AFade` Out effect)

### Material Cropping

Use `In` and `Out` to crop materials:
```json
{
  "Type": "Video",
  "MediaURL": "https://.../long_video.mp4",
  "In": 30,
  "Out": 45,
  "TimelineIn": 0,
  "TimelineOut": 15
}
```
This means cutting from the 30th second to the 45th second of the original video and placing it at the 0-15 second position on the timeline.

Other cropping options:

- `MaxOut`: at most cut up to the Nth second. If the material is longer than N seconds, cut the first N seconds; if shorter, cut to the end of the material. Useful when materials have unknown/varied lengths.
- Random clip: `{"Type": "Clip", "SubType": "RandomClip", "ClipDuration": 5}` in the clip's `Effects` picks a random 5-second segment of the material — handy for batch remixing to produce distinct outputs from the same materials.

Clips without `TimelineIn`/`TimelineOut` are automatically concatenated back-to-back.

## Mixed Material Types

Different types of materials can be mixed in one video:

```json
{
  "VideoTracks": [
    {
      "VideoTrackClips": [
        {
          "Type": "Video",
          "MediaURL": "https://.../intro.mp4",
          "In": 0,
          "Out": 5,
          "TimelineIn": 0,
          "TimelineOut": 5
        },
        {
          "Type": "Image",
          "MediaURL": "https://.../title_card.jpg",
          "In": 0,
          "Out": 3,
          "TimelineIn": 5,
          "TimelineOut": 8
        },
        {
          "Type": "Video",
          "MediaURL": "https://.../main_content.mp4",
          "In": 0,
          "Out": 60,
          "TimelineIn": 8,
          "TimelineOut": 68
        }
      ]
    }
  ]
}
```

## Landscape-to-Portrait Adaptation

When landscape materials are composed into a portrait output, the system scales them proportionally and centers them (black bars top/bottom by default). Alternatives:

- **Blurred background**: add `{"Type": "Background", "SubType": "Blur", "Radius": 0.1}` (Radius in [0.01, 1]) to fill the empty area with a blurred version of the video.
- **Solid color background**: `{"Type": "Background", "SubType": "Color", "Color": "#000066"}`.
- **Three-way split screen**: stack three video tracks, each clip with `"Width": 1, "Height": 0.3333, "X": 0` and `Y` at `0` / `0.3333` / `0.6666`, with `"AdaptMode": "Cover"` (scale to fill the area while keeping aspect ratio, cropping overflow).

## Watermark / Sticker / GIF Overlay

Add images on a second (top) video track with position/size to overlay watermarks or stickers. GIF stickers require `DyncFrames` (the number of frames of the GIF):

```json
{
  "VideoTrackClips": [
    { "Type": "Image", "MediaURL": ".../sticker.png", "TimelineIn": 0, "Duration": 5, "X": 40, "Y": 40, "Width": 300, "Height": 150 },
    { "Type": "Image", "MediaURL": ".../animated.gif", "TimelineIn": 5, "Duration": 5, "X": 20, "Y": 800, "Width": 200, "Height": 200, "DyncFrames": 8 }
  ]
}
```

Note: `Type` defaults to `Video`; image materials must set `"Type": "Image"` and use `Duration` for display length.

## Speed Change

Set `Speed` on video or audio clips, e.g. `"Speed": 2` for 2x playback.

## Flip / Rotate / Crop / Freeze Frame

These effects go in the clip's `Effects` array:

| Effect | Configuration | Description |
|------|------|------|
| Flip | `{"Type": "Flip", "Direction": "horizontal"}` (or `"vertical"`) | Mirror the clip; stack both for a horizontal+vertical mirror. Do NOT use `VFX` with `hflip`/`vflip` SubTypes — they are invalid (`InvalidTimelineFormat: Invalid vfx subType`) |
| Rotate | `{"Type": "Rotate", "Degree": 90}` | Rotate by degrees (90/180/270) |
| Crop | `{"Type": "Crop", "X": 0.3, "Y": 0.3, "Width": 0.4, "Height": 0.4}` | Crop to a region (relative values) |
| FreezeFrame | `{"Type": "FreezeFrame", "Duration": 2}` | Hold the last frame for 2 seconds at the clip end |

## LLM Generation Suggestions

When the user mentions the following requirements, consider using multi-clip editing:
- "Splice several videos together"
- "Video splicing"
- "Multi-segment video synthesis"
- "Edit together"
- "Clip A followed by clip B"
- "Turn landscape videos into portrait", "Add blurred background"
- "Add watermark/sticker", "Speed up/slow down", "Flip/rotate video"
- "Batch produce different videos from the same materials"
