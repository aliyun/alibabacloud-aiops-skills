# 17 Snapshot & ASR — the cloud video-understanding layer

Two API families that let the agent *read* a video without downloading it: `SubmitASRJob` gives the dialogue timeline, `SubmitSnapshotJob` gives frames, a filmstrip and a time↔pixel map. Together they replace local `ffmpeg` frame extraction and any third-party ASR.

**Every number in this document was measured**, not read off the docs. Reference material: a 89.584 s / 1080×1920 vertical short drama, submitted in **`cn-beijing`**. Region availability outside `cn-beijing` is untested — confirm before relying on it elsewhere.

## 0 Which signal, and only that one

Pick by the **question you still have to answer**, not by the shape of the request. These are billed jobs: unlike upstream content-analysis pipelines they return in seconds, but fast is not free, and the wrong signal costs exactly what the right one does.

| Question you still have | Signal | Measured wall time |
|---|---|---|
| Where does a line actually end — so where may a cut land? | `SubmitASRJob` + `SentenceMaxLength` → dialogue timeline + inter-phrase gaps | **10–20 s** |
| What is in the picture across the whole video — is there a burned-in band, how tall, what does each shot hold? | Snapshot `Sprite`, `FrameType: normal` — one tiled image | **12 s** |
| Which pixel on that filmstrip is time *t*? | Snapshot `WebVtt`, `FrameType: normal` — 40 cues | **6 s** |

No open question → no job. A whole-file concatenation, user-supplied `In`/`Out`, a slideshow, a template render: skip this document and go straight to the Timeline (`SKILL.md` §2).

**Position and style are visual questions, not audio ones.** Text at a time and place the user already gave you needs no ASR — the only thing worth checking is what the frame looks like (`11-output-verification.md` §3). ASR earns its cost only when a number you must choose comes out of the *dialogue*.

**What still needs local ffmpeg**: the audio RMS waveform, and only that. No ICE API returns an amplitude envelope, and `AudioQualityAssessment` (`13-intelligent-production.md`) only scores. Produce an audio-only track first, then read it over HTTP — never download the media. `silencedetect` for the audio tail and `volumedetect` for loudness are the other two local passes, both audio-only (`SKILL.md` Hard Rule 2). Everything visual is a cloud job: frames and filmstrips from `SubmitSnapshotJob` (§2), shot boundaries from `omni_segment.py` or a filmstrip you read (§1.6) — ffmpeg never touches the picture.

---

## 1 ASR — the dialogue timeline

`SubmitASRJob` → poll `GetSmartHandleJob`. Async: submit returns a `JobId` with `State: Created`; the result arrives in `JobResult.AiResult` as a **JSON string** that must be parsed again.

### 1.1 Request

Only `InputFile` matters; it takes an `oss://` address **or** a MediaId. `EditingConfig` is a JSON string.

```json
Action        = SubmitASRJob
InputFile     = "f1e2d3c4b5a6f7e8d9c0b1a2f3e4d5c6"
EditingConfig = "{\"SentenceMaxLength\": 4, \"EnableSemanticSentenceDetection\": true}"
```

`StartTime` / `Duration` (`"00:00:00"` / `"00:00:10"`) and `EditingConfig.HotwordLibraryIdList` are documented but **untested here**. The CLI does pass them through (`asr --start-time … --duration …`), which is how you re-recognize a single window of a finished output: register it with `register-media-info`, then ASR each window on that MediaId. AK/SK only — no DashScope key involved (`SKILL.md` §1.3).

### 1.2 Result shape

```json
{
  "State": "Finished",
  "JobResult": { "AiResult": "[{\"content\":\"earthen kiln,\",\"from\":8.48,\"to\":8.81}, …]" },
  "SmartJobInfo": { "JobType": "ASR", "InputConfig": { … } }
}
```

`from` / `to` are **seconds** (float). `State` is `Created` | `Executing` | `Finished` | `Failed` — note this differs from the producing job's `Success`/`Fail` vocabulary. On failure, read `ErrorCode` (e.g. `SpeechTranslationNoValidVocal` when the input has no speech).

### 1.3 Word-level output is NOT reachable, and the failure is silent

