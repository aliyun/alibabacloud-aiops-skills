# Subtitles and Title Effects

This document explains how to add various text effects to videos, including static titles, dynamic subtitles, scrolling subtitles, etc.

## Subtitle Track Basics

Subtitles use the `SubtitleTracks` track, supporting multiple text styles and animation effects.

Important rules:

1. The subtitle text field is **`Content`** (not `Text`).
2. Subtitles can be placed in a dedicated `SubtitleTracks` track, or inside a video clip's `Effects` array (`"Type": "Text"` effect).
3. Entry/exit time is set with `TimelineIn`/`TimelineOut`. If omitted, subtitles in a subtitle track last for the entire output video, while subtitles inside a clip's `Effects` last for that clip's render time.
4. Line breaks inside `Content` can be written as `\n` or `\N`.
5. For subtitles inside a clip's `Effects`, prefer `FixedFontSize` (and `FixedX`/`FixedY`) so the size/position stays constant regardless of video size.
6. **Subtitles that must match spoken narration**: do NOT hand-guess `TimelineIn`/`TimelineOut` for `Type: "Text"` clips against TTS/avatar speech — the timings will drift from the real audio. Use `AI_ASR` with `AlignmentText` (in the `Effects` of the narration/avatar clip) so the platform aligns the text with the actual speech. See `07-smart-media-features.md`.

### External Subtitle Files

Instead of writing each subtitle by hand, load an existing subtitle file with `Type: "Subtitle"`:

```json
{
  "SubtitleTracks": [{
    "SubtitleTrackClips": [{
      "Type": "Subtitle",
      "FileURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/subtitle.srt"
    }]
  }]
}
```

- Supported formats: `.srt` and `.ass` (for `.ass`, styles defined inside the file are used)
- `TimelineIn`/`TimelineOut` still work to limit the display range
- `Font`, `FontSize`, `FontColor` etc. can override the file's style for `.srt`

## 1. Static Title

Add a fixed-position title at the top or bottom of the video:

