# 13 Intelligent Production (IProduction) — single-media algorithm jobs

`SubmitIProductionJob` / `QueryIProductionJob` run **one algorithm over one media file**. This is a different pipeline from `SubmitMediaProducingJob`: there is no `Timeline`, no `OutputMediaConfig`, no track model — just `FunctionName` + `Input` + `Output` (+ `JobParams`).

Use this when the user wants a *derived asset* from a single file (cover images, logo/subtitle erasure, caption SRT, beauty, H→V reframe, denoise, stem separation, beat/chorus/quality analysis). Use the timeline pipeline (`01`–`12`) whenever several clips must be assembled.

## 1 The 14 functions

| FunctionName | Does | Input | Output | JobParams |
|---|---|---|---|---|
| `Cover` | smart cover frames | video | **N images** png (or gif) | `Model` |
| `VideoClip` | video summary | video | summary video + `VideoSummaryList` ranges (Input/Output not specified in the official doc) | none |
| `VideoDelogo` | erase logo / TV bug | video | mp4 | `LogoModel`, `Boxes` |
| `VideoDetext` | erase burned-in subtitles | video | mp4 | `LimitRegion`, `Time` |
| `CaptionExtraction` | OCR burned-in subtitles | video | **SRT** | `fps`, `roi`, `lang`, `track` |
| `VideoGreenScreenMatting` | green-screen matting | video | mp4 (with `bgimage`) or webm w/ alpha | `bgimage` |
| `FaceBeauty` | face retouch | video | mp4 | `beauty_params` |
| `VideoH2V` | landscape → portrait reframe | video | mp4 | none |
| `MusicSegmentDetect` | chorus detection | audio | JSON | none |
| `AudioBeatDetection` | beat detection | audio | JSON | none |
| `AudioQualityAssessment` | audio quality scoring | audio | **no file** — result inline | none |
| `SpeechDenoise` | speech denoise | **WAV 16k/48k** | wav | none |
| `AudioMixing` | mix in a second track | audio | wav | `inputs` |
| `MusicDemix` | vocals / accompaniment split | audio (song) | **2 wav** | none |

Anything not in this list is rejected client-side by `video_editor.py` before the call is made.

## 2 Input / Output

Both are objects, both are sent as **JSON strings** in the query (same convention as `Timeline`); `scripts/video_editor.py` handles the encoding — never hand-build the call.

```json
Input  = {"Type": "OSS",   "Media": "oss://bucket/in.mp4"}
Input  = {"Type": "Media", "Media": "<mediaId>"}
Output = {"Type": "OSS",   "Media": "oss://bucket/out/{source}-{sequenceId}.png"}
Output = {"Type": "Media", "Media": "", "Biz": "IMS", "OutputUrl": "https://bucket.oss-cn-beijing.aliyuncs.com/out.mp4"}
```

- `Type: OSS` accepts `oss://bucket/object` **or** `http(s)://bucket.oss-<regionId>.aliyuncs.com/object`. The bucket must be in the **same region as the job**.
- **A wrong-region output bucket does not fail at submit here — it fails silently at the end.** Unlike `SubmitMediaProducingJob` (which rejects the mismatch with a 400 before anything runs), an IProduction job accepts it, runs to completion and reports **`Success`**; only the write fails. Measured (`Cover`, submitted in `cn-beijing`, bucket in `cn-shanghai`): every `OutputFiles` / `Result[].Url` entry came back as the literal string `oss fail to save the image in the given bucket`, the signed `OutputUrls` were built against the wrong host (`<bucket>.oss-cn-beijing.aliyuncs.com`), and **zero objects landed**. Never report an IProduction job as done on `Status: Success` alone — read `OutputFiles` and confirm the objects exist.
- `Type: Media` takes a media asset id; `Media: ""` + `Biz` (`IMS`/`VOD`) creates a new asset. `Biz` is only meaningful for a new asset — with an existing id it follows the source.
- Input and output types can be mixed freely. **Verified: `Media` input + `OSS` output works.**
- `--input-type` / `--output-type` are inferred from the value shape (`oss://`, `http(s)://`, or 32-hex media id); pass them explicitly only when the value is ambiguous or empty.

### Output placeholders

| Placeholder | Filled with |
|---|---|
| `{source}` | input file base name, **without extension** (verified) |
| `{timestamp}` | Unix timestamp |
| `{sequenceId}` | generation index, `00001`, `00002`, … |
| `{resultType}` | server-decided output kind (vocal / accompaniment) |

**Multi-output functions must carry a placeholder or the files overwrite each other.** `video_editor.py` hard-fails: `Cover` without `{sequenceId}`, `MusicDemix` without `{resultType}`.

