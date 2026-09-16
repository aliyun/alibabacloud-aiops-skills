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

- `SubType`: `"In"` for fade-in, `"Out"` for fade-out
- `Duration`: fade duration (seconds)
- `Curve`: volume curve, e.g. `"tri"` (linear); default is `"exp"` (exponential)

Fades work both on audio clips and on video clips with sound (put the same `AFade` effects in the video clip's `Effects`).

## Volume and Mute

The `Volume` effect's `Gain` field controls volume for both video and audio clips:

- `0`: mute (a `Gain: 0` effect on a video clip mutes its sound entirely)
- `1`: original volume
- `(0, 1)`: quieter than original
- `> 1`: louder than original (amplify), valid range is 0-10. Values that are too high can cause clipping/distortion — prefer values ≤ 3 and combine with `ALoudNorm` when normalizing loudness

> **The parameter is `Gain`, not `Volume`**: `{"Type": "Volume", "Volume": 0}` is invalid and makes the job fail (`ProduceFailed`). To mute, use `{"Type": "Volume", "Gain": 0}`.

**Mute a whole video:**

```json
{
  "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video.mp4",
  "Effects": [{ "Type": "Volume", "Gain": 0 }]
}
```

**Mute only a time interval** (add `In`/`Out` to the Volume effect; the rest keeps original volume):

```json
{
  "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video.mp4",
  "Effects": [{ "Type": "Volume", "Gain": 0, "In": 2, "Out": 5 }]
}
```

**Typical voiceover pattern** — mute the video, then re-dub via AudioTracks. Use `In`/`Out` to select the audio segment and `TimelineIn` to set where it starts in the output. Example: take seconds 10-19 of the audio and start it at output second 5:

```json
{
  "VideoTracks": [{ "VideoTrackClips": [{
    "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video.mp4",
    "Effects": [{ "Type": "Volume", "Gain": 0 }]
  }] }],
  "AudioTracks": [{ "AudioTrackClips": [{
    "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/music.mp3",
    "In": 10, "Out": 19, "TimelineIn": 5
  }] }]
}
```

## Audio Loop Playback

`LoopMode` is evidenced for `AudioTrackClips`, not video clips. Set `LoopMode: true` to loop the selected audio segment over the timeline range:

```json
{
  "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/music.wav",
  "LoopMode": true,
  "In": 4, "Out": 10,
  "TimelineIn": 2, "TimelineOut": 14
}
```

This cuts seconds 4-10 of the audio and plays it repeatedly from output second 2 to 14.

**For audio, prefer a single `LoopMode` clip over duplicated clips.** For video repetition, use adjacent clip copies; in a normal template, expose them through `ArrayItems`, repeating the same source as many times as needed and trimming the last copy.

Complete example — mute a video and loop a music segment (seconds 4-10 of the music, looping from output second 2 to 14):

```json
{
  "VideoTracks": [{ "VideoTrackClips": [{
    "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video.mp4",
    "Effects": [{ "Type": "Volume", "Gain": 0 }]
  }] }],
  "AudioTracks": [{ "AudioTrackClips": [{
    "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/music.wav",
    "In": 4, "Out": 10,
    "LoopMode": true,
    "TimelineIn": 2, "TimelineOut": 14
  }] }]
}
```

## Audio Denoise

Both videos with sound and pure audio support denoising via the `ADenoise` effect (`Mode` selects the denoise mode):

```json
{ "Type": "ADenoise", "Mode": 1 }
```

| Mode | Effect |
|------|------|
| `0` | Remove wind noise |
| `1` | Remove general background noise (default choice) |
| `2` | Remove echo/reverberation |
| `3` | Enhance voice clarity |
| `4` | Remove music from voice |

## Loudness Normalization (ALoudNorm)

Normalizes loudness on audio/video clips. When combined with `ADenoise` or `Volume`, the applied order is `ADenoise` > `Volume` > `ALoudNorm`.

```json
{ "Type": "ALoudNorm", "Loudness": -24.0, "TruePeak": -2.0 }
```

## Volume Equalization (AEqualize)

Equalizes volume across the whole output. **Global only** — it must be placed in `EffectTracks`, not on individual clips:

```json
{
  "VideoTracks": [{ "VideoTrackClips": [ {"MediaURL": "https://.../a.mp4"}, {"MediaURL": "https://.../b.mp4"} ] }],
  "EffectTracks": [{ "EffectTrackItems": [{ "Type": "AEqualize", "Peak": 0.95, "Gain": 10 }] }]
}
```

## Extract Audio from Video

To extract a video's audio as a standalone output, put the video file as an AudioTrackClip (no video tracks):

```json
{ "AudioTracks": [{ "AudioTrackClips": [{ "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/video.mp4" }] }] }
```

## Audio Concatenation

On the same audio track, place two clips with adjacent In/Out ranges to join them end-to-end:

```json
{
  "AudioTracks": [{ "AudioTrackClips": [
    { "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/music.wav", "In": 0, "Out": 12 },
    { "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/speech.mp3", "In": 12, "Out": 20 }
  ] }]
}
```

## LLM Generation Suggestions

When the user mentions the following keywords, consider using multi-track audio:
- "Voiceover", "Narration", "Commentary"
- "Background music", "BGM"
- "Mixing"
- "Keep original sound"
- "Mute", "Remove sound", "Lower/raise volume"
- "Loop music", "Repeat audio"
- "Denoise", "Remove noise"
- "Normalize volume", "Even out volume"
- "Extract audio", "Get the sound only"