```json
{
  "SubtitleTracks": [
    {
      "SubtitleTrackClips": [
        {
          "Type": "Text",
          "Content": "My Amazing Video",
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

### Position Coordinates and Alignment

- `X`: Horizontal position, 0.0=leftmost, 0.5=center, 1.0=rightmost
- `Y`: Vertical position, 0.0=top, 0.5=center, 1.0=bottom
- `Alignment`: alignment determines the anchor point of the subtitle text box

9-point alignment values and their default positions:

| Alignment | Alignment style | Default position |
|------|------|------|
| `TopLeft` | Left | Top-left corner |
| `TopCenter` | Center | Top of the vertical axis |
| `TopRight` | Right | Top-right corner |
| `CenterLeft` | Left | Left of the horizontal axis |
| `CenterCenter` | Center | Center of the canvas |
| `CenterRight` | Right | Right of the horizontal axis |
| `BottomLeft` | Left | Bottom-left corner |
| `BottomCenter` | Center | Bottom of the vertical axis |
| `BottomRight` | Right | Bottom-right corner |

For precise positioning, use `Left` / `Center` / `Right`: the anchor becomes the top-left corner, the top-edge midpoint, or the top-right corner of the text box respectively, so `X`/`Y` pin that exact point.

Common positions:
- Top center: `{"Y": 0.15, "Alignment": "TopCenter"}`
- Bottom center: `{"Y": 0.85, "Alignment": "TopCenter"}`
- Bottom left: `{"X": 0.1, "Y": 0.85}`
- Replacing burned-in text: `Alignment: "TopCenter"` + `Y` = the top of the band you measured off 2–3 frames (`13-intelligent-production.md` §3 erases it, `07-smart-media-features.md` re-times the new text), so the replacement sits exactly where the old text sat. The `BottomCenter` default hugs the canvas bottom edge — avoid it; 0.85–0.90 only when the user asks not to glue text to the band. Frame-check the rendered position afterwards — coordinate semantics elsewhere in the engine are not trustworthy.
- Corner credit running over a long body (a whole-show title): `Alignment: "TopRight"`, `Y: 0.03`, `FontSize` 54 on a 1080-wide canvas — 34 is barely legible and reads as a bug, 54 is readable without dominating. Wrap a Chinese title in 《》. Exclude the intro/outro card windows, which already carry the title large and centered: set `TimelineIn`/`TimelineOut` to the body span only.

Note `FontSize` is a required parameter, common font sizes:
- Top title: 80
- Bottom subtitle: 40
- Watermark: 30

## 2. Dynamic Subtitles (Display Sentence by Sentence)

Add subtitles that change over time to the video. Use `Outline`/`OutlineColour` for stroke effects:

```json
{
  "SubtitleTracks": [
    {
      "SubtitleTrackClips": [
        {
          "Type": "Text",
          "Content": "First subtitle content",
          "TimelineIn": 0,
          "TimelineOut": 3,
          "Font": "AlibabaPuHuiTi",
          "FontSize": 40,
          "FontColor": "#FFFFFF",
          "Outline": 2,
          "OutlineColour": "#000000",
          "Alignment": "TopCenter",
          "Y": 0.85
        },
        {
          "Type": "Text",
          "Content": "Second subtitle content",
          "TimelineIn": 3,
          "TimelineOut": 6,
          "Font": "AlibabaPuHuiTi",
          "FontSize": 40,
          "FontColor": "#FFFFFF",
          "Outline": 2,
          "OutlineColour": "#000000",
          "Alignment": "TopCenter",
          "Y": 0.85
        },
        {
          "Type": "Text",
          "Content": "Third subtitle content",
          "TimelineIn": 6,
          "TimelineOut": 9,
          "Font": "AlibabaPuHuiTi",
          "FontSize": 40,
          "FontColor": "#FFFFFF",
          "Outline": 2,
          "OutlineColour": "#000000",
          "Alignment": "TopCenter",
          "Y": 0.85
        }
      ]
    }
  ]
}
```

## 3. Font, Style, Outline, Shadow, Rotation

- `FontSize`: font size. Inside a clip's `Effects`, prefer `FixedFontSize`.
- `Font`: system font name. `FontURL`: OSS URL of a custom font file. When both are set, `FontURL` wins.
- `FontFace`: `{"Bold": true, "Italic": false, "Underline": false}` for bold/italic/underline.
- `Outline` + `OutlineColour`: stroke width and color. `Shadow` + `BackColour`: shadow distance and color.
- `Angle`: counter-clockwise rotation angle of the subtitle.
- `FontColorOpacity`: subtitle color opacity.
- `Spacing` / `LineSpacing`: character spacing / line spacing.

```json
{
  "SubtitleTracks": [{
    "SubtitleTrackClips": [
      {
        "Type": "Text", "X": 0, "Y": 900,
        "Content": "Custom font with black stroke\\nmulti-line supported",
        "FontURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/fonts/custom.ttf",
        "Outline": 1, "OutlineColour": "000000",
        "Alignment": "TopCenter", "FontSize": 40, "FontColor": "#ffffff",
        "FontFace": { "Bold": true, "Italic": false, "Underline": false }
      },
      {
        "Type": "Text", "X": 20, "Y": 20, "Font": "KaiTi",
        "Content": "Shadow text",
        "Alignment": "BottomRight", "FontSize": 40, "FontColor": "#ffffff",
        "Shadow": 3, "BackColour": "#000000"
      }
    ]
  }]
}
```

## 4. Styled Text

- `EffectColorStyle`: one-click styled-text style id, e.g. `"CS0001-000004"`, `"CS0002-000002"`, `"CS0003-000006"`, `"CS0004-000005"`.
- `SubtitleEffects`: multi-layer outline/shadow for custom styled text. Each item has `Type` (`Shadow` or `Outline`), `Color`, plus `XBord`/`YBord` (border thickness), `XShift`/`YShift` (offset), `Blur` (glow), `Opacity`.

```json
{
  "TimelineIn": 0, "TimelineOut": 2,
  "Type": "Text", "Y": 0.2,
  "Font": "WenQuanYi Zen Hei Mono",
  "Content": "Custom styled text",
  "Alignment": "TopCenter", "FontSize": 200, "FontColor": "#FFFFFF",
  "SubtitleEffects": [
    { "Color": "#0420B6", "Type": "Shadow", "XBord": 0.07, "YBord": 0.07, "YShift": 0.06 },
    { "Color": "#F2213F", "Type": "Shadow", "XBord": 0.07, "YBord": 0.07, "YShift": 0.03 },
    { "Color": "#000000", "Type": "Shadow", "XShift": 0.01, "YShift": 0.01 },
    { "Color": "#000000", "Type": "Outline", "XBord": 0.01, "YBord": 0.01 }
  ]
}
```

### Inline Override Codes in Content

Override codes inside `Content` style part of the text. All codes start with two backslashes (`\\`), are wrapped in `{}`, and apply to the text that follows until the matching reset code:

| Code | Effect | Example |
|------|------|------|
| `\\1c&[BBGGRR]&` / `\\3c&[BBGGRR]&` / `\\4c&[BBGGRR]&` | Font / border / shadow color (BGR hex, reversed order) | `"set {\\1c&00FF7F&}green{\\1c} text"` |
| `\\bord[n]` / `\\xbord[n]` / `\\ybord[n]` | Border width (px) | `"set {\\bord3\\3c&EBCE87&}border{\\bord\\3c} style"` |
| `\\b1` / `\\b0` | Bold on / off | `"set {\\b1}bold{\\b0} text"` |
| `\\i1` / `\\i0` | Italic on / off | |
| `\\u1` / `\\u0` | Underline on / off | |
| `\\s1` / `\\s0` | Strike-through on / off | |
| `\\fs[n]` | Font size (px) | `"set {\\fs100}big{\\fs} text"` |
| `\\fn[name]` | Font name (system fonts only) | `"set {\\fnKaiTi}KaiTi{\\fn} font"` |

Codes can be combined: `"{\\1c&00FF00&\\b1\\fs100\\i1}combined{\\1c\\b0\\fs\\i0}"`. For an opaque background box, set `BorderStyle: 3` on the clip.

## 5. Auto Line Wrapping

- `AdaptMode: "AutoWrap"`: wrap when the subtitle exceeds the canvas (or the `TextWidth` limit), so content stays fully visible. `TextWidth` accepts a canvas ratio (e.g. `0.7`) or absolute pixels.
- `AdaptMode: "AutoWrapAtSpaces"`: only wrap at spaces (for English text, avoids splitting words).
- `AdaptMode: "AutoWrapAtSpacesStrict"`: strict space-based wrapping variant.
- `AdaptMode: "AutoScale"`: automatically scale the font size down so the text fits the available width.

## 6. Subtitle Motion Effects

- In/out effects: `AaiMotionInEffect` + `AaiMotionIn` (duration), `AaiMotionOutEffect` + `AaiMotionOut` (duration). They can be stacked together.
- Loop effect: `AaiMotionLoopEffect` + `Ratio` (loop speed).
- Loop effects cannot be used together with in/out effects.

```json
{ "Type": "Text", "Content": "Entrance effect, 2s", "FontSize": 70,
  "AaiMotionInEffect": "rotateflip_in", "AaiMotionIn": 2 }