An extension written into the template around the placeholder is **not** consumed: `demix_{resultType}.wav` produced `demix_vocals.wav.wav` and `demix_accompaniment.wav.wav`. Read the real names from `OutputFiles` instead of composing them.

> Cover's count is **not** fixed at the documented "3": a 79 s vertical video produced **5** PNGs (`00001`–`00005`). Never assume the number — read `OutputFiles`/`OutputUrls` from the query response.

## 3 JobParams per function

`JobParams` is a JSON **object serialized to a string**; `-p` takes either a JSON string or a path to a `.json` file.

- **Cover** — `Model`: `""` (default) → still PNG; `"gif"` → animated cover.
- **VideoDelogo** — `LogoModel`: `tv` and/or `internet`, comma-separated. `Boxes`: **string** holding normalized `[xmin, ymin, width, height]` from the top-left, max 2 boxes, e.g. `"[[0,0,0.3,0.3],[0.7,0,0.3,0.3]]"`.
- **VideoDetext** — `LimitRegion`: list of `[xmin, ymin, width, height]` normalized boxes, e.g. `[[0, 0.65, 1, 0.2]]`; **omitted ⇒ only the bottom 30 % is scanned**. `Time`: `[start, end]` in seconds; a 2-D list (`[[5,20],[25,43]]`) works **only with** `--model-id algo-video-detext-new` (better erasure, slower, pricier).
  Measure the band first — extract 2–3 frames and read the burned-in text's normalized y range. Vertical-drama subtitles frequently sit *above* the default scan band (measured y ≈ 0.68–0.74), which is exactly the case that erases nothing. Pass the measured band **with margin**. Keep the number: it is also the vertical anchor for any replacement subtitle (`03-subtitles-and-titles.md` §1).
- **CaptionExtraction** — `fps` int `[2,10]` default 5; `roi` `[[top,bottom],[left,right]]` normalized, default bottom ¼; `lang` `ch` | `en` | `ch_ml`, default `ch`; `track: "main"` keeps only the main subtitle track.
  Three measured behaviours: the default `roi` misses any band above y ≈ 0.75 — a band at 0.71–0.74 needed `"roi": [[0.65, 0.80], [0, 1]]`; OCR also reads **diegetic** on-screen text (an email UI and a phone UI produced garbage cues `Coy O`, `Space arm`), so intersect the cues with the ASR speech windows and drop any cue with no spoken counterpart; and it is unreliable on stylized subtitle fonts. Use it for **wording**, with ASR for timing (`17-snapshot-and-asr.md` §1.8) — do not promise "extract the existing text and re-typeset it" as a deliverable.
- **VideoGreenScreenMatting** — `bgimage`: URL of the background image to composite. Omit it to get a WEBM with an alpha channel.
- **FaceBeauty** — `beauty_params`: one comma-separated string, e.g. `"whiten=20,smooth=50,face_thin=50"`.

  | Key | Range / default | Key | Range / default |
  |---|---|---|---|
  | `skin_beauty_enable` | 0/1, def 1 | `chin_thin` | 0–100, def 0 |
  | `shape_beauty_enable` | 0/1, def 1 | `eye_size` | 0–100, def 0 |
  | `whiten` | 0–100, def 20 | `eye_corner1` | ±100, def 0 |
  | `smooth` | 0–100, def 20 | `eye_distance` | ±100, def 0 |
  | `detail` | 0–100, def 20 | `nose_thin` | ±100, def 0 |
  | `skin_model` | 0/1, def 1 | `nose_wing` | ±100, def 0 |
  | `cheek_thin` | 0–100, def 0 | `nose_length` | ±100, def 0 |
  | `face_cut` | 0–100, def 0 | `mouth_size` | ±100, def 0 |
  | `face_thin` | 0–100, def 0 | `mouth_position` | ±100, def 0 |
  | `face_length` | ±100, def 0 | `lip_thickness` | ±100, def 0 |
  | `chin_length` | ±100, def 0 | `hair_line` | ±100, def 0 |
  | `smile` | 0–100, def 0 | `detect_mode` | 0 video / 1 image, def 1 |
  | `detect_level` | 0–2, def 1 | `threshold` | 0–1, def 0.8 |
  | `detect_interval` | 1–65535, def 5 | `max_face_num` | 0–32, def 32 |
  | `min_face` | 10–1024, def 40 | | |

  Keep edits conservative (`whiten`/`smooth` ≤ 50) unless the user asks for a strong look — high `smooth` visibly destroys skin texture. `detect_mode=0` (video) tracks faces across frames and is more stable on moving subjects.
