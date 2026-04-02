# Multi-Track Audio Mixing

When a video requires multiple audio elements such as narration, background music, and sound effects, multi-track audio mixing is needed.

## Typical Scenarios

- **Corporate Promotional Videos**: Main video + narration + background music
- **Tutorial Videos**: Screen recording + instructor voiceover + prompt sound effects
- **Vlog**: Original sound + narration + background music

## Track Structure

```
Video Track 1: Main video
Audio Track 1: Original sound (optional)
Audio Track 2: Narration
Audio Track 3: Background music
Audio Track 4: Sound effects
```

## Timeline Example

```json
{
  "VideoTracks": [
    {
      "VideoTrackClips": [
        {
          "Type": "Video",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/main_video.mp4",
          "In": 0,
          "Out": 60,
          "TimelineIn": 0,
          "TimelineOut": 60
        }
      ]
    }
  ],
  "AudioTracks": [
    {
      "AudioTrackClips": [
        {
          "Type": "Audio",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/original_audio.mp3",
          "In": 0,
          "Out": 60,
          "TimelineIn": 0,
          "TimelineOut": 60,
          "Effects": [
            {
              "Type": "Volume",
              "Gain": 0.3
            }
          ]
        }
      ]
    },
    {
      "AudioTrackClips": [
        {
          "Type": "Audio",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/narration.mp3",
          "In": 0,
          "Out": 60,
          "TimelineIn": 0,
          "TimelineOut": 60
        }
      ]
    },
    {
      "AudioTrackClips": [
        {
          "Type": "Audio",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/bgm.mp3",
          "In": 0,
          "Out": 60,
          "TimelineIn": 0,
          "TimelineOut": 60,
          "Effects": [
            {
              "Type": "Volume",
              "Gain": 0.2
            }
          ]
        }
      ]
    }
  ],
  "SubtitleTracks": []
}
```

## Volume Control Recommendations

| Track Type | Recommended Volume | Description |
|----------|----------|------|
| Original sound | 0.2-0.4 | Lower to avoid interfering with narration |
| Narration | 0.8-1.0 | Keep clear |
| Background music | 0.1-0.3 | Set the mood, don't overpower |
| Sound effects | 0.5-0.8 | Adjust according to specific sound effects |

## Fade In/Fade Out Effects

Add fade in/fade out to audio to avoid abruptness:

```json
{
  "Type": "Audio",
  "MediaURL": "https://...",
  "In": 0,
  "Out": 60,
  "TimelineIn": 0,
  "TimelineOut": 60,
  "Effects": [
    {
      "Type": "AFade",
      "SubType": "In",
      "Duration": 1,
      "Curve": "tri"
    },
    {
      "Type": "AFade",
      "SubType": "Out",
      "Duration": 2,
      "Curve": "tri"
    },
    {
      "Type": "Volume",
      "Gain": 0.2
    }
  ]
}
```

- `FadeIn`: Fade in duration (seconds)
- `FadeOut`: Fade out duration (seconds)

## LLM Generation Suggestions

When the user mentions the following keywords, consider using multi-track audio:
- "Voiceover", "Narration", "Commentary"
- "Background music", "BGM"
- "Mixing"
- "Keep original sound"