```

Example effect names:

- In effects: `blur_in`, `wave_in`, `typewriter1_in`, `rotateflip_in`, `zoomin_i`, `slide_left_in`, `slide_right_in`, `slide_up_in`, `slide_down_in`
- Out effects: `dissolve_out`, `slide_down_out`, `fade_out`
- Loop/display effects: `normal_display`, `heartbeat_display`, `rainbrush_display`

## 7. Subtitle Background (Box)

Use `SubtitleEffects` with `Type: "Box"` for a solid-color background behind the text (works with wrapping, styled text and motion effects):

| Field | Description |
|------|------|
| `Color` | Background color, e.g. `"1E90FF"` |
| `XShift` / `YShift` | Background offset (px) |
| `Bord` | Background padding beyond the text |
| `Radius` | Rounded corner radius |
| `Opacity` | Background opacity (e.g. `"0.5"`) |
| `ImageURL` | Use a texture image instead of a solid color |

```json
{
  "Type": "Text", "Content": "Subtitle with box background",
  "AdaptMode": "AutoWrap", "Alignment": "TopCenter", "FontSize": 70, "FontColor": "#F5FFFA",
  "SubtitleEffects": [
    { "Type": "Box", "Color": "1E90FF", "XShift": 20, "YShift": -20, "Bord": 20, "Radius": 20 }
  ]
}
```

## 8. Bubble Text

- `BubbleStyleId`: one-click bubble style id (e.g. `"BS0001-000001"`). Bubble styles are grouped into categories `BS0001`–`BS0007`; the full suffix picks a specific style within a category. Adjust with `BubbleWidth`/`BubbleHeight`; `X`/`Y` position the bubble image's top-left corner.
- Custom bubble: in `SubtitleEffects` use a `Box` with `ImageURL` plus `Width`/`Height` (bubble image size) and `TextArea` (text area position/size relative to the bubble, `"x,y,w,h"`).
- Inside a bubble, text wraps and scales automatically.

```json
{
  "Type": "Text", "Content": "Custom bubble",
  "FontColor": "#000000", "X": 0.1, "Y": 0.3, "BubbleWidth": 0.8, "Alignment": "TopCenter",
  "SubtitleEffects": [{
    "Type": "Box", "Width": 1050, "Height": 250,
    "TextArea": "0.1,0.2,0.8,0.6",
    "ImageURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/bubble.png"
  }]
}
```

## 9. Scrolling Subtitles (End Credits)

Vertical scrolling (bottom to top), e.g. end credits:

- `ScrollStartY` / `ScrollEndY`: scroll start/end Y position (px).
- `ScrollSpeed`: scroll speed (px/s).
- Optional: `ScrollStartFreeze` / `ScrollEndFreeze` (freeze time at start/end), `ScrollStartShift` / `ScrollEndShift` (offset), `ScrollLoopTime` (loop count).
- If `TimelineOut` is omitted, the duration is estimated from the scroll distance automatically.

Horizontal scrolling:

- `ScrollDirection`: e.g. `"Left"`.
- `ScrollStartX` / `ScrollEndX`: start/end X position. `ScrollSpeed`: speed. `ScrollLoop: true`: loop.

Alignment between materials: give the scrolling subtitle a `"ClipId": "ScrollSubtitle"`, then set `"ReferenceClipId": "ScrollSubtitle"` on background images, BGM or banners to align them with it. The vertical scrolling subtitle's start time must equal the intro clip's duration for alignment to work.

```json
{
  "SubtitleTracks": [{
    "SubtitleTrackClips": [{
      "Type": "Text",
      "TimelineIn": 3,
      "ClipId": "ScrollSubtitle",
      "Content": "Director: Zhang San\\nStarring: Li Si\\nCinematography: Wang Wu",
      "FontSize": 50, "FontColor": "#ffffff", "Font": "Alibaba PuHuiTi",
      "X": 0.1, "TextWidth": 0.8, "AdaptMode": "AutoWrap",
      "ScrollStartY": 1120, "ScrollEndY": 200, "ScrollSpeed": 75,
      "ScrollStartFreeze": 2, "ScrollEndFreeze": 2
    }]
  }]
}
```

### Scrolling a narration block in sync with `AI_TTS` — reference the TTS clip, omit `ScrollSpeed`

Validated on a real job (2026-09-03, 1080×1920, 502-char narration over an 88.5 s `zhilun` voiceover): the whole text scrolls bottom→top across the full narration in **one job, no ASR**.

- Give the `AI_TTS` clip a `ClipId` (e.g. `"tts"`), put the **entire** narration in one `Type: "Text"` clip and set `"ReferenceClipId": "tts"` on it.
- Set only `ScrollStartY` (just below the canvas, e.g. `1920`) and `ScrollEndY` (`-(block height + margin)`, so the text fully exits the top). **Omit `ScrollSpeed`** — the engine interpolates Start→End across the referenced clip's duration (supersedes the scroll-distance estimate above), so the scroll spans exactly the narration with no hand-timed math.
- `ScrollEndY` needs the block height in px: `ceil(len(paragraph) / chars_per_line) × line_pitch` summed over paragraphs, where `chars_per_line = floor(canvas_width × TextWidth / FontSize)` and `line_pitch ≈ 1.5 × FontSize`; add one pitch per blank-line paragraph break.
- Pitfall — with an explicit `ScrollSpeed`, the clip's duration is `distance / speed`, so syncing to a voiceover forces a two-pass dance: render → measure the audio duration → recompute speed → re-render. The pass is avoidable, not merely redundant: TTS is deterministic per `Content`, so re-rendering reproduced the audio to the millisecond and `ReferenceClipId` without `ScrollSpeed` lands on the same result in one job.
- Pitfall — `Scroll*` fields only take effect on `Type: "Text"` clips. Attached to an `AI_ASR` effect they are silently ignored (job reports `Success`, subtitles render per sentence at the bottom; `Alignment: "CenterCenter"` is ignored there too, `TopCenter` + `Y` works) → `07-smart-media-features.md`.
- Pitfall — **`AdaptMode: "Cover"` is silently ignored on `Type: "Image"` clips** (same 2026-09-03 job): a 1920×1072 landscape image on a 1080×1920 portrait canvas rendered centered with big black bars, `Success` all along. Fix: crop it yourself with an effect — `{"Type": "Crop", "X": <(1-crop_w)/2>, "Y": 0, "Width": <img_h/img_w × target_ratio>, "Height": 1}` (relative to the source image) — which fills the canvas without distortion. Verify the fill in a sampled frame, never trust the `AdaptMode`.

## 10. Consistent Subtitle Size Across Resolutions (FECanvas)

`FontSize` is a pixel count in the output frame, so the same `FontSize` occupies different proportions at different output resolutions. To keep the subtitle proportion identical across resolutions, set `FECanvas` in the Timeline (usually to the resolution whose look you want to keep):

```json
{
  "FECanvas": { "Width": 720, "Height": 1280 },
  "SubtitleTracks": [{ "SubtitleTrackClips": [
    { "Type": "Text", "Content": "Title", "FontSize": 80, "Alignment": "TopCenter", "Y": 200 }
  ] }]
}
```

## 11 Re-timing a track — a translation, or any rewrite

A cue list written for other text does not fit the text you now have: a translation runs 10–30 % longer than its source for the same meaning, so reusing source cue timings is what produces overflow and flash-by.

Two files drive it — a **script** (one entry per line: `id`, `speaker`, source text, `start`, `end`) and a **glossary** pinning the terms that must not drift plus the per-language style rules:

```json
{
  "characters": { "cassian": { "full_name": "Cassian Whitlock", "es": "Cassian Whitlock", "de": "Cassian Whitlock" } },
  "worldbuilding": { "title": { "term": "Gold Hunter", "es": "Gold Hunter", "de": "Gold Hunter" } },
  "style_rules": { "es": { "max_lines": 2, "max_chars_per_line": 42, "reading_cps": 17, "min_duration": 1.0 } }
}
```

Personal names, place names, world-building nouns, brand and drama titles keep their source spelling unless the user supplies a localized form. Sentence-by-sentence translation drifts by construction and the glossary is the constraint that stops it, so assert every glossary hit mechanically and let a violation fail the build instead of shipping. On-screen text that is not spoken belongs in the glossary as context, **not** in the subtitle track. The shipped defaults are Spanish 42 chars/line at 17 cps and German 40 at 16, both 2 lines and 1.0 s min dwell — confirm against the customer's own style guide when they have one.

Then recompute each cue from three inputs: source timings, the new text, and `style_rules`.

```
lines     = wrap(text, max_chars_per_line, max_lines)      # break on word boundaries
read_need = max(min_duration, len(text) / reading_cps)
sub_start = source line start
sub_end   = min( max(sub_start + read_need, dub_audio_end), next_line_start - 0.05 )
```

- **`sub_end` must cover the dubbed audio** for that line (`audio_start + measured_dub_duration + 0.05`). A subtitle that disappears while its line is still spoken is the defect users report first — which is why cue timings are finalized *after* the dub is measured, not before (`07-smart-media-features.md`).
- **Clamp to the next line's start** so cues never overlap.
- **Reject rather than squeeze**: a wrapped line that still exceeds `max_chars_per_line`, or needs more than `max_lines`, means the *text* is too long. Go back to the fitting ladder in `07-smart-media-features.md` and shorten it; do not shrink the font.
- Keep the new subtitles where the old ones sat (§1 positions).
- **One language per timeline** — a multi-language deliverable is one render per language, never mixed cues on one track.

`scripts/subtitle_localize.py` implements exactly this (wrap + dwell + glossary assertions + SRT emit):

```bash
python "$SKILL_DIR/scripts/subtitle_localize.py" \
  --script script.json --glossary glossary.json \
  --translations trans_es.json --lang es \
  --dub-manifest dub_es.json \        # optional; enforces sub_end ⊇ dub audio
  --out subs_es.json --srt subs_es.srt
```

`--translations` is `{"1": "No tengas miedo.", ...}` keyed by line id. Without `--dub-manifest` it computes reading-based dwell only (subtitles-only jobs); with it, cues are extended to cover the measured dub. Overlong lines and glossary violations exit non-zero — fix the text, do not relax the rule.

## Common Fonts

- `Alibaba PuHuiTi` (also seen as `AlibabaPuHuiTi`) - Alibaba PuHuiTi
- `KaiTi` - KaiTi
- `HappyZcool-2016` - ZCOOL KuaiLe
- `WenQuanYi Zen Hei Mono` - WenQuanYi Zen Hei Mono
- Custom fonts: upload a `.ttf` to OSS and reference it with `FontURL`

## LLM Generation Suggestions

When the user mentions the following requirements, consider adding subtitles:
- "Add a title"
- "Add subtitles"
- "End credits"
- "Scrolling subtitles"
- "Annotation text"
- "Bubble text", "Styled/fancy text", "Subtitle background"
- "Subtitle animation/effect"
