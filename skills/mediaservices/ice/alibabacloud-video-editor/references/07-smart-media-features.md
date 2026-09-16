# Smart Media Features (AI)

ICE supports AI-driven features that can participate in editing and producing: speech recognition (ASR), text-to-speech (TTS), digital avatars and matting. Most AI features are available in `cn-beijing`, `cn-shanghai` and `cn-hangzhou` regions — submit the job in one of these regions when using them.

## AI_ASR — Speech Recognition / Karaoke Subtitles

Generate subtitles from a clip's audio, or align existing text with the audio. **Speech recognition is always done by the built-in `AI_ASR` capability — never transcribe the audio yourself (or call an external LLM) and hardcode the lines as `Type: "Text"` clips.** Prefer the platform's ASR capability.

- The clip `Type` is **`AI_ASR`** (there is no `Type: "ASR"`).
- Placement option 1: put it in `SubtitleTracks` as a `SubtitleTrackClip` whose `MediaURL` points to the source video; the service recognizes the speech and renders subtitles on top of it. Style fields (`Font`, `FontSize`, `FontColor`, `Outline`, `Alignment`, `Y`, …) apply as usual.
- Placement option 2 (**preferred for narration / digital-avatar videos**): put it as an entry in the `Effects` array of a clip on `VideoTracks`/`AudioTracks` — `{"Type": "AI_ASR", "AlignmentText": "...", <style fields>}`. The subtitles are then driven by **that clip's own audio** and rendered in the same producing job, in a single step (no second pass over the finished video needed). This is the way to keep subtitles exactly in sync with AI-generated speech (`AI_Avatar`/`AI_TTS`).
- `AlignmentText`: text to align with the audio (word-level timing); when omitted, the service performs speech recognition on the audio and produces subtitles. For a narration clip, set `AlignmentText` to the full script (the same text as `Content`) so every word is aligned with the synthesized speech.
- **Pass `AlignmentText` verbatim and in full** when re-timing text you did not write (a replacement for a burned-in track, a re-voiced line). Never strip words you expect the aligner to miss, and never compensate with hand-timed `Type: "Text"` patches. Non-speech utterances — shouts, grunts, onomatopoeia — are silently skipped by the aligner: expected engine behaviour, not a defect to patch.
- **Accept the aligner's quirks**: display lines get re-split at speech pauses, and occasionally a word attaches to the tail of the previous line.
- The clip's `MediaURL` must still be fetchable when the job starts — signed URLs expire (≈1 h), so submit promptly after generating them.
- The submitted Timeline only says `AI_ASR`; it does not contain the sentence boundaries the aligner chose, so it is the wrong thing to adjust. To shift a subtitle, restyle a line or trim the clip, export the computed timeline first — `export-timeline --project-id <the ProjectId from GetMediaProducingJob>` (`21-timeline-export.md`). The recognized text comes back as an **srt file** on an appended subtitle track, not as per-sentence text clips.

```json
{
  "VideoTracks": [{ "VideoTrackClips": [{ "Type": "Video", "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/speech.mp4" }] }],
  "SubtitleTracks": [{
    "SubtitleTrackClips": [{
      "Type": "AI_ASR",
      "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/speech.mp4",
      "Font": "Alibaba PuHuiTi",
      "FontSize": 80,
      "FontColor": "#FFFFFF",
      "FontFace": { "Bold": true, "Italic": false, "Underline": false },
      "Outline": 2,
      "OutlineColour": "#000000",
      "Alignment": "TopCenter",
      "Y": 0.15,
      "AdaptMode": "AutoWrap"
    }]
  }]
}
```

### Keyword / Focus Highlighting

To auto-detect the key words in the recognized subtitles and highlight them, set `NeedHighlighting: true` and describe the highlight look in `HighlightingStyle` (highlighted words use its `FontColor`; `OutlineColour` + `Outline` give them a stroke). Do this with these parameters — do not hand-edit the text with inline override codes.

> **Colour byte-order pitfall (BGR, not RGB)**: Inside `HighlightingStyle`, colour strings are interpreted as **BGR** in byte order and **must omit the `#` prefix**. This is the opposite of the normal `FontColor`/`OutlineColour` fields on the same clip, which take `#RRGGBB`. The mismatch is silent — no error, just the wrong colour rendered. Verified mappings:
> | Desired colour | RGB hex | `HighlightingStyle` value (BGR, no `#`) |
> |---|---|---|
> | yellow | `#FFFF00` | `"00FFFF"` ✅ |
> | red | `#FF0000` | `"0000FF"` |
> | green | `#00FF00` | `"00FF00"` |
> | orange | `#F6DD14` | `"14DDF6"` |
> Do **not** pass `"#FFFF00"` (with `#`) — the parser fails and renders black. Do **not** pass `"FFFF00"` thinking it is RGB — it is BGR, so `FFFF00` renders **cyan**, not yellow.

