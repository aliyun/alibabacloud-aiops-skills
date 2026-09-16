# Visual Effects and Transitions

This document introduces how to add transition effects, filters, and visual effects to videos.

## Transition Effects

Transitions are used for smooth transitions between two video clips. The `Transition` effect is placed on the **earlier** clip (the one whose end transitions into the next clip). Default duration is 1 second if `Duration` is omitted. The last clip of a track therefore never carries one — there is nothing after it to transition into.

**Duration impact**: a regular `Transition` overlaps the end of the earlier clip with the beginning of the next one, so the total output duration is **shortened** by the transition's `Duration`. To keep the output duration unchanged, use `Type: "DLTransition"` (duration-lock transition) instead — it plays on top of the clips without eating into their duration. Advanced transitions with ids like `OT0001-xxxxxx` require the paid advanced-effect package to be enabled on the account.

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
      "Duration": 0.3
    }
  ]
}
```

### Random Transitions

- `SubType: "random"` randomly picks one from **all** transitions.
- `SubType: "wiperight,perlin"` (comma-separated) randomly picks one from the listed transitions.

### Supported Transition Types

| Type | Description | Duration Recommendation |
|------|------|---------------|
| `linearblur` | Linear blur | 0.3-0.5 seconds |
| `wiperight` | Wipe right | 0.3-1 seconds |
| `perlin` | Perlin / spreading | 0.3-2 seconds |
| `circleopen` | Ellipse dissolve | 0.3-0.5 seconds |
| `waterdrop` | Water drop | 0.3-0.5 seconds |
| `displacement` | Vortex | 0.3-0.5 seconds |
| `pinwheel` | Pinwheel | 0.3-0.5 seconds |
| `randomsquares` | Random squares | 0.3-0.5 seconds |
| `squareswire` | Square replace | 0.3-0.5 seconds |
| `random` | Random pick | - |

Additional common transition `SubType` values: `directional`, `directionalwarp`, `directionalwipe`, `windowslice`, `windowblinds`, `bowTieVertical`, `bowTieHorizontal`, `simplezoom`, `glitchmemories`, `glitchdisplace`, `polka`, `bounce_up`, `bounce_down`, `wipeleft`, `wipedown`, `wipeup`, `morph`, `colordistance`, `circlecrop`, `swirl`, `dreamy`, `dreamyzoom`, `gridflip`, `zoomincircles`, `radial`, `mosaic`, `undulatingburnout`, `crosshatch`, `crazyparametricfun`, `kaleidoscope`, `hexagonalize`, `doomscreentransition_up`, `doomscreentransition_down`, `ripple`, `angular`, `burn`, `circle`, `colorphase`, `crosswarp`, `cube`, `doorway`, `fade`, `fadecolor`, `fadegrayscale`, `flyeye`, `heart`, `luma`, `multiplyblend`, `pixelize`, `polarfunction`, `rotatescalefade`, `squeeze`, `swap`, `wind`.

## VFX Visual Effects

> **Flip is NOT a VFX**: mirror effects must use the dedicated `Flip` effect — `{"Type": "Flip", "Direction": "horizontal"}` and/or `{"Type": "Flip", "Direction": "vertical"}` in the clip's `Effects` (both can be stacked for a horizontal+vertical mirror). `VFX` has no `hflip`/`vflip` SubType; using them fails with `InvalidTimelineFormat: Invalid vfx subType`.

```json
// Horizontal + vertical mirror (both directions at once)
{
  "Type": "Video",
  "MediaURL": "https://.../clip.mp4",
  "Effects": [
    { "Type": "Flip", "Direction": "horizontal" },
    { "Type": "Flip", "Direction": "vertical" }
  ]
}
```

VFX effects change the visual presentation of video. They can be applied at three scopes:

1. **Single clip**: put the `VFX` effect in that clip's `Effects` array. Without start/end times, it lasts for the clip's render time.
2. **Global (whole output)**: put it in an independent `EffectTracks` track (`EffectTrackItems`), not tied to any clip. Without start/end times, it lasts for the whole output.
3. **Partial time range**: on an `EffectTracks` item, set `TimelineIn`/`TimelineOut` (e.g. apply only from second 3 to 7).

```json
// Global VFX on the whole output
{
  "VideoTracks": [{ "VideoTrackClips": [ {"MediaURL": ".../a.mp4"}, {"MediaURL": ".../b.mp4"} ] }],
  "EffectTracks": [{ "EffectTrackItems": [{ "Type": "VFX", "SubType": "h_blur", "TimelineIn": 3, "TimelineOut": 7 }] }]
}
```

> **One effect type per EffectTrack**: each entry in `EffectTracks` may only hold a single effect type in its `EffectTrackItems`. Mixing a `Filter` and a `VFX` in the same `EffectTrackItems` array fails the job — put them in separate EffectTrack entries instead:
>
> ```json
> "EffectTracks": [
>   { "EffectTrackItems": [ { "Type": "Filter", "SubType": "warm" } ] },
>   { "EffectTrackItems": [
>       { "Type": "VFX", "SubType": "h_blur", "TimelineIn": 0, "TimelineOut": 1 },
>       { "Type": "VFX", "SubType": "h_blur", "TimelineIn": 3, "TimelineOut": 7 }
>   ] }
> ]
> ```
> (Multiple items of the **same** type — e.g. several `VFX` time ranges — are fine in one EffectTrack.)

Random VFX work the same as random transitions: `SubType: "random"` (any) or `SubType: "movie,image_in_image"` (pick from the list).

Other common VFX `SubType` values include `mosaic_rect` (rectangular mosaic), `glass` (frosted glass), `fisheye` (fisheye lens), `planet` (little planet). Advanced VFX ids like `OV0001-xxxxxx` require the paid advanced-effect package to be enabled on the account.

### Mask Effects

Use `Type: "VFX"` with a mask `SubType` and an `ExtParams` string of `key=value` pairs:

| SubType | Shape |
|------|------|
| `mask_circle` | Circle / ellipse |
| `mask_rec` | Rectangle (with rounded corners) |
| `mask_linear` | Linear |
| `mask_minor` | Mirror |

Common `ExtParams` keys (coordinates in `[0,1]` are relative to the material, `>1` are absolute pixels):

| Key | Meaning |
|------|------|
| `x`, `y` | Mask center position |
| `width`, `height` | Mask size |
| `radius` | Corner radius (mask_rec) |
| `size` | Size (mask_minor) |
| `angle` | Rotation angle |
| `antialias` | Edge feathering, higher = softer edge |
| `blur_intensity` | Blur strength inside the mask (0 = off). `blur_intensity=1.0` blurs the whole inside — do NOT default it to 1.0 |
| `outer_alpha` | Opacity of the area outside the mask (0 = fully transparent, 1 = keep original). `outer_alpha=1.0` keeps the outside unchanged, which makes the mask **look as if it did nothing** — do NOT default it to 1.0 |

**Only set `blur_intensity` / `outer_alpha` when the user explicitly asks for inside blur or outside transparency.** If the user only specifies shape, size and position, omit these keys so the engine defaults apply:

```json
// User asked for: a circle mask, 200x200 px, centered on the material, first 5 seconds
{
  "Type": "VFX",
  "SubType": "mask_circle",
  "ExtParams": "x=0.5,y=0.5,width=200,height=200,antialias=0.01"
}
```

Set them intentionally only when requested, e.g. blur inside while keeping the outside visible:

```json
{
  "Type": "VFX",
  "SubType": "mask_circle",
  "ExtParams": "x=0.5,y=0.5,width=0.6,height=0.6,antialias=0.01,blur_intensity=0.6,outer_alpha=1.0"
}
```

## Filter Effects

Filters apply color grading. Like VFX they can be applied to a single clip (in its `Effects`), globally (`EffectTracks`), or to a time range (`TimelineIn`/`TimelineOut`).

```json
{ "Type": "Filter", "SubType": "m7" }
```

- Preset filters: `SubType` such as `m7` (gray-orange), `pl3` (spring bud), `warm`, `pj2`, `pj3`.
- Random filters: `SubType: "random"` or a comma-separated list like `"pj2,pj3"`.
- Other available preset families: `m1`-`m8`; `pf1`-`pf9`, `pfa`-`pfc`; `pi1`-`pi4`; `pl1`-`pl4`; `pj1`-`pj4`; single names `delta`, `electric`, `faded`, `slowlived`, `tokoyo`, `urbex`, `warm`; `f1`-`f7`; `pv1`-`pv6`; `a1`-`a6`.

### Custom Color Grading

Set `SubType: "color"` and provide tuning in `ExtParams`:

| Key | Meaning |
|------|------|
| `brightness` | Brightness (negative darkens) |
| `contrast` | Contrast |
| `saturation` | Saturation |
| `kelvin_temperature` | Color temperature (K) |
| `temperature_ratio` | Temperature ratio |
| `tint` | Tint |
| `dark_corner_ratio` | Vignette strength |

```json
{
  "Type": "Filter",
  "SubType": "color",
  "TimelineIn": 3, "TimelineOut": 7,
  "ExtParams": "effect=color,brightness=-10,contrast=10,saturation=10,kelvin_temperature=6000,temperature_ratio=0,tint=0,dark_corner_ratio=50"
}
```

## KenBurns Camera Push/Pull

Apply a slow camera pan/zoom (Ken Burns) to a clip, commonly used for image slideshows and photo albums.

- With no parameters, it defaults to a slow zoom-out (same orientation), a rightward slide (landscape material in a portrait output), or a downward slide (portrait material in a landscape output).
- To control it, set `Start` and `End` as `"x,y,w,h"` rectangles.
- Constraints: `Duration` max 10 seconds; cannot be combined with `Crop`, `Scale`, `Pad`, `Background` effects on the same clip.

```json
{
  "Type": "Image",
  "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/photo.png",
  "Duration": 5,
  "Effects": [{ "Type": "KenBurns", "Start": "0,0.5,0.5,0.5", "End": "0.5,0,0.5,0.5" }]
}
```

## Zoom Effect

Center zoom on a clip: `{ "Type": "Zoom", "StartRate": 1, "EndRate": 1.5, "Duration": 2 }`. `StartRate`/`EndRate` are the zoom ratios at the start/end of the effect (1 = original size), `Duration` is how long the zoom lasts (seconds). **`EndRate` must be greater than `StartRate`** — the shrinking direction fails the job with `InvalidEffectParam`; a "rush-in" punch is a fast 1.0→1.3, not 1.3→1.0.

## Background Effects

### 1. Background Blur

`Radius` (blur radius) ranges `[0.01, 1]`.

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
| `heartbeat` | Heartbeat throb (verified live: **no intensity parameter** — `ExtParams` like `intensity=0.5` are silently ignored; control perceived strength by limiting the effect to ~1 s windows via `EffectTracks` `TimelineIn`/`TimelineOut`) |
| `starexplosion` | Starlight blooming |
| `starry` | Twinkling stars |

## Global Background and Watermark Logo

Use `Type: "GlobalImage"` to display an image from second 0 until the end of the video:

- If the timeline also contains real video clips, the `GlobalImage` automatically spans the whole output duration — no `Duration` needed.
- **If the timeline contains only `GlobalImage` clips (no video), you must set an explicit `Duration`**, otherwise the image only shows on the first frame.
- **Filling the screen**: a background image whose aspect ratio differs from the output canvas (e.g. a square image on a 9:16 output) is placed at its natural size by default, leaving black bars. To make it fill the whole screen, set `"Width": 1, "Height": 1` (canvas-relative sizes; 1 = full extent). Values in [0,1] are relative to the canvas, values >1 are absolute pixels.

Put a background image in a lower track and a watermark logo in a top track:

```json
{
  "VideoTracks": [
    { "VideoTrackClips": [{ "Type": "GlobalImage", "MediaURL": "https://.../background.jpg" }] },
    { "VideoTrackClips": [{ "MediaURL": "https://.../main_video.mp4" }] },
    { "VideoTrackClips": [{ "Type": "GlobalImage", "MediaURL": "https://.../logo.png", "X": 10, "Y": 10, "Width": 247, "Height": 74 }] }
  ]
}
```

Full-screen background behind a digital avatar (background on the low track, avatar on a higher track, both spans the whole output):

```json
{
  "VideoTracks": [
    { "VideoTrackClips": [{ "Type": "GlobalImage", "MediaId": "<background-media-id>", "Width": 1, "Height": 1 }] },
    { "VideoTrackClips": [{ "Type": "AI_Avatar", "AvatarId": "fanyu-broadcast_standing", "Voice": "zhide", "Content": "..." }] }
  ]
}
```

GlobalImage-only timeline (explicit `Duration` required):

```json
{
  "VideoTracks": [
    { "VideoTrackClips": [{ "Type": "GlobalImage", "MediaURL": "https://.../background.jpg", "Duration": 10 }] },
    { "VideoTrackClips": [{ "Type": "GlobalImage", "MediaURL": "https://.../logo.png", "Duration": 10, "X": 10, "Y": 10 }] }
  ]
}
```

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

### Split-Screen with Real-Scene Matting Overlay

For effects like "left half plays the original video, right half replaces the background with an image while keeping the person", stack three video tracks (bottom → top: full original video, the replacement image sized to the half, the matted person on top):

```json
{
  "VideoTracks": [
    { "VideoTrackClips": [{
        "Type": "Video", "MediaURL": "https://.../person_real_scene.mov",
        "In": 0, "Out": 10, "TimelineIn": 0, "TimelineOut": 10
    }] },
    { "VideoTrackClips": [{
        "Type": "Image", "MediaURL": "https://.../background.jpg",
        "Duration": 10, "TimelineIn": 0, "TimelineOut": 10,
        "X": 0.5, "Y": 0, "Width": 0.5, "Height": 1, "AdaptMode": "Cover"
    }] },
    { "VideoTrackClips": [{
        "Type": "Video", "MediaURL": "https://.../person_real_scene.mov",
        "In": 0, "Out": 10, "TimelineIn": 0, "TimelineOut": 10,
        "Effects": [{ "Type": "AI_RealMatting" }, { "Type": "Volume", "Gain": 0 }]
    }] }
  ]
}
```

**Do not set `Width`/`Height` on the matted-person overlay unless the user explicitly asks to resize the person.** Constraining the overlay's width/height rescales the person (they appear smaller), so the result no longer looks like "same person, different background". Set only the position (`X`/`Y`) needed to place the overlay, and let the person keep the original size:

```json
{ "Type": "Video", "MediaURL": "https://.../person.mov",
  "X": 0.5, "Y": 0,
  "Effects": [{ "Type": "AI_RealMatting" }] }