- **AudioMixing** — `inputs`: the track to mix in, **exactly one** supported, e.g. `{"file":"http://bucket.oss-cn-shanghai.aliyuncs.com/2.mp4"}`.
- **SpeechDenoise** — no params, but the **input must be WAV @ 16 kHz or 48 kHz**; output keeps the input's sample rate. Do not convert locally (`SKILL.md` Hard Rule 2), and no ICE job is a format converter — the WAV-outputting functions are not one either (`SpeechDenoise` gates on WAV in, `MusicDemix` returns stems, `AudioMixing` returns a mix). So **prefer the `ADenoise` Timeline effect** in a producing job, which denoises video or audio directly with no format gate (`02-multi-track-audio.md` §Audio Denoise). Use SpeechDenoise only when the WAV already exists (the user or upstream hands it over, uploaded to OSS); otherwise the job fails on input format.
- **VideoClip / VideoH2V / MusicSegmentDetect / AudioBeatDetection / AudioQualityAssessment / MusicDemix** — no params.

## 4 Submit & poll

```bash
# Cover images from a media asset into OSS (verified end-to-end in cn-beijing)
python scripts/video_editor.py iproduction \
  -f Cover -i <mediaId> \
  -O 'oss://my-bucket/iproduction/{source}-{sequenceId}.png' \
  -p '{"Model":""}' --name cover-job -r cn-beijing --wait

# Extract burned-in subtitles as SRT
python scripts/video_editor.py iproduction -f CaptionExtraction \
  -i oss://my-bucket/ep01.mp4 -O oss://my-bucket/srt/ep01.srt \
  -p '{"lang":"ch_ml","fps":5}' -r cn-shanghai --wait

# Poll / re-read a finished job
python scripts/video_editor.py iproduction-status -j <jobId> -r cn-beijing
```

- `-r/--region` is **required and has no default** — it must be the region the user confirmed *and* the region the buckets live in. Every function here is an AI feature, so it must also be `cn-shanghai` / `cn-beijing` / `cn-hangzhou`; anything else is refused locally before the API is called (the service itself only answers `InvalidParameter.FunctionNotSupported`). Ask the user for a region and a matching bucket — never substitute one (`SKILL.md` §2.1).
- Submitting prints a confirmation summary (function, input, output, params, region, cost warning, output-overwrite pre-check) unless `-y`. Overwrite pre-check is skipped when the output path contains placeholders.
- Status values: `Queuing` → `Analysing` → `Success` | **`Fail`**. It is `Fail`, *not* `Failed` — do not pattern-match the wrong token.
- `SubmitIProductionJob` has **no `ClientToken`** (unlike `SubmitMediaProducingJob`); retrying a submit creates a second billable job. `QueryIProductionJob` does accept one.
- Optional: `--template-id`, `--model-id`, `--pipeline-id` / `--priority` (1–10, lower = higher priority, default 6), `--user-data` (≤ 256 chars, returned verbatim).

## 5 Reading results

`QueryIProductionJob` returns `Status`, `OutputFiles`, `OutputMediaIds`, `OutputUrls` and `Result` (a JSON **string** — `iproduction-status` pretty-prints it).

- **`OutputUrls` are already presigned** (`x-oss-expires=3599`, `http://`). For OSS output you do **not** need a second `media-info` call to get a fetchable link — but they die after ~1 h, so re-sign with `aliyun ossutil presign` for anything longer-lived (see `23-production-pitfalls.md` §3).
- `Cover` → `[{"Score":9.665,"Time":"4640.0","Url":"cover/x-00001.png"}, …]`. `Score` is confidence; **`Time` is in milliseconds** (`"4640.0"` = 4.64 s) even though the timeline pipeline talks in seconds.
- `VideoClip` → `{"VideoSummaryList":[{"StartTime":"0.28","EndTime":"5.28"}]}`, seconds.
- `MusicSegmentDetect` → `[{"start":39.32,"end":63.85,"title":"Chorus"}, …]`, seconds.
- `AudioQualityAssessment` → array, **one entry per channel**, no output file. Key metrics:

  | Field | Meaning |
  |---|---|
  | `Tag` | `Valid` / `File too Short` (<2 s) / `Mute` / `Voice too Short`. **Anything but `Valid` ⇒ MOS, Discontinuity, Coloration, Noisiness are meaningless (reported as 0)** |
  | `MOS(0-5)` / `MOS` | overall speech quality + its band: `(4,5]` Excellent, `[3,4)` Good, `[2,3)` Fair, `[1,2)` Poor, `[0,1)` Bad (same bands for every `*(0-5)` metric) |
  | `Discontinuity(0-5)` | continuity; drops on capture stutter, double-talk suppression, packet loss |
  | `Coloration(0-5)` | clarity / intelligibility; drops on reverb, low bitrate, mumbling |
  | `Noisiness(0-5)` | noise severity (ambient, device noise floor, echo residue) |
  | `Loudness(0-5)`, `Loudness(-90dB-0dB)` | voice loudness; below −24 dB sounds too quiet, `-90.0` = no speech detected |
  | `Worst *(0-5)` | worst value seen during scoring — use these to find local defects a good average hides |
  | `Speech Ratio`, `Double Talk Ratio(%)`, `Bad Mute Ratio(%)`, `Saturated Ratio(%)` | %, diagnostic aids: high `Saturated Ratio` ⇒ clipping from too-high capture gain |
