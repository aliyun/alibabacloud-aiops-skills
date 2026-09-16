# 25 Error → Fix index

Look up the error message the API, the CLI or a script returned. Every row names the cause and the shortest fix, with the section that explains it. Errors that fail *loudly* live here; failures that report `Success` and still ruin the deliverable are in SKILL.md §11 Anti-Patterns.

| Error message | Cause | Fix |
|---|---|---|
| `submit: error: the following arguments are required: ... --region/-r` | Region omitted — there is no default region by design | Pass the region the user confirmed in SKILL.md §2.1 |
| `N blocking checklist violation(s)` on `compile` or `submit` | A SKILL.md §5 rule with a recorded failed job | Each message cites the section; fix the EDL/Timeline (`18-edl-and-compile.md` §3) |
| `EDL.ranges[i].source '…' is not declared in sources` | Typo in a range's source key | Declare it in `sources` or fix the key |
| `EDL.ranges[i].out (…) exceeds source '…' duration (…)` | Range runs past the end of the material | Correct the range, or drop the source's `duration` if it was wrong |
| `InvalidMaterial.NotFound: The specified clips url not found` | A material URL was altered or is unreachable | Copy the URL verbatim (SKILL.md §4) |
| `TimelineFormatError: Both video tracks and audio tracks are empty.` | Subtitle-only timeline — a text-only deliverable is not buildable | Ask the user for a background image or BGM; never generate or upload one (SKILL.md §5-D) |
| `InvalidTimelineFormat: Invalid vfx subType` | `VFX` used for flip/mirror | Use `{"Type":"Flip","Direction":...}` (SKILL.md §5-A) |
| `InvalidTimelineFormat: ... MediaId is empty` | `AI_Avatar` placed inside `Effects` | Make it a clip in `VideoTrackClips` (SKILL.md §5-A) |
| `ProduceFailed` after using `{"Volume": 0}` | Wrong volume key | Use `{"Type":"Volume","Gain":0}` (SKILL.md §5-B) |
| Job fails when Filter + VFX share an EffectTrack | Multiple effect kinds in one EffectTrack | Split into separate `EffectTracks` entries (SKILL.md §5-C) |
| AI feature job fails in the chosen region | Feature unavailable there | Ask the user to pick `cn-shanghai` / `cn-beijing` / `cn-hangzhou` and a same-region bucket; never switch either one yourself (SKILL.md §2.1) |
| `400 InvalidParameter` on `submit` with a valid-looking Timeline | Output bucket in a different region than the job — checked *before* auth, so it reads like a plain parameter error | Use a same-region bucket (`08-output-and-job-config.md`) |
| IProduction job reports `Success` but `OutputFiles` read `oss fail to save the image in the given bucket` and nothing landed | Output bucket in a different region than the job — IProduction accepts it at submit and only fails on the write | Use a same-region bucket; always verify `OutputFiles` rather than trusting `Success` (`13-intelligent-production.md` §2) |
| `OutputMediaConfig.MediaURL must be a valid HTTP/HTTPS URL` | An `oss://` address was passed as the Timeline job's output | Use `https://<bucket>.oss-<region>.aliyuncs.com/<object>`; `oss://` is IProduction-only (`08-output-and-job-config.md`) |
| Highlighting has no effect | `AI_ASR` on `SubtitleTrackClips` | Move it to a `VideoTracks`/`AudioTracks` clip's `Effects` (SKILL.md §5-A) |
| Background shows black bars | Aspect-ratio mismatch | Set `"Width": 1, "Height": 1` (SKILL.md §5-C) |
| Advanced effect id (`OT0001-*` / `OV0001-*`) rejected | Paid advanced-effect package not enabled | Use a built-in `SubType` or ask the user to enable the package |
| `Invalid FunctionName '...'. Must be one of: Cover, ...` | Typo / an algorithm ICE does not offer | Pick from the 14 functions (`13-intelligent-production.md` §1) |
| `Cover writes several output files, so its OSS output path must contain the {sequenceId} placeholder` (same for `MusicDemix` / `{resultType}`) | Multi-output function with a fixed output path | Add the placeholder (`13-intelligent-production.md` §2) |
| `InvalidParameter.JobNotFound` on `iproduction-status` | Wrong JobId, or querying a region other than the one submitted in | Query the same region (`13-intelligent-production.md`) |
| IProduction job returns `Success` but output looks unchanged | `VideoDetext` only scans the bottom 30 % by default; `VideoDelogo` needs the right `LogoModel`/`Boxes` | Pass `LimitRegion` / `Boxes` (`13-intelligent-production.md` §3) |
| IProduction `JobParams` rejected or ignored | Parameters copied from the MPS docs | ICE names differ: `LogoModel`+`Boxes`, `LimitRegion`+`Time` (`13-intelligent-production.md` §7) |
| `SpeechDenoise` job fails | Input is not WAV @ 16/48 kHz | Denoise with the `ADenoise` Timeline effect instead — no local transcode (`13-intelligent-production.md` §3, SKILL.md Hard Rule 2) |
| Snapshot job returns `Success` but only ⅓ of the requested frames | `FrameType: intra` emits frames only where I-frames exist, ignoring `Count`/`Interval` | Always `FrameType: normal` (`17-snapshot-and-asr.md` §2.2) |
| `InvalidParameter.NotSupport: Vtt snapshot does not support "SpriteSnapshotConfig"` | `SpriteSnapshotConfig` sent to a `WebVtt` (`Subtype: 3`) template | Drop it — `WebVtt` layout is server-chosen (`17-snapshot-and-asr.md` §2.3) |
| Snapshot frames land at the wrong instants | `Time` treated as seconds | `Time` is **ms**, `Interval` is **s** (`17-snapshot-and-asr.md` §2.5) |
| Cropped filmstrip tiles do not match the video | Tile coordinates computed from request params, or a VTT's coordinates applied to a `Sprite` image | Read `xywh` from that job's own VTT (`17-snapshot-and-asr.md` §2.3) |
| An `EditingConfig` field on `SubmitASRJob` has no effect and no error | Undocumented fields are silently ignored | Only `SentenceMaxLength`, `EnableSemanticSentenceDetection`, `HotwordLibraryIdList` exist (`17-snapshot-and-asr.md` §1.3) |
| `Pass exactly one of --project-id / --timeline` on `export-timeline` | Both or neither given | The API is strictly one-of (`21-timeline-export.md` §3) |
| Export job `Success` but `ExportResult.Timeline` is empty | `ExportType=AdobePremierePro` returns `ProjectUrl`, not a Timeline | Use `ExportType=BaseTimeline` (`21-timeline-export.md` §1) |
| Exported subtitle track shows no text | ASR sentences are inside the srt file, not on the clip | Read the clip's `FileUrl`; `ExportResult.SrtList` is empty in practice (`21-timeline-export.md` §2.1) |
| 403 fetching the exported srt | `FileUrl` is an unsigned OSS URL on a private bucket | Sign it: `oss_sign_clean.sh oss://<bucket>/<object>` (`21-timeline-export.md` §2.1) |
| Resubmitting an exported Timeline fails with `InvalidMaterial.NotFound` | The signed `MediaURL`s embedded in it expired | Re-sign them before submitting (`21-timeline-export.md` §4) |
| `'EditingConfig.SentenceMaxLength' is invalid, input: N, value range: 4-50` | ASR sentence length outside the allowed range | Pass 4–50 (`17-snapshot-and-asr.md` §1.4) |
| `InvalidParameter: [cosyvoice:]Engine return error code: 418` / `url error` when synthesizing with a cloned voice | Supplied `VoiceId` used on a DashScope REST endpoint | Cloned voices are ICE-only — synthesize via `AI_TTS`+`customizedVoice` (`09-voice-and-avatar-catalog.md`) |
| Dub lands seconds late, or `AI_TTS` clips ignore their spacing | 1–5 s variable leading silence; `AI_TTS` without `TimelineOut` falls back to sequential placement | Micro-render per line, trim, place measured `Audio` clips (`07-smart-media-features.md`) |
| Dubbed line loses its tail although the clip window looks right | `TimelineOut` truncates, it does not compress | Fit the audio first (rewrite → `SpeechRate` → `Speed` on the clip) (`07-smart-media-features.md`) |
| Validation Error: `MediaURL must be a valid HTTP/HTTPS URL` | `oss://` address in a timeline clip | Sign it — `oss_sign_clean.sh` (SKILL.md §5, `23-production-pitfalls.md` §3) |
| Permission / AccessDenied | Missing RAM actions | `ram-policies.md` |
| `ffmpeg not found on PATH` | ffmpeg missing — it is audio-analysis only now (SKILL.md §1.4) | Frames never needed it: read cloud `snapshot` frames, or `frame_qa.py --mode full` (SKILL.md §9). `brew install ffmpeg` restores the waveform / `silencedetect` / loudness passes and `timeline_view.py`'s chart |
| `timeline_view.py`: `the VTT URL is signed, so the tile URL cannot be derived` | The tile needs its own signature | Pass `--tile` with `SnapshotUrls[0]` from `snapshot-urls` |
| `timeline_view.py`: `no #xywh cues found` | The file is not a snapshot WebVTT | Use `snapshot --mode webvtt`; `sprite` mode emits no `.vtt` |
| `timeline_view.py`: waveform row missing | The audio URL expired, or the input has no audio stream | Re-sign the source URL; check with `ffprobe` |
| `pack_material.py`: every seam shows `CUT?` | The `silencedetect` threshold is too strict for this material | Raise it — `-25dB` finds almost no silence under continuous music or rain; try `-18dB` or `-12dB` (`17-snapshot-and-asr.md` §1.6) |
| HTTP 403 fetching a media or frame URL | Plain OSS URL on a private bucket — nothing is downloaded locally any more (SKILL.md Hard Rule 1) | Sign it: `media-info` for the output, `snapshot-urls` for frames (SKILL.md §8) |
| `frame_qa.py`: `DASHSCOPE_API_KEY was rejected` | Wrong/expired key, or AK/SK used by mistake | Create a Model Studio API key (SKILL.md §1.3) — AK/SK cannot call model inference |
| `frame_qa.py`: `too large to inline` | `--mode full` on a big local file | Upload to OSS and pass the signed URL, or read cloud `snapshot` frames (SKILL.md §9) |
| `frame_qa.py`: `Local frame sampling is gone` | `--mode frames` was removed — it downloaded the video and ran ffmpeg on it (Hard Rules 1–2) | Cloud frames: `snapshot --mode normal --time <ms> …` → `snapshot-urls`, then read them yourself or pass them to `frame_qa.py --frames <url> …` (SKILL.md §9) |
| `frame_qa.py`: `--frames takes signed https URLs` | Local frame files passed in | `snapshot-urls` output only — nothing is downloaded (Hard Rules 1–2) |
| `frame_qa.py --mode full`: HTTP 400 `video too long` | Output is over ~60 s of vertical video | `volumedetect` / `silencedetect` on the signed URL (`11-output-verification.md` §4) |
| Literal `{timestamp}` in the output object name | `OutputMediaConfig.MediaURL` is a path, not a template | Fixed filename; iterate by overwriting it (`08-output-and-job-config.md`) |
| `InvalidEffectParam` on a `Zoom` effect | `EndRate` is not greater than `StartRate` | Zoom in only — a rush is 1.0→1.3 fast (`04-effects-and-transitions.md`) |
| Filmstrip tiles unreadable | `snapshot --mode sprite` without `--width`/`--height` → ~15 px cells | Pass both (`17-snapshot-and-asr.md` §2.3) |
| Stem files named `*.wav.wav` | An extension written around `{resultType}` is not consumed | Read the real names from `OutputFiles` (`13-intelligent-production.md` §2) |
| Erasure `Success` but the text is still visible | `Success` only means a file was written, or the band sits above the default bottom-30 % scan | Frame-check inside the band; pass `LimitRegion` (`13-intelligent-production.md` §3) |
| New subtitles glued to the canvas edge, or off from the original band | `BottomCenter` default | `TopCenter` + `Y` = top of the measured band (`03-subtitles-and-titles.md` §1) |
| Re-timed text overflows the frame, flashes by, or vanishes mid-line | Source cue timings reused; dwell from reading speed only | Recompute wrap + dwell, and make `sub_end` cover the audio (`03-subtitles-and-titles.md` §11) |
| A line is voiced by the wrong speaker | `VoiceId` ↔ speaker mapping guessed from timbre | Adjudicate with the on-screen subject (`17-snapshot-and-asr.md` §1.7) |
| Only the first word of a synthesized line is audible | A long mid-sentence pause read as the speech end | Take the **last** long-silence start before EOF (`07-smart-media-features.md`) |
| Every take measures the same suspicious length | `silencedetect` threshold too strict — −35 dB latches onto the codec noise floor | −30 / −25 / −20 dB (`07-smart-media-features.md`) |
