# Subtitles and Title Effects

This document explains how to add various text effects to videos, including static titles, dynamic subtitles, scrolling subtitles, etc.

## Subtitle Track Basics

Subtitles use the `SubtitleTracks` track, supporting multiple text styles and animation effects.

## 1. Static Title

Add a fixed-position title at the top or bottom of the video:

```json
{
  "SubtitleTracks": [
    {
      "SubtitleTrackClips": [
        {
          "Type": "Text",
          "Text": "My Amazing Video",
          "TimelineIn": 0,
          "TimelineOut": 5,
          "Font": "AlibabaPuHuiTi",
          "FontSize": 80,
          "FontColor": "#FFFFFF",
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

### Position Coordinates

- `X`: Horizontal position, 0.0=leftmost, 0.5=center, 1.0=rightmost
- `Y`: Vertical position, 0.0=top, 0.5=center, 1.0=bottom
- `Alignment`: Subtitle alignment method; when Alignment=TopCenter, X does not need to be set, subtitles will automatically center left and right

Common positions:
- Top center: `{"Y": 0.15, "Alignment": "TopCenter"}`
- Bottom center: `{"Y": 0.85, "Alignment": "TopCenter"}`
- Bottom left: `{"X": 0.1, "Y": 0.85}`

Note `FontSize` is a required parameter, common font sizes:
- Top title: 80
- Bottom subtitle: 40
- Watermark: 30


## 2. Dynamic Subtitles (Display Sentence by Sentence)

Add subtitles that change over time to the video:

```json
{
  "SubtitleTracks": [
    {
      "SubtitleTrackClips": [
        {
          "Type": "Text",
          "Text": "First subtitle content",
          "TimelineIn": 0,
          "TimelineOut": 5,
          "Font": "AlibabaPuHuiTi",
          "FontSize": 40,
          "FontColor": "#FFFFFF",
          "StrokeColor": "#000000",
          "StrokeWidth": 2,
          "Alignment": "TopCenter",
          "Y": 0.85
        },
        {
          "Type": "Text",
          "Text": "Second subtitle content",
          "In": 3,
          "Out": 6,
          "TimelineIn": 3,
          "TimelineOut": 6,
          "Font": "Alibaba-PuHuiTi-Regular",
          "FontSize": 40,
          "FontColor": "#FFFFFF",
          "StrokeColor": "#000000",
          "StrokeWidth": 2,
          "Alignment": "TopCenter",
          "Y": 0.85
        },
        {
          "Type": "Text",
          "Text": "Third subtitle content",
          "In": 6,
          "Out": 9,
          "TimelineIn": 6,
          "TimelineOut": 9,
          "Font": "Alibaba-PuHuiTi-Regular",
          "FontSize": 40,
          "FontColor": "#FFFFFF",
          "StrokeColor": "#000000",
          "StrokeWidth": 2,
          "Alignment": "TopCenter",
          "Y": 0.85
        }
      ]
    }
  ]
}
```

## 3. Scrolling Subtitles (End Credits)

Implement a scrolling subtitle effect from bottom to top:

```json
{
  "SubtitleTracks": [
    {
      "SubtitleTrackClips": [
        {
          "Type": "Text",
          "Text": "Director: Zhang San\nStarring: Li Si\nCinematography: Wang Wu\nMusic: Zhao Liu",
          "In": 0,
          "Out": 15,
          "TimelineIn": 0,
          "TimelineOut": 15,
          "Font": "AlibabaPuHuiTi",
          "FontSize": 36,
          "FontColor": "#CCCCCC",
        }
      ]
    }
  ]
}
```

## 4. Styled Title (With Background/Border)

```json
{
  "SubtitleTracks": [
    {
      "SubtitleTrackClips": [
        {
          "Type": "Text",
          "Text": "Important Notice",
          "In": 0,
          "Out": 5,
          "TimelineIn": 0,
          "TimelineOut": 5,
          "Font": "Alibaba-PuHuiTi-Bold",
          "FontSize": 60,
          "FontColor": "#FFD700",
          "Alignment": "TopCenter",
          "Y": 0.85
        }
      ]
    }
  ]
}
```

## Common Fonts

- `Alibaba PuHuiTi` - Alibaba PuHuiTi
- `Microsoft YaHei` - Microsoft YaHei
- `HappyZcool-2016` - ZCOOL KuaiLe

## LLM Generation Suggestions

When the user mentions the following requirements, consider adding subtitles:
- "Add a title"
- "Add subtitles"
- "End credits"
- "Scrolling subtitles"
- "Annotation text"
