# Visual Effects and Transitions

This document introduces how to add transition effects, filters, and visual effects to videos.

## Transition Effects

Transitions are used for smooth transitions between two video clips.

### Basic Usage

```json
{
  "Type": "Video",
  "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video2.mp4",
  "In": 0,
  "Out": 10,
  "TimelineIn": 10,
  "TimelineOut": 20,
  "Effects": [
    {
      "Type": "Transition",
      "SubType": "linearblur",
      "Duration":0.3
    }
  ]
}
```

### Supported Transition Types

| Type | Description | Duration Recommendation |
|------|------|---------------|
| `linearblur` | Linear blur | 0.3-0.5 seconds |
| `circleopen` | Ellipse dissolve | 0.3-0.5 seconds |
| `waterdrop` | Water drop | 0.3-0.5 seconds |
| `displacement` | Vortex | 0.3-0.5 seconds |
| `pinwheel` | Pinwheel | 0.3-0.5 seconds |
| `randomsquares` | Random squares | 0.3-0.5 seconds |
| `squareswire` | Square replace | 0.3-0.5 seconds |

## Video Effects

Effects are used to change the visual presentation of video clips.

### 1. Background Blur

```json
{
  "Type": "Video",
  "MediaURL": "https://...",
  "Effects": [
    {
      "Type": "Background",
      "SubType": "Blur",
      "Radius": 0.1
    }
  ]
}
```

### 2. Background Color

```json
{
  "Type": "Video",
  "MediaURL": "https://...",
  "Effects": [
    {
      "Type": "Background",
      "SubType": "Color",
      "Color": "#000066"
    }
  ]
}
```

## Ambient Effects

Ambient effects add decorative materials to the video (such as starlight, light spots, etc.), making the picture more lively. They are generally used in videos with themes such as cute pets and cute children.

```json
{
  "Type": "Video",
  "MediaURL": "https://...",
  "Effects": [
    {
      "Type": "VFX",
      "SubType": "colorfulradial"
    }
  ]
}
```

### Supported Ambient Effect Types

| Type | Description | 
|------|------|
| `colorfulradial` | Rainbow rays |
| `colorfulstarry` | Brilliant starry sky |
| `flyfire` | Fireflies |
| `heartfireworks` | Heart fireworks |
| `meteorshower` | Meteor shower |
| `moons_and_stars` | Star and moon fairy tale |
| `sparklestarfield` | Stars rushing screen |
| `spotfall` | Light spots falling |
| `starexplosion` | Starlight blooming |
| `starry` | Twinkling stars |


## Picture-in-Picture Effect (PiP)

Use multiple video tracks to achieve picture-in-picture:

```json
{
  "VideoTracks": [
    {
      "VideoTrackClips": [
        {
          "Type": "Video",
          "MediaURL": "https://.../main_video.mp4",
          "In": 0,
          "Out": 30,
          "TimelineIn": 0,
          "TimelineOut": 30
        }
      ]
    },
    {
      "VideoTrackClips": [
        {
          "Type": "Video",
          "MediaURL": "https://.../overlay_video.mp4",
          "In": 0,
          "Out": 10,
          "TimelineIn": 5,
          "TimelineOut": 15,
          "X": 50,
          "Y": 50,
          "Width": 200,
          "Height": 200
        }
      ]
    }
  ]
}
```

### Picture-in-Picture Position Configuration

| Property | Description | Example Value |
|------|------|--------|
| `X` | X-axis offset (pixels) | 50 |
| `Y` | Y-axis offset (pixels) | 50 |
| `Width` | Width of the material in the canvas | 100 |
| `Height` | Height of the material in the canvas | 200 |


## LLM Generation Suggestions

When the user mentions the following requirements, consider adding effects:
- "Add a transition", "Background blur"
- "Add red background"
- "Blur background"
- "Picture-in-picture", "Small window"
- "Make the picture more lively"