The official response example contains `"request_params":"&enable_word_level_result=true"` inside `JobParameters`, which suggests a word-level mode. **It is not exposed.** Three attempts, all measured against the same media:

| `EditingConfig` | Segments | Avg duration | Avg chars |
|---|---|---|---|
| *(omitted)* — baseline | 27 | 1.336 s | 6.63 |
| `{"EnableWordLevelResult": true}` | 27 | 1.336 s | 6.63 |
| `{"RequestParams": "&enable_word_level_result=true"}` | 27 | 1.336 s | 6.63 |

Byte-identical to the baseline. **Undocumented fields are accepted and silently ignored — no error, no effect.** Never infer support from a field appearing in a response example.

### 1.4 `SentenceMaxLength` is the granularity dial

It is the only working substitute for word-level timing:

| `SentenceMaxLength` | Segments | Avg duration | Min duration | Avg chars |
|---|---|---|---|---|
| *(omitted)* | 27 | 1.336 s | 0.38 s | 6.63 |
| `30` | 29 | 1.207 s | — | 7.17 |
| `15` | 29 | 1.294 s | 0.20 s | 7.28 |
| `8` | 35 | 1.057 s | — | 6.03 |
| **`4`** | **56** | **0.647 s** | **0.18 s** | **3.77** |

`SentenceMaxLength: 4` roughly doubles the temporal resolution versus the default. **Use it whenever cut boundaries matter.** The accepted range is **4–50**; anything else fails with `'EditingConfig.SentenceMaxLength' is invalid, input: N, value range: 4-50`.

### 1.5 Trailing punctuation marks the real sentence boundary — gaps do not

Passing **any** `SentenceMaxLength` turns on punctuation. `EnableSemanticSentenceDetection` does *not* control it:

| Config | Segments carrying trailing punctuation |
|---|---|
| no `EditingConfig` | **0 / 27** |
| `SentenceMaxLength: 30`, `EnableSemanticSentenceDetection: false` | **29 / 29** |
| `SentenceMaxLength: 8`, `EnableSemanticSentenceDetection: true` | 29 / 35 |

The 6 unpunctuated segments in the `len8` run are exactly the fragments where `SentenceMaxLength` **forced a split inside a sentence**. That makes punctuation a free boundary classifier:

- segment ends with `，。？！、；` → real sentence boundary
- segment ends without punctuation → mid-sentence truncation, **never cut here**

This matters because the silence gap alone is misleading. Cross-tabulating the 55 seams of the `SentenceMaxLength: 4` run:

| | gap ≥ 0.30 s | gap < 0.30 s |
|---|---|---|
| previous segment **has** punctuation (true boundary) | **14** | 14 |
| previous segment **lacks** punctuation (mid-sentence) | **2** | 25 |

Two seams look safe by the gap rule but sit mid-sentence — `"handmade" | "earthen kiln"` at 0.54 s and `"where are you going" | "get the hanging box"` at 0.41 s. **A gap-only rule mis-cuts 2 of 16 candidates (12.5 %).**

> **Cut rule**: require *both* trailing punctuation on the outgoing segment *and* a gap ≥ 0.30 s. This is the cheap first filter; the boundary rules in `18-edl-and-compile.md` §1.5 and the subtitle-band / `silencedetect` cross-check below still apply — punctuation cannot see an ambient audio tail.

### 1.6 Ground truth — one audio pass, two cloud passes

ASR gives sentence boundaries, but not cut points and not what the picture is doing. Three passes fill that in: the audio one locally over HTTP, the two visual ones as cloud jobs (SKILL.md Hard Rules 1–2 — ffmpeg analyzes audio, ICE renders and snapshots):

| Pass | Command | Gives |
|---|---|---|
| Speech end (**local, audio**) | `ffmpeg -ss A -to B -i <url> -af silencedetect=noise=-20dB:d=0.1 -f null -` | the audio tail, which routinely runs past the visual cut. Raise to −18/−12 dB when rain or crowd noise masks the gaps |
| Shot boundaries (**cloud**) | `scripts/omni_segment.py <url> out.json shots 2` | a cut list within ~0.1–0.2 s of frame-exact — a clip's `in` snaps onto these points (±0.5 s). There is no local scene filter any more: ffmpeg does not touch the picture |
| Subtitle band (**cloud**) | `video_editor.py snapshot --mode normal -i <oss:// object or MediaId> -r <region> --time <ms> --count 12 --interval 1 -O "oss://<bucket>/band/b-{Count}.jpg" --wait` → `snapshot-urls`, then read the signed frames | switch points of the burned-in text, read with your own vision. The tie-breaker when two analyses disagree by ~1 s |

