# Timeline Basic Structure

The Timeline of Alibaba Cloud ICE is the core configuration for video editing. This document explains how to build a multi-track timeline.

## Core Concepts

### Track

A Timeline consists of multiple types of tracks:

- **VideoTracks** - Video tracks, can have multiple (for picture-in-picture, overlays, etc.)
- **AudioTracks** - Audio tracks, can have multiple (for mixing)
- **SubtitleTracks** - Subtitle tracks, can have multiple (for multi-language subtitles)

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
| `Type` | Material type | `"Video"`, `"Image"`, `"Audio"`, `"Text"` |
| `MediaURL` | Material URL | OSS URL or HTTP URL |
| `In` | In point | Start using the material from the Nth second, default: 0 |
| `Out` | Out point | End the material at the Nth second, default is the material duration |
| `TimelineIn` | Timeline in point | Start position of the clip in the output video, default is the end time of the previous clip |
| `TimelineOut` | Timeline out point | End position of the clip in the output video, default is TimelineIn + Out - In |
| `Volume` | Volume | 0.0-1.0, only valid for audio |

## Multi-Track Rules

1. **Video track overlay**: Video tracks with higher indices will overlay on top of tracks with lower indices
2. **Audio track mixing**: All audio tracks will be mixed and played, pay attention to volume control to avoid clipping
3. **Timeline alignment**: Ensure the TimelineIn/TimelineOut of each track are correctly aligned

## Suggestions for Generating Timeline

Let the LLM based on user requirements:
1. Determine which types of tracks are needed
2. Add appropriate clips for each track
3. Set correct In/Out/TimelineIn/TimelineOut
4. Add optional configurations such as effects and transitions
