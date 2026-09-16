# Slideshow Video Production

Combining multiple images into a video with music and titles is one of the most commonly used video types.

## Typical Scenarios

- Travel photo collections
- Event recaps
- Product showcases
- Birthday/Wedding memorials

## Basic Structure

```
Video Track 1: Image sequence (each image displayed for several seconds)
Audio Track 1: Background music
Subtitle Track 1: Title text
```

## Timeline Example

```json
{
  "VideoTracks": [
    {
      "VideoTrackClips": [
        {
          "Type": "Image",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/photo1.jpg",
          "In": 0,
          "Out": 5,
          "TimelineIn": 0,
          "TimelineOut": 5,
          "Effects": [
            {
              "Type": "Background",
              "SubType": "Blur",
              "Radius": 0.1
            },
            {
              "Type": "Transition",
              "SubType": "linearblur",
              "Duration":0.3
            }
          ]
        },
        {
          "Type": "Image",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/photo2.jpg",
          "In": 0,
          "Out": 5,
          "TimelineIn": 5,
          "TimelineOut": 10,
          "Effects": [
            {
              "Type": "Background",
              "SubType": "Blur",
              "Radius": 0.1
            },
            {
              "Type": "Transition",
              "SubType": "linearblur",
              "Duration":0.3
            }
          ]
        },
        {
          "Type": "Image",
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/photo3.jpg",
          "In": 0,
          "Out": 5,
          "TimelineIn": 10,
          "TimelineOut": 15,
          "Effects": [
            {
              "Type": "Background",
              "SubType": "Blur",
              "Radius": 0.1
            },
            {
              "Type": "Transition",
              "SubType": "linearblur",
              "Duration":0.3
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
          "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/bgm.mp3",
          "In": 0,
          "Out": 15,
          "TimelineIn": 0,
          "TimelineOut": 15,
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
  "SubtitleTracks": [
    {
      "SubtitleTrackClips": [
        {
          "Type": "Text",
          "Content": "Our Wonderful Moments",
          "TimelineIn": 0,
          "TimelineOut": 5,
          "Font": "AlibabaPuHuiTi",
          "FontSize": 80,
          "X": 0.5,
          "Y": 0.15,
          "Outline": 1,
          "OutlineColour": "#000000",
          "Alignment": "TopCenter"
        }
      ]
    }
  ]
}
```

## Key Configuration Instructions

### Image Duration

Image clips (`"Type": "Image"`) typically set their display time with `Duration` (seconds), e.g. `{"Type": "Image", "MediaURL": "...", "Duration": 3}`, instead of `In`/`Out`.

Recommended duration for each slide:
- **Fast switching**: 1-2 seconds/image
- **Normal browsing**: 3-4 seconds/image
- **Careful reading**: 5-6 seconds/image (if there is text on the image)

Total duration = Number of images × Duration per image

### Transition Effects

- The first image does not need a transition
- Add `Transition` to subsequent images for smooth transitions
- Recommend `Fade` (fade in/fade out), universal and elegant

### Background Music

- Music duration should match the total video duration
- Volume recommendation `0.2-0.4`, don't overpower
- Add an `AFade` effect (`SubType: "In"` / `SubType: "Out"`, see `02-multi-track-audio.md`) to avoid abruptness

### Title Style

- Font size: 60-100 (adjust according to video size)
- White text + black outline, ensure clear visibility
- Position: Top (Y=0.15) or Bottom (Y=0.85)

### Camera Motion (KenBurns)

To make static images feel dynamic, add a KenBurns effect to each image clip (slow zoom/pan). With no parameters it defaults to a slow zoom-out; see `04-effects-and-transitions.md` for `Start`/`End` control.

```json
{
  "Type": "Image",
  "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/photo1.jpg",
  "Duration": 5,
  "Effects": [{ "Type": "KenBurns" }]
}
```

### Global Watermark / Logo

Add a persistent watermark or logo over the whole slideshow by putting a `GlobalImage` clip in a top video track (see `04-effects-and-transitions.md`):

```json
{ "VideoTrackClips": [{ "Type": "GlobalImage", "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/logo.png", "X": 10, "Y": 10, "Width": 247, "Height": 74 }] }
```

## LLM Generation Suggestions

When the user mentions the following requirements, consider using the slideshow template:
- "Make photos into a video"
- "Image carousel"
- "Slideshow"
- "Digital photo album"
- "Photo collection"