`scripts/omni_segment.py <url-or-file> <out.json> <shots|lines|full> [fps]` (needs `DASHSCOPE_API_KEY`) adds a multimodal second opinion:

- Model is `qwen3.5-omni-plus` (720P@1FPS up to 400 s, 10 h+ audio). **Never `qwen-omni-turbo`** — its timestamps are quantized or hallucinated even on 40 s chunks (suspiciously regular 1.6–2.4 s steps, or beyond the duration).
- ≤ 400 s: pass the signed URL **whole** — no chunking, no re-encode (re-encoding blurs burned-in subtitles and degrades the audio the model listens to). Longer: chunking is a local transcode and is barred (SKILL.md Hard Rule 2) — produce per-window proxies with an ICE job and pass those URLs, or cover the first 400 s and say what you could not see.
- `shots` @ fps=2 → the cut list; this is the primary cut-point source now, and what omni is worth running for. `full` @ fps=2 → a second opinion on the dialogue timeline, catching shouts and non-verbal beats ASR drops. `lines` @ fps=1 is worse than both (subtitle OCR typos, merged sentences, string-typed timestamps).
- fps=2 means 0.5 s frame spacing, so omni alone cannot resolve a fast montage (3 cuts inside 0.2 s). A snapshot job can: `Time` is **milliseconds**, so pin any instant with a one-frame job — `snapshot --mode normal --time 12340 --count 1 --interval 1 -O "oss://<bucket>/cut/c-{Count}.jpg"` — and bisect between the last frame before the change and the first after it to land the cut exactly. Respect the cost inversion (§2.4): a whole-video scan is one cheap job, a pinpoint instant is one job each, so scan broad (omni or a filmstrip) and drill narrow. Never a local scene filter.
- **No key**: omni is unavailable, so cut points come from upstream scene labels and a snapshot filmstrip you read; ASR + the punctuation-and-gap rule + `silencedetect` still cover sentence boundaries. The one real gap is that nobody *listens*: shouts and subtle speech tails under music rest on `silencedetect` numbers. Say so in the report.

### 1.7 Who is speaking — attributing lines to a speaker

Needed whenever a request turns on the speaker: one `VoiceId` per actor, a glossary of character names, or "keep the scenes with X". Run it as an ordered procedure, never a single oracle:

1. **Upstream diarization proposes** when the chain produced it (SKILL.md §2.4): ASR grouped into paragraphs, each with a `speakerId` and `words[]` ms stamps. Measured: it **over-splits** emotional audio — a two-actor source came back as five ids. With no upstream result, skip to step 2.
2. **The on-screen subject adjudicates** every window where the speaker is visible: 2–4 cloud snapshot frames per line window (`--time` at the line in ms, `--count 4`, `--interval 1` — §1.6), read with your own vision. A single-subject close-up with a moving mouth is decisive. In a two-shot a 1 s spacing can land between mouth movements — `--time` is milliseconds, so add one-frame jobs (`--count 1`) at chosen offsets through the window, e.g. every 200–300 ms over the stressed syllables. That is a job per instant, so widen only the windows that actually matter; if the faces still do not separate, fall through to step 3 or to upstream attribution, and say which one decided it.
3. **Timbre (omni) or the user's ear settles what the picture cannot** — off-screen lines, narration, reaction shots where the listener is on camera.