- `VideoDelogo`, `VideoDetext`, `CaptionExtraction`, `VideoGreenScreenMatting`, `FaceBeauty`, `VideoH2V`, `AudioBeatDetection`, `SpeechDenoise`, `AudioMixing`, `MusicDemix` → `Result` is `{}`; the payload *is* the output file.

## 6 Feeding results back into a timeline

IProduction output is ordinary media, so it chains straight into `SubmitMediaProducingJob`:

- `CaptionExtraction` → SRT → `SubtitleTracks` clip `{"Type":"Subtitle","FileURL":"<srt url>"}`, restyle via `Font`/`FontSize`/`FontColor` (`03-subtitles-and-titles.md`).
- `Cover` → PNG/GIF → cover image, or a `GlobalImage`/`Image` clip.
- `VideoDetext` / `VideoDelogo` / `FaceBeauty` / `VideoH2V` / `VideoGreenScreenMatting` → cleaned mp4 → source clip on `VideoTracks`. Erase text/logos **before** cutting, so the erasure model sees continuous footage.
- `VideoClip` / `MusicSegmentDetect` / `AudioBeatDetection` → time ranges → clip `In`/`Out` or beat-aligned cut points. Convert `Cover` times from ms first.
- `SpeechDenoise` / `MusicDemix` / `AudioMixing` → wav → `AudioTracks` (`02-multi-track-audio.md`).
  `MusicDemix` exists so a re-voiced track replaces **only the dialogue** while BGM and effects survive. **Ask the user first** — "keep BGM/SFX" versus "replace the whole track" changes the deliverable. The vocals stem is also the clean dialogue reference for a timbre check (`11-output-verification.md` §7): dialogue without music, never the mixed track.

Two-step jobs: submit IProduction, wait for `Success`, take `OutputUrls`/`OutputMediaIds`, then build the timeline. Verify the final render as usual (`11-output-verification.md`).

## 7 Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Only one cover file, or files overwritten | output path lacks `{sequenceId}` | placeholder is mandatory for `Cover` (client-side check) |
| `MusicDemix` output collides | no `{resultType}` | add it — the two stems share the path otherwise |
| Cover count ≠ 3 | the "default 3" is not a contract (5 observed) | read `OutputFiles`, don't hardcode |
| Cover timestamps look 1000× too big | `Result.Time` is **ms** | divide by 1000 before using as timeline seconds |
| Job never leaves `Queuing`, or the wrong status branch fires | code checked for `Failed` | the value is `Fail` |
| `InvalidParameter.JobNotFound` | wrong JobId, or querying in a different region than the submit | query the same region |
| Input rejected / not found | bucket in another region, or an unregistered bucket for `Type: Media` + `OutputUrl` | keep bucket, media asset and job in one region |
| `JobParams` ignored / rejected | params copied from the **MPS** docs | MPS uses `Logo`/`Text`; **ICE uses `LogoModel` + `Boxes` (VideoDelogo) and `LimitRegion` + `Time` (VideoDetext)** |
| `VideoDetext` erases nothing | subtitles sit outside the default bottom-30 % band | pass `LimitRegion` |
| Erasure reports `Success` but the text is still visible | `Success` only means a file was written | frame-check the clean output, inside the band, before building on it (`11-output-verification.md` §3) |
| Stem files named `*.wav.wav` | an extension in the `{resultType}` template is not consumed | read the real names from `OutputFiles` |
| Job seems stuck | these algorithms run in minutes, not the seconds snapshot/ASR take | measured on a 118 s source: `MusicDemix` ≈170 s, `VideoDetext` ≈200 s |
| Multiple `Time` ranges rejected | 2-D `Time` needs the new model | `--model-id algo-video-detext-new` |
| `SpeechDenoise` fails on an mp4/mp3 | input must be WAV 16k/48k, and local transcoding is barred | denoise with the `ADenoise` Timeline effect instead (§3, `SKILL.md` Hard Rule 2); `SpeechDenoise` only when a WAV already exists |
| Duplicate billed jobs after a retry | submit is **not** idempotent (no ClientToken) | query before resubmitting |
| Output URL 403 after a while | presigned URL expired (~1 h) | re-sign with `aliyun ossutil presign` |