> **Placement matters**: `NeedHighlighting` / `HighlightingStyle` only work when the `AI_ASR` clip is placed on a **`VideoTracks` or `AudioTracks` track** — putting them on a `SubtitleTrackClips` entry is silently ignored (no highlighting). Keep the style fields on the same `AI_ASR` clip:

```json
{
  "VideoTracks": [
    { "VideoTrackClips": [{ "Type": "Video", "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/speech.mp4" }] },
    { "VideoTrackClips": [{
      "Type": "AI_ASR",
      "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/speech.mp4",
      "FontSize": 80,
      "FontColor": "#FFFFFF",
      "FontFace": { "Bold": true, "Italic": false, "Underline": false },
      "Alignment": "TopCenter",
      "Y": 0.15,
      "AdaptMode": "AutoWrap",
      "SubtitleEffects": [{ "Type": "Box", "Color": "000000", "Bord": 20, "Radius": 20, "Opacity": "0.5" }],
      "NeedHighlighting": true,
      "HighlightingStyle": {
        "FontColor": "00FFFF",
        "OutlineColour": "873600",
        "Outline": 4
      }
    }] }
  ]
}
```

(The same `AI_ASR` clip may also be placed on `AudioTracks`; the subtitle rendering is driven by the clip, not by `SubtitleTrackClips`.)

## AI_TTS — Text to Speech

Synthesize narration directly in the timeline (no separate TTS call needed). **The audio clip `Type` must be `AI_TTS`** — a bare `Type: "TTS"` does not exist and the job will fail. Put the clip on an `AudioTracks` track with `Voice` and `Content` directly on the clip:

```json
{
  "AudioTracks": [{ "AudioTrackClips": [
    { "Type": "AI_TTS", "Voice": "zhichu", "Content": "First narration segment" },
    { "Type": "AI_TTS", "Voice": "zhichu", "Content": "<speak>Second narration segment<break time=\"500ms\"/>with a pause</speak>" }
  ] }]
}
```

Multiple `AI_TTS` clips can be concatenated back-to-back on the same audio track (they are placed sequentially by default).

| Field | Meaning |
|------|------|
| `Content` | The text to synthesize (supports SSML, see below) |
| `Voice` | Voice id, e.g. `zhichu`, `sicheng`, `zhiqing`, `zhimiao_emo`; CosyVoice voices use the `long*` series. Full catalog: `09-voice-and-avatar-catalog.md` |
| `Format` | Audio format |
| `SpeechRate` | Speaking rate |
| `PitchRate` | Pitch |

The synthesized voice occupies the clip's render time and mixes like normal audio; combine with `Volume` effects to balance it against BGM.

> Note: a timeline containing only `AI_TTS` audio clips is valid (audio track not empty), but if the user also expects a visual result, pair it with video/image content — `VideoTracks` and `AudioTracks` must not both be empty.

### Fitting a line into a shot — rewrite, then re-rate, then stretch

**Priority ladder, in order. Never skip a rung.**

1. **Shorten the text.** A 34-char line at ~10.5 chars/s needs 3.2 s; forcing it into a 2.0 s shot always sounds rushed. Rewriting `Te protegeré de ahora en adelante.` (34) → `Siempre te protegeré.` (21) landed at **1.8 s natural — zero speed-up**, same meaning. This is the rung users ask for by name.
2. **Raise `SpeechRate`.** Measured calibration on a cloned voice: `0 / 100 / 200` → speech span `3.05 / 2.52 / 2.16` s, i.e. ratio `1.00 / 0.83 / 0.71`. Build the curve once per voice with a probe clip and reuse it.
3. **`Speed` on the audio clip** in the assembled Timeline (`06-multi-clip-editing.md`), cap ≈1.5. Last resort, and audible above ~1.2. Never a local `atempo` — ffmpeg does not generate media (`SKILL.md` Hard Rule 2).

**Never change the picture speed to fit the audio.** The voice serves the cut, not the reverse.

### Measure, don't place — per-line micro-render