```

Apply `Width`/`Height` to the overlay only when the request is really about fitting/splitting the frame (as in the example above, where the overlay intentionally occupies the right half).

## Combining Filter, VFX, and Transition

You can stack multiple effects in one clip's `Effects` array and add global effects in `EffectTracks`:

```json
{
  "VideoTracks": [{
    "VideoTrackClips": [
      { "MediaURL": ".../h1.mp4", "Out": 6, "Effects": [
        { "Type": "Transition", "SubType": "random", "Duration": 1 },
        { "Type": "VFX", "SubType": "withcircleflashlight" }
      ] },
      { "MediaURL": ".../h2.mp4", "Out": 6, "Effects": [
        { "Type": "Transition", "SubType": "perlin", "Duration": 1 },
        { "Type": "Filter", "SubType": "pl3" }
      ] },
      { "MediaURL": ".../h3.mp4", "Out": 5 }
    ]
  }],
  "EffectTracks": [{ "EffectTrackItems": [
    { "Type": "Filter", "SubType": "warm", "TimelineIn": 11, "TimelineOut": 13 }
  ] }]
}
```

## LLM Generation Suggestions

When the user mentions the following requirements, consider adding effects:
- "Add a transition", "Background blur"
- "Add red background"
- "Blur background"
- "Picture-in-picture", "Small window"
- "Make the picture more lively"
- "Add a filter", "Color grading", "Warm tone"
- "Camera zoom / Ken Burns", "Make photos feel alive"
- "Watermark", "Logo overlay", "Global background"
- "Mask", "Spotlight", "Blur part of the screen"