Who moves their mouth is *direct* evidence; timbre similarity is *secondary*. On camera the visual check wins — measured, a timbre model confidently merged a flashback speaker with the present-day one (a boy's clear voice ≈ a young man sobbing), and the frames overturned it. A wrong merge fails silently: one voice ends up on two actors, and only a full re-render fixes it. Off-screen the visual check is blind — escalate rather than guess.

### 1.8 The transcript is a draft — check it before building on it

Everything downstream quotes the transcript: a translation, an on-screen credit, a glossary, a `quote` field in the EDL. An ASR error therefore propagates into every deliverable.

- **Never assume the spoken language from the filename.** `qwen3-asr-flash` with `enable_lid` returns a `language` annotation per segment; sample two windows, since dialogue is often sparse at the head. With no DashScope key, read the transcript yourself — the source language is obvious from it.
- **Cross-check with a second recognizer.** ICE ASR and `qwen3-asr-flash` disagree on tails: measured, ICE returned `he was all my foot` where the line was `It was all my fault`. Reconcile before writing anything that quotes it.
- **When the source carries burned-in subtitles, OCR wins on wording.** `iproduction -f CaptionExtraction` reads what is *printed* (`13-intelligent-production.md` §3). Division of labor: **OCR for wording, ASR for timing and speech presence**.

---

## 2 Snapshot — frames, filmstrip, and the time map

Three calls: `CreateCustomTemplate` (`Type: 2`) → `SubmitSnapshotJob` → `GetSnapshotUrls`. Poll with `GetSnapshotJob`; terminal state is `Success` / `Fail`. Measured completion: **6–12 s**.

### 2.1 The three subtypes

| `Subtype` | `TemplateConfig.Type` | Output | Use for |
|---|---|---|---|
| 1 | `Normal` | N separate JPEGs | Precise frames at one point in time — seam drill-down, or picking a still for a title card. Reject any candidate that carries burned-in subtitles: leftover dialogue text collides with the overlay |
| 2 | `Sprite` | One tiled image | Whole-video filmstrip, geometry under your control |
| 3 | `WebVtt` | One tiled image **+ a `.vtt`** | Whole-video filmstrip **with an authoritative time↔pixel map** |

### 2.2 `FrameType` MUST be `normal` — `intra` silently truncates

With `Count: 40, Interval: 2` (should cover 80 s) on the 89.584 s source:

| | `FrameType: intra` | `FrameType: normal` |
|---|---|---|
| VTT cues | 13 | **40** |
| Time covered | 0–26 s | **0–80 s** |
| Sprite cells filled | 15 / 40 | **40 / 40** |

`intra` only emits frames where an I-frame exists, ignoring `Count`/`Interval` — and **the job still reports `Success`**. Two thirds of the requested data vanishes without a warning. Always pass `FrameType: normal`.

### 2.3 `Sprite` and `WebVtt` use independent, incompatible geometries

**`Sprite` honours the request exactly.** Requesting `CellWidth 135`, `Columns 8`, `Lines 5`, `Padding 4`, `Margin 8` yielded a **1124 × 1232** image — `8×135 + 7×4 + 2×8 = 1124`, `5×240 + 4×4 + 2×8 = 1232`.

Which means omitting the geometry is a real failure, not a neutral default: a `snapshot --mode sprite` run with no `--width`/`--height` came back as **~15 px tiles** (a 118-tile strip totalling 152×180, unreadable). `--width 108 --height 192` gave 1132×2364 — legible enough to read burned-in subtitles and tell characters apart. Always pass both.

**`WebVtt` ignores all of it.** It rejects the parameter outright:

```
InvalidParameter.NotSupport: Vtt snapshot does not support "SpriteSnapshotConfig" parameter
```

Without it the server picks its own layout: **134 px cells, 10 columns**, on a **1340 × 2400** canvas (a 10×10 grid of which only the first 4 rows are used for 40 cues). Note `134 ≠ 135` even though `Width: 135` was requested.

> **Never compute tile coordinates from your request parameters, and never apply a VTT's coordinates to a `Sprite` image.** Doing exactly that produced SSIM 0.30–0.42 during verification — reading coordinates from the VTT instead raised it to 0.87–0.95.

### 2.4 Reading the VTT

Each cue maps a time range to a crop rectangle, relative to the `.vtt` file's own directory:

```
WEBVTT

00:00:00.000 --> 00:00:02.000
webvtt-normal/snapshot-tile-00001.jpg#xywh=0,0,134,240

00:00:12.000 --> 00:00:14.000
webvtt-normal/snapshot-tile-00001.jpg#xywh=804,0,134,240
```

`GetSnapshotUrls` returns the tile image in `SnapshotUrls[0]` and the map in `WebVTTUrl`.

**The tile shows the cue's START instant, not its midpoint.** SSIM of the cropped tile against a frame extracted at each candidate time:

| Cue | vs cue start | vs cue midpoint |
|---|---|---|
| #1 (0–2 s) | **0.953** | 0.434 |
| #7 (12–14 s) | **0.949** | 0.736 |
| #20 (38–40 s) | **0.874** | 0.423 |
| #40 (78–80 s) | **0.900** | 0.401 |
| #7 tile vs 38 s / 78 s (control) | 0.332 / 0.358 | |

So cue `[t, t+Interval)` depicts exactly `t`.

### 2.5 `Time` is milliseconds, `Interval` is seconds

Two different units in one template — the single easiest thing to get wrong. Verified: `Time: 10000, Count: 5, Interval: 2` produced frames at **10 / 12 / 14 / 16 / 18 s** (SSIM against ffmpeg extraction at those instants: 0.918–0.997; cross-comparison against the wrong instants: 0.440–0.576).

### 2.6 Output placeholders

| Mode | Required in the output object | Result |
|---|---|---|
| `Normal` | `{Count}` | `normal-00001.jpg` … — **5-digit zero padding** |
| `Sprite` | `{TileCount}` | one file |
| `WebVtt` | filename must end in **`.vtt`** | `x.vtt` + `x/snapshot-tile-00001.jpg` |

These are a **different placeholder family** from IProduction's `{source}` / `{timestamp}` / `{sequenceId}` / `{resultType}` (`13-intelligent-production.md` §2). Do not mix them.

### 2.7 `GetSnapshotUrls` signs for up to 36 hours

`Timeout` accepts up to **129600 s**, and it works — measured **35.96 h** of remaining validity across four jobs. This removes the expiry churn of STS URLs from `media-info`, which die within ~1 h and force re-signing mid-session (`23-production-pitfalls.md` §3). Prefer snapshot URLs over presigned OSS URLs for anything long-running.

### 2.8 `BlackLevel` / `PixelBlackThreshold` do not move the frames

A/B on the same `Time`/`Interval`/`Count` with and without `BlackLevel: 30, PixelBlackThreshold: 70` returned **byte-identical images** (30131 / 34474 / 106695 / 100986 / 66900 in both runs). These are first-frame black-screen filters only; they are safe to omit and safe to set.

---

## 3 Recommended recipe — read a whole video in two jobs

```jsonc
// 1. Filmstrip + authoritative time map        (~6 s)
CreateCustomTemplate  Type=2  Subtype=3
  TemplateConfig = {"Type":"WebVtt","FrameType":"normal",
                    "Time":0,"Count":<ceil(duration/interval)>,"Interval":2,
                    "Width":135,"Height":240,"IsSptFrag":true}
SubmitSnapshotJob     Output = oss://<bucket>/<prefix>/strip.vtt
GetSnapshotUrls       Timeout=129600   → SnapshotUrls[0] + WebVTTUrl

// 2. Dialogue timeline with fine granularity   (~20 s)
SubmitASRJob  InputFile=<mediaId>
  EditingConfig = {"SentenceMaxLength":4,"EnableSemanticSentenceDetection":true}
GetSmartHandleJob → JobResult.AiResult  (parse the JSON string)
```

Set `Count` to cover the **whole** duration: `Count × Interval ≥ duration`, otherwise the tail is silently missing (89.584 s at `Interval 2` needs `Count ≥ 45`, not 40 — the 40-cue run above stops at 80 s and drops the last 9.5 s).

Then drill into suspicious seams with `Subtype: 1` (`Normal`, `Time` = seam in ms, `Count` 3–5, small `Interval`). Cost inversion worth noting: **on ICE a whole-video scan is one cheap job, while pinpoint drill-down costs one job per location** — the opposite of local ffmpeg, where seeking a single frame is nearly free. Scan broadly first, drill narrowly second.

The sprite/VTT tile is legible enough to read burned-in subtitles at 135 px wide (verified on 1080×1920 source), so one image usually establishes the whole plot and dialogue.

---

## 4 Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Only ⅓ of the requested frames, job says `Success` | `FrameType: intra` | Use `FrameType: normal` (§2.2) |
| `InvalidParameter.NotSupport: Vtt snapshot does not support "SpriteSnapshotConfig"` | `SpriteSnapshotConfig` sent to a `WebVtt` template | Drop it; `WebVtt` geometry is server-chosen (§2.3) |
| Cropped tiles do not match the video (SSIM ≈ 0.3–0.4) | Coordinates computed from request params, or a VTT's coordinates used on a `Sprite` image | Read `xywh` from the VTT of that same job (§2.3) |
| Tile looks half a beat late | Assumed the cue midpoint | The tile is the cue **start** (§2.4) |
| Frames land at the wrong instants | `Time` treated as seconds | `Time` is **ms**, `Interval` is **s** (§2.5) |
| Output files overwrite each other | Missing `{Count}` / `{TileCount}`, or `.vtt` suffix absent | §2.6 |
| Last seconds of the video absent from the strip | `Count × Interval < duration` | Raise `Count` (§3) |
| `EditingConfig` field has no effect and no error | The field is undocumented | Only `SentenceMaxLength`, `EnableSemanticSentenceDetection`, `HotwordLibraryIdList` exist (§1.3) |
| ASR text has no punctuation | `EditingConfig` omitted entirely | Pass `SentenceMaxLength` (§1.5) |
| A kept line is cut mid-sentence although the gap looked wide | Gap-only boundary rule | Require trailing punctuation **and** gap ≥ 0.30 s (§1.5) |
| `SpeechTranslationNoValidVocal` | Input has music/ambience but no speech | Expected; not a configuration error |
| Snapshot job cannot read/write the bucket | Bucket not registered in IMS storage management, or not in the job's region | Register it, keep media + bucket + job in one region |

---

## 5 API quick reference

- `SubmitASRJob` — `InputFile`, `EditingConfig`, `StartTime`, `Duration`, `Title`, `Description`, `UserData` → `JobId`, `State`. [docs](https://help.aliyun.com/zh/ims/developer-reference/api-ice-2020-11-09-submitasrjob)
- `GetSmartHandleJob` — `JobId` → `State`, `JobResult.AiResult` (JSON string), `SmartJobInfo`. Serves every smart job type (ASR, TextToSpeech, TextGenerate). Queries only the **last year** of jobs. [docs](https://help.aliyun.com/zh/ims/developer-reference/api-ice-2020-11-09-getsmarthandlejob)
- `CreateCustomTemplate` — `Name`, `Type` (**2 = snapshot**), `Subtype` (1 `Normal` / 2 `Sprite` / 3 `WebVtt`), `TemplateConfig` → `CustomTemplate.TemplateId`. [docs](https://help.aliyun.com/zh/ims/developer-reference/api-ice-2020-11-09-createcustomtemplate)
- `SubmitSnapshotJob` — `Name`, `Input` / `Output` (JSON strings, `{Type, Media}`), `TemplateConfig` (`{TemplateId, OverwriteParams}`), `ScheduleConfig.PipelineId`, `UserData` → `JobId`. `OverwriteParams` accepts the same fields as the template, so one template can be reused with per-call `Time`/`Count`/`Interval`. [docs](https://help.aliyun.com/zh/ims/developer-reference/api-ice-2020-11-09-submitsnapshotjob)
- `GetSnapshotJob` — `JobId` → job state. [docs](https://help.aliyun.com/zh/ims/developer-reference/api-ice-2020-11-09-getsnapshotjob)
- `GetSnapshotUrls` — `JobId`, `PageNumber`, `PageSize` (≤30, default 10), `OrderBy` (`Asc`/`Desc`), `Timeout` (≤129600) → `Total`, `SnapshotUrls[]`, `WebVTTUrl`. [docs](https://help.aliyun.com/zh/ims/developer-reference/api-ice-2020-11-09-getsnapshoturls)

Snapshot template parameters in full: [snapshot template parameter reference](https://help.aliyun.com/zh/ims/user-guide/template-parameter-description/).