Placing `AI_TTS` clips directly on the timeline misaligns them. Measured causes:

- **1–5 s of variable leading silence** before the speech starts (leads across 16 lines: 0.00, 0.53, 0.61, 0.76, 1.47, 1.52, 1.68, 1.75, 1.78, 2.05, 2.32, 2.44, 3.01, 4.49 s). Anchoring `TimelineIn` to the intended line start therefore puts the voice seconds late.
- **Without `TimelineOut`, clips fall back to sequential placement**, silently ignoring the spacing you intended — a probe laid out at 10 s intervals collapsed into a back-to-back run.
- **`TimelineOut` truncates; it does not compress.** A 3.3 s take under a 2.0 s cap simply loses its tail.

So render one small clip per line, measure it where it lies, and let the assembled Timeline do the trimming and stretching:

```
for each line:
  1. render a micro clip:  AI_TTS(voice, text, SpeechRate), TimelineIn 0, TimelineOut 8
  2. measure it in place: silencedetect over its signed URL → leading silence, speech end
     (audio analysis only — nothing is downloaded, SKILL.md Hard Rules 1-2)
  3. turn the measurement into numbers: source In = lead - 0.03, Out = speech_end + 0.05
  4. if that duration > window: Speed = duration / window, capped at 1.5   # only after rungs 1-2
  5. record In / Out / Speed and the resulting duration
assemble: plain Audio clips carrying those In/Out (+ Speed), at TimelineIn = intended line start,
          TimelineOut = start + measured duration
```

The final timeline then carries **`Audio` clips of known length**, not `AI_TTS` declarations — deterministic, and re-renderable without paying for synthesis again. The trim and the stretch live in the Timeline as `In`/`Out`/`Speed`, not in a locally edited file, so the next round can change one number and re-submit instead of re-cutting media by hand. Reuse an already-rendered narration the same way instead of re-synthesizing it. When the voice replaces dialogue that is still on the picture, mute the video clip (`{"Type": "Volume", "Gain": 0}`) and keep any music bed on its own audio track.

A cloned `customizedVoice` (`09-voice-and-avatar-catalog.md`) adds two constraints: it cannot be measured outside ICE — DashScope REST rejects it with `418` / `url error` — so the micro-render loop above is the only way to time it; and one clone rendered **silent at non-zero `SpeechRate`** while rate 0 worked, so synthesize at rate 0 and fit with `Speed` on the assembled clip.

### Reading `silencedetect` without fooling yourself

- ffmpeg emits a `silence_end` at EOF, so "the last `silence_start` with no matching end" is **not** the trailing silence. Pair the events first, then treat a span that reaches the file end as trailing.
- `-30 dB / d=0.3` worked for most takes; escalate to `-25` / `-20` when a take yields no usable span. Too strict a threshold (`-35 dB`) latches onto the codec noise floor and reports every segment as the full window length.
- A **long mid-sentence dramatic pause** looks identical to trailing silence. One take put a 2 s beat after `No.`, and a naive "first long silence = end" rule truncated the line to that single word. Take the **last** long-silence start before EOF as the speech end; when a take has an internal pause, either keep it (if the window allows) or place the two halves as separate `Audio` clips with a ~0.2 s gap in the Timeline — never re-concatenate files locally (`SKILL.md` Hard Rule 2).
- **Some texts truncate deterministically.** `Ich lag falsch.` came back cut at the same point across repeated renders, at two speech rates and two window lengths. The fix is a **reworded, semantically equivalent line** (`Ich habe falsch gelegen.`), not another retry — then re-run the cue timing (`03-subtitles-and-titles.md` §11) so the subtitle matches.
- A take can be phonetically bad rather than mis-timed: ASR heard a phantom name where the text said `für dich` ("Freddy"). ASR-verify every trimmed take and reword to clearer phonemes — that is ladder rung 1.

### SSML in Content

`Content` accepts SSML (based on W3C Speech Synthesis Markup Language 1.0, Alibaba subset) to fine-tune the synthesized speech — it controls not only what is read but how: pauses, pronunciation, rate, pitch, volume, emotion and sound effects. Remember to XML-escape special characters inside the text (`"` → `&quot;`, `'` → `&apos;`, `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`).

