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

- The first clip does not need a transition (can add FadeIn if needed)
- Add transitions to middle clips for smooth transitions
- The last clip usually does not have a transition (or only FadeOut)

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
This means截取 from the 30th second to the 45th second of the original video and place it at the 0-15 second position on the timeline.

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

## LLM Generation Suggestions

When the user mentions the following requirements, consider using multi-clip editing:
- "Splice several videos together"
- "Video splicing"
- "Multi-segment video synthesis"
- "Edit together"
- "Clip A followed by clip B"