Support scope:
- Only Chinese and English voices support SSML; supported tags differ slightly between them.
- Smart voice tasks and voice cloning (basic edition) support all tags below.
- Voice cloning (public edition) supports only `<speak>`, `<break>`, `<s>`, `<sub>`, `<w>`, `<phoneme>`, `<say-as>`; `<speak>` accepts only rate/pitch/volume attributes.
- CosyVoice `cosyvoice-v2` voices support only `<speak>`, `<break>`, `<s>`, `<sub alias>` (see `09-voice-and-avatar-catalog.md`).

Elements:

| Element | Purpose |
|------|------|
| `<speak>` | Root element; all SSML content goes inside it. Carries voice/rate/pitch/volume/format/effect/bgm attributes |
| `<emotion category="..." intensity="...">` | Emotion style for multi-emotion voices (`zhimiao_emo`, `zhimi_emo`, `zhibei_emo`, `zhiyan_emo`, `zhitian_emo`); using it on a non-multi-emotion voice fails the job. `intensity` 0.01–2.0, default 1.0 |
| `<break time="500ms"/>` | Insert a pause; `[n]s` with n in [1,10] or `[n]ms` with n in [50,10000]; empty tag, put it inside `<s>` if present |
| `<s>` | Sentence structure; may contain `<break>`, `<w>`, `<phoneme>`, `<say-as>` |
| `<sub alias="...">text</sub>` | Replace the enclosed text with the spoken alias, e.g. `<sub alias="World Wide Web Consortium">W3C</sub>` |
| `<w>` | Word-level segmentation/pronunciation control, e.g. `<w>CHINESE_WORD</w>`; the enclosed word must not mix Chinese with other languages |
| `<phoneme alphabet="py" ph="...">` | Custom pronunciation via pinyin for Chinese text. `ph` is space-separated pinyin with tone number 1-5 (5 = neutral), one syllable per character, e.g. `ph="dian3 dang4 hang2"` for a three-character word |
| `<say-as interpret-as="...">` | Interpret numbers, dates, phone numbers, etc. by type |
| `<soundEvent src="..."/>` | Insert a sound effect at any position; `src` is an HTTP(S) URL of a WAV file on public-read OSS (16 kHz, mono, 16-bit depth, ≤ 2 MB); empty tag |

`<speak>` attributes (Alibaba-specific; each takes precedence over the corresponding job-level request parameter):

| Attribute | Values | Overrides |
|------|------|------|
| `voice` | lowercase voice id, e.g. `siyue` | request `voice` |
| `encodeType` | `PCM`/`WAV`/`MP3` | request `format` |
| `sampleRate` | `8000`/`16000`/`24000`/`48000` | request `sample_rate` |
| `rate` | integer [-500,500], default 0 (>0 faster) | request `speech_rate` |
| `pitch` | integer [-500,500], default 0 (>0 higher) | request `pitch_rate` |
| `volume` | integer [0,100], default 50 (>50 louder) | request `volume` |
| `effect` | `robot`/`lolita`/`lowpass`/`echo`/`eq`/`lpfilter`/`hpfilter` | — |
| `effectValue` | parameters for `eq` (8 band gains in [-20,20] dB, space-separated, e.g. `"1 1 1 1 1 1 1 1"`), `lpfilter`/`hpfilter` (cutoff frequency in (0, sampleRate/2] Hz) | — |
| `bgm` | background music URL (see below) | — |
| `backgroundMusicVolume` | integer [0,100], default 50 | — |

- Only one `effect` per SSML; sound effects add synthesis latency.
- `bgm`: built-in samples (e.g. `http://nls.alicdn.com/bgm/2.wav`) or a custom WAV on public-read OSS — 16 kHz, mono, 16-bit depth, ≤ 3.5 MB for short-text synthesis / ≤ 10 MB for long-text; if the speech outlasts the music, the music loops. A custom bed must **arrive** in that format (the user or upstream hands over the WAV, uploaded to OSS) — converting one locally is barred (`SKILL.md` Hard Rule 2), and no ICE job outputs WAV. Otherwise use a built-in sample, or put the music on its own `AudioTracks` bed in the Timeline instead of inside the TTS clip (`02-multi-track-audio.md`).

`<say-as interpret-as="...">` types:

| Type | Reads as |
|------|------|
| `cardinal` | integer/decimal number (CN up to 20 integer digits; EN up to 13) |
| `digits` | digit by digit (recommend ≤ 20 digits; pauses inserted after 10+ digits) |
| `telephone` | phone number (landline with area code/extension, mobile, service numbers; supports 86/(86)/+86/(+86)/0086 country code) |
| `name` | person name |
| `address` | postal address (Chinese text only) |
| `id` | account id / nickname, character by character |
| `characters` | character by character |
| `punctuation` | punctuation names |
| `date` | date (`2018/08/08`, `10/20~10/31`, `mon-wed`, `19-20 Jan, 2000`, …) |
| `time` | time (`12:00`, `5:30 am`, `09:00-14:00`, …) |
| `currency` | money with currency code/symbol (`$12.00`, `12.50 RMB`, `1,000.00 EUR`, …; supports USD/RMB/CNY/EUR/GBP/JPY/HKD/AUD/CAD/CHF/NOK/SEK/SGD etc.) |

Examples:

```
<speak>Close your eyes and rest.<break time="500ms"/>Now open them.</speak>
<speak voice="xiaogang">This uses the selected voice.</speak>
<speak rate="200" pitch="-100" volume="80">Rate, pitch, and volume are combined here.</speak>
<speak effect="robot">This line uses the robot effect.</speak>
<speak><phoneme alphabet="py" ph="dian3 dang4 hang2">CHINESE_TEXT</phoneme></speak>
<speak voice="zhitian_emo"><emotion category="happy" intensity="1.0">The weather is wonderful today!</emotion></speak>
<speak bgm="http://nls.alicdn.com/bgm/2.wav" backgroundMusicVolume="30" rate="-500" volume="40">Background music plays under this line.</speak>
```

In JSON, escape the inner quotes: `"Content": "<speak rate=\"200\">This line is faster than normal.</speak>"`.

## AI_Avatar — Digital Human Narration

Render a digital human presenting the given text. Use a portrait canvas (e.g. output 1080×1920, 9:16) so the avatar fills the frame.

> **`AI_Avatar` is a clip `Type`, NOT an effect.** Put `{"Type": "AI_Avatar", ...}` directly as a clip in `VideoTrackClips`. Do NOT put it inside another clip's `Effects` array — doing so yields `InvalidTimelineFormat: ... Video MediaId is not valid. MediaId is empty.`

> **One `AI_Avatar` clip for the whole script.** Put the full narration in a single clip's `Content` — the clip duration follows the synthesized speech and the avatar's gestures stay continuous. **Do NOT split the script into one clip per sentence**: each clip is synthesized independently, so the avatar repeats its opening gesture on every sentence and the result looks bad. Likewise, for subtitles aligned with the narration, do NOT hand-estimate `TimelineIn`/`TimelineOut` for `Type: "Text"` subtitle clips — attach `AI_ASR` + `AlignmentText` as an `Effects` entry on the avatar clip (see the one-step example below).

| Field | Meaning |
|------|------|
| `AvatarId` | Official avatar image id, e.g. `fanyu-broadcast_standing`, `xinxin-marketing_standing`, `ziling_ancient_standing`; full list: `09-voice-and-avatar-catalog.md` |
| `Voice` | Voice id for the avatar |
| `Content` | Script text to speak (SSML supported); example narration scripts: `10-narration-script-examples.md` |
| `SpeechRate` | Speaking rate |

Constraints:
- Avatar synthesis output spec is fixed: portrait 9:16, resolution 1080×1920, bitrate 4000 kb/s.
- When the avatar is driven by speech or by text (converted to speech), the resulting speech must be no shorter than 1 second.

```json
{
  "VideoTracks": [{ "VideoTrackClips": [{
    "Type": "AI_Avatar",
    "AvatarId": "fanyu-broadcast_standing",
    "Voice": "zhichu",
    "Content": "Script content"
  }] }]
}
```

### One-step pattern: avatar + custom background + speech-aligned subtitles

A complete newscast-style video in a single producing job: a `GlobalImage` background on a lower video track (with `Width: 1, Height: 1` so it fills the whole screen instead of leaving black bars), the avatar on a higher track, and `AI_ASR` with `AlignmentText` in the avatar clip's `Effects` so the subtitles are word-aligned with the avatar's own speech — no second job, no manual subtitle timing:

```json
{
  "VideoTracks": [
    {
      "VideoTrackClips": [
        { "Type": "GlobalImage", "MediaId": "<background-media-id>", "Width": 1, "Height": 1 }
      ]
    },
    {
      "VideoTrackClips": [
        {
          "Type": "AI_Avatar",
          "AvatarId": "fanyu-broadcast_standing",
          "Voice": "zhide",
          "Content": "Full narration script here (single clip, spoken continuously).",
          "Effects": [
            {
              "Type": "AI_ASR",
              "AlignmentText": "Full narration script here (single clip, spoken continuously).",
              "Font": "Alibaba PuHuiTi",
              "FontSize": 40,
              "FontColor": "#FFFFFF",
              "Outline": 2,
              "OutlineColour": "#000000",
              "Alignment": "TopCenter",
              "Y": 0.85,
              "AdaptMode": "AutoWrap"
            }
          ]
        }
      ]
    }
  ]
}
```

Key points from real productions:

- `AlignmentText` must match the spoken `Content`; the subtitles then follow the real synthesized speech instead of guessed timings.
- The background clip's `Width: 1, Height: 1` stretches it to the full canvas regardless of its native aspect ratio — without this, a square/smaller background sits centered with black bars around it.
- Because the avatar's clip duration follows its speech, the `GlobalImage` background automatically spans the whole output — no `Duration` needed (an avatar video counts as real video).
- If a user asks for "subtitles matching the narration" on an avatar/TTS video, prefer this single-job layout over: (a) per-sentence avatar clips with `ReferenceClipId` subtitles (works, but repeats the avatar's opening gesture per sentence), or (b) a two-stage flow (render the avatar video first, then run `AI_ASR` on it as a second job) — only fall back to two stages when something must be added after the first render.

Complete example — digital human narration combined with a hard subtitle (the subtitle is a regular `Type: "Text"` clip on `SubtitleTracks`, see `03-subtitles-and-titles.md`):

```json
{
  "VideoTracks": [{ "VideoTrackClips": [{
    "Type": "AI_Avatar",
    "Voice": "zhichu",
    "Content": "<speak>Welcome<break time=\"3000ms\"/>Explore with us</speak>",
    "AvatarId": "fanyu-broadcast_standing"
  }] }],
  "SubtitleTracks": [{ "SubtitleTrackClips": [{
    "Type": "Text",
    "Content": "Welcome",
    "TimelineIn": 0, "TimelineOut": 5,
    "Font": "Alibaba PuHuiTi", "FontSize": 80, "FontColor": "#FFFFFF",
    "Outline": 2, "OutlineColour": "#000000",
    "Alignment": "TopCenter", "Y": 0.15
  }] }],
  "AudioTracks": []
}
```

The produced clip's duration follows the synthesized speech; use it together with `ReferenceClipId`/`ClipId` to align BGM or subtitles with the narration.

## AI_Matting / AI_RealMatting — Background Removal

Choose the matting type by the source footage:

- `AI_Matting`: portrait matting for **green-screen / single-color-background** materials. For green-screen footage, set `"Color": "green"` — note the parameter name is **`Color`** (not `ColorType`) and the value is **`green`** (not `GreenScreen`).
- `AI_RealMatting`: matting a person out of **real-scene footage without a green screen** (streets, rooms, outdoor scenes, …). Using `AI_Matting` on real scenes gives poor edges; use `AI_RealMatting`.

Hard rules:
- The effect `Type` is exactly `AI_Matting` or `AI_RealMatting`. There is no bare `Type: "Matting"` effect, and no `SubType: "Matting"` — those fail the job.
- Place the matting effect in the clip's `Effects`; after matting, the transparent result can be overlaid on another track (background video or image):

```json
// Green-screen footage → AI_Matting with Color: "green"
{
  "Type": "Video",
  "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/person_greenscreen.mp4",
  "Effects": [{ "Type": "AI_Matting", "Color": "green" }]
}

// Real-scene footage → AI_RealMatting
{
  "Type": "Video",
  "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/person_real_scene.mp4",
  "Effects": [{ "Type": "AI_RealMatting" }]
}
```

## Harmonization — Color Unification

`{ "Type": "Harmonization", "ReferenceClipId": "clipA" }` adjusts a clip's color tone to match the referenced clip, unifying the look of clips from different sources.

## Usage Notes

- AI features run in the producing pipeline and add processing time — poll status as usual.
- Voice/avatar availability and feature regions can change; when a feature is not supported in the chosen region the job fails, so prefer `cn-shanghai`/`cn-beijing`/`cn-hangzhou`.
- Combine with subtitle effects (see `03-subtitles-and-titles.md`) to build narration + highlighted karaoke subtitles + digital-human videos.
- Choose voices and avatars from `09-voice-and-avatar-catalog.md`; reuse narration script styles from `10-narration-script-examples.md` when the user has no script.
