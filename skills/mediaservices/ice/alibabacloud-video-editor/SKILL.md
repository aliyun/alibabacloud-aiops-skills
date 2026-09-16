---
name: alibabacloud-video-editor
description: >
  Edit videos with Alibaba Cloud ICE using URL or OSS inputs and cloud-rendered outputs. Use for Timeline editing, normal-template creation and rendering, multi-clip composition, titles, subtitles, transitions, audio mixing, translation or localization, and single-media intelligent-production jobs such as smart covers, erasure, caption extraction, matting, beauty, reframing, and audio processing. Also inspect templates and verify output URLs. Content analysis such as labels, highlight candidates, speaker attribution, and transcripts must be supplied upstream. Never use local ffmpeg to generate, convert, or extract media; it is limited to streamed audio analysis.
---
# Video Editor Skill
Edit video in the cloud (Alibaba Cloud ICE) — no local ffmpeg. Three modes:
- **Timeline editing** (`SubmitMediaProducingJob`) — assemble several clips: you write a Timeline JSON, the script submits a producing job, polls it, and returns the output video URL.
- **Normal templates** (`AddTemplate`, `Type=Timeline`) — store a parameterized Timeline Config, inspect its `ClipsParam` contract, and repeatedly render it with replacement text/media → `references/22-normal-templates.md`.
- **Intelligent production** (`SubmitIProductionJob`) — run **one algorithm over one media file** (smart cover, logo/subtitle erasure, caption extraction, matting, beauty, H→V, audio denoise/mixing/demix/analysis). No Timeline involved → §7.1 and `references/13-intelligent-production.md`.

**This skill is the last link of the chain.** Content understanding — what happens where, who speaks, which moments matter — is produced upstream by other capabilities and handed to this skill as data (§2.4). Everything here turns that data plus the material into a rendered, verified video.
## Hard Rules
Six rules where deviation is not a taste call. Everything else in this document — every font size, colour, duration, preset and length ratio — is a *worked example* from a job that shipped, not a mandate. Read those for what is possible, then make your own call from the material and the user's ask.

1. **Nothing lands on the user's local storage.** Media is never downloaded — read it in place (`ffmpeg -i "<https URL>"` streams over HTTP; a snapshot job returns signed frame URLs). Intermediates live in OSS: an algorithm's output, a dub take, a proxy, a converted input — all of them are OSS objects an ICE job wrote, never files on the user's disk. The deliverable is handed over as a **playback URL** (§8), not a downloaded file; produce a local file only when the user explicitly asks for one. The few things a local tool must write to be read at all (a waveform PNG, a `silencedetect` transcript, frames you inspect, `edl.json`, `project.md`) go into one scratch dir outside the user's project — `${TMPDIR:-/tmp}/video-editor/<session>` — and are disposable; never create them in the user's workspace. A local file the user hands over is uploaded to OSS first (§4) and operated on there.
2. **All generation goes through ICE; ffmpeg only analyzes audio.** Cutting, concatenating, trimming, overlaying, transitions, subtitle burn-in, mixing, speed change, synthesized speech/dubbing, format conversion: an ICE job renders it (`SubmitMediaProducingJob` for a Timeline, `SubmitIProductionJob` for a single-media algorithm, a template render for a Normal Timeline). ffmpeg's whole remit is **reading the audio signal** — waveform (`showwavespic`), silence/speech tails (`silencedetect`), loudness (`volumedetect`), duration (`ffprobe`) — and it writes nothing but those analysis numbers (§1.4). It never generates or transforms **media**: no `concat`, no `-filter_complex` over a media file, no `-c copy`, no re-encode, no `atempo`, no transcode. Frames come from `SubmitSnapshotJob`, not from ffmpeg. The one exception is a chart, not media: `timeline_view.py` crops tiles out of a **cloud** snapshot sprite and stacks them over the waveform, because no ICE API returns either (§1.4). Not a Python media library either, and not a different cloud product. If no ICE job can express what the user needs, say so and stop — a locally rendered deliverable is a wrong answer, not a workaround.
3. **Confirm region first, then the output bucket before any render** (§2.1). Template Config generation and `AddTemplate` do not need a bucket; rendering one does. There is no default region, not even `cn-shanghai`.
4. **Confirm the plan in plain language before submitting anything** (§2.2). A producing job costs money and minutes; a paragraph of prose costs neither.
5. **Verify every deliverable before reporting it** (§9). `Success` means a file was written, nothing more. Never report an unverified output as verified.
6. **Compile every multi-clip Timeline; never write it directly.** Even when the user asks only for `timeline.json` and forbids cloud calls, first write `edl.json`, then execute `python "$SKILL_DIR/scripts/video_editor.py" compile --edl edl.json --output timeline.json` — `compile` is offline and makes no cloud call (§2.1, `18-edl-and-compile.md`). The generated file is the deliverable. Fix every blocking checklist violation; both `compile` and `submit` enforce the same checklist (§5).
**Division of labor**: `references/` = knowledge base you read on demand; `scripts/video_editor.py` = pure executor (submit / poll / fetch URL, plus `iproduction` / `iproduction-status`); `scripts/frame_qa.py` = model review of **cloud** material — the whole video (`--mode full`) or signed snapshot frames (`--frames`), never local sampling (§9). All editing logic lives in the Timeline you generate.
## 1. Setup

`$SKILL_DIR` below = the directory containing this SKILL.md. **Always invoke the scripts with an absolute path** (`python "$SKILL_DIR/scripts/video_editor.py" ...`); the working directory is usually the user's project, not the skill directory.

```bash
pip install -r "$SKILL_DIR/scripts/requirements.txt"
```

AK/SK (§1.1) and an OSS output bucket (§1.2) are required — without them, stop and guide the user. `DASHSCOPE_API_KEY` (§1.3) and ffmpeg (§1.4) are optional: when they are missing, verify by reading **cloud snapshot frames** with your own vision instead (§9), and never skip verification.

### 1.1 Alibaba Cloud credentials (required)

The script uses the Alibaba Cloud default credential chain: environment variables, then the `aliyun` CLI profile (`~/.aliyun/config.json`, the profile named by `current`, override with `ALIBABA_CLOUD_PROFILE`), then `~/.alibabacloud/credentials.ini`, then the ECS RAM role. The CLI-profile provider only exists in `alibabacloud-credentials>=1.0.2`, which is why `scripts/requirements.txt` floors it there — on an older release a perfectly good `aliyun configure` profile is skipped and the failure looks like missing credentials, not like a version problem.

Guide the user through whichever they prefer:

```bash
# Option A — aliyun CLI (writes a reusable profile; recommended). Install if `aliyun` is missing:
brew install aliyun-cli   # macOS; or fetch a binary and `tar xzf` it + `sudo mv aliyun /usr/local/bin/`
# Binaries: https://aliyuncli.alicdn.com/aliyun-cli-darwin-arm64-latest.tgz (macOS), https://aliyuncli.alicdn.com/aliyun-cli-linux-amd64-latest.tgz (swap amd64→arm64), https://aliyuncli.alicdn.com/aliyun-cli-windows-amd64-latest.zip (put aliyun.exe on PATH)
aliyun version            # verify the install — aliyun CLI >= 3.3.3 required (upgrade: brew upgrade aliyun-cli, or re-download the binary)
aliyun configure          # prompts for AccessKey ID / Secret / region
# RAM role assumption or STS token: pick the matching authentication mode in the prompts

# Option B — environment variables in ~/.zshenv (all zsh sessions, incl. IDE terminals)
echo 'export ALIBABA_CLOUD_ACCESS_KEY_ID=<id>' >> ~/.zshenv
echo 'export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<secret>' >> ~/.zshenv
```

Get the keys from the [AccessKey console](https://ram.console.aliyun.com/manage/ak). Verify that **the SDK** resolves them — `aliyun sts get-caller-identity` only proves the CLI can read its own config, not that the Python chain picked it up:

```bash
python3 -c "from alibabacloud_credentials.client import Client; print(Client().get_credential().provider_name)"
# cli_profile/static_ak → Option A live; env → Option B live; CredentialException → nothing configured
```

### 1.2 OSS output bucket (required)

For uploads and as the job output location:
```bash
export OSS_BUCKET=your_bucket_name
export OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
```
The bucket is chosen during the Step-0 confirmation (§2.1): run `aliyun ossutil ls`, show the user only the buckets in the region they confirmed, and let them pick. Never pick one silently. OSS reuses the same credential chain. The output bucket must be in the **same region** as the producing job.

Output buckets are normally private; §8 covers turning the finished object into a verified playback link.

### 1.3 Model Studio API key (optional, for verification)

`DASHSCOPE_API_KEY` lets `scripts/frame_qa.py` check the finished video with a multimodal model. It is a **separate credential from AK/SK** — AK/SK cannot call model inference. Create the key in the [Model Studio console](https://bailian.console.aliyun.com/) → **API-KEY**, then persist it with `echo 'export DASHSCOPE_API_KEY=sk-xxxxxxxx' >> ~/.zshenv` (every zsh session, incl. IDE terminals) and open a new shell. Use `~/.zshrc` instead if only interactive terminals need it; do not set it in both.

**If the user declines or has not set it**, verification still happens — read cloud snapshot frames with your own vision (§9). Mention the key once, then proceed; never report an unverified video as verified.

### 1.4 ffmpeg (optional — audio analysis only)

**Editing and composition need no ffmpeg** — that is the point of this skill. ffmpeg has exactly one job here: during the *understanding* and *verification* phases, turn the **audio signal** into text or a chart that a model can reason over. It never generates, transforms or extracts media (Hard Rule 2), it never downloads a media file (Hard Rule 1) — pass it an https URL and it streams what it needs — and the only files it writes are analysis artifacts in the scratch dir (Hard Rule 1).

Use it for the audio things no ICE API returns: an RMS waveform (`showwavespic`), silence/speech-tail detection (`silencedetect` — ASR gaps cover sentence boundaries but not ambient audio tails, `17-snapshot-and-asr.md` §1.5), loudness (`volumedetect`), and duration (`ffprobe`). Stacking a **cloud** filmstrip against that waveform on one axis is `timeline_view.py` — the tiles come from a snapshot job; ffmpeg draws the waveform and pastes the two rows into one PNG, which is a chart, not media (Hard Rule 2). Everything visual is a cloud job, not ffmpeg: frames, filmstrips and contact sheets come from `SubmitSnapshotJob` (`17-snapshot-and-asr.md` §2), and cut points come from upstream scene labels, `omni_segment.py`, or a filmstrip you read (§2.4).

Install on macOS: `brew install ffmpeg`. Without it: cloud snapshots still cover every frame you need (`17-snapshot-and-asr.md`), and you lose the waveform, the audio tail and the loudness numbers — verify via `--mode full` (§9) and state plainly which checks you could not run. Do not silently downgrade.

### 1.5 Observability — User-Agent

**UA template:** `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`

**Session ID rule:** Use the host's `AGENT_SESSION_ID` when available; otherwise generate one 32-char lowercase hex ID per process. Every Alibaba Cloud call in the same run must use that single session ID. Here `{skill-name}` is `alibabacloud-video-editor`, and `{skill-version}` comes from `references/manifest.json` — the script reads it at import time, before any cloud client is created. `scripts/video_editor.py` builds the value once and applies it to every client; new clients must also set `config.user_agent = USER_AGENT`.

---

## 2. Workflow

| Step | Action | Details |
|------|--------|---------|
| 0 | **Confirm region, then output bucket — before anything else** | → §2.1 |
| 1 | Classify the request | → §3 routing table |
| 2 | Read the matching reference doc(s) | → §3 |
| 3 | Collect material URLs | → §4 |
| 4 | **Read the material — one signal per open question** (below). Upstream results first (§2.4), then only the `asr` / `snapshot` / `pack_material.py` passes that answer something you still have to decide | → `17-snapshot-and-asr.md` §0, §2.4, `19-editor-brief.md` |
| 5 | Write an EDL (cut decisions), then `compile` it into a Timeline | → `18-edl-and-compile.md`; §5 checklist runs mechanically |
| 6 | **Propose the plan in plain language — wait for confirmation** | → §2.2 |
| 7 | Submit the job | → §7 |
| 8 | Poll, fetch signed URL | → §8 |
| 9 | **Verify, self-fix (≤3 rounds), then report** | → §9 |

**Single-media algorithm requests take a shortcut**: when the whole task is one algorithm on one file (smart cover, logo/subtitle erasure, caption extraction, matting, beauty, H→V, speech denoise, audio mixing/demix, beat/chorus/quality detection), skip steps 4–5 and go from §2.1 straight to §7.1 — there is no Timeline and the §5 checklist does not apply. Steps 0, 3, 6, 9 (region/bucket, material URLs, plan confirmation, verification) still do. If the algorithm output then has to be assembled with other material, run the algorithm job first and feed its output into the timeline pipeline (`13-intelligent-production.md` §6).

**Normal-template creation also takes a shortcut**: confirm the region, design and review the parameterized Config, then call `AddTemplate` after confirmation. No output bucket is needed until the template is rendered. Read `references/22-normal-templates.md`.

**Step 4 is per-signal, not all-or-nothing.** Name the question you still have to answer, then buy only the signal that answers it — `17-snapshot-and-asr.md` §0 is the index. A whole-file concatenation has no open question, so step 4 does not happen at all: go from step 3 to step 5. A subtitle at a user-given time and place has exactly one question and it is **visual** — sample a frame and look at it (`11-output-verification.md` §3); ASR would answer a question nobody asked. `asr` and `snapshot` are **billed jobs**: "returns in seconds" is not "free", and running the wrong one costs the same as running the right one.

### 2.1 Environment confirmation comes first

Never assume a region — not even `cn-shanghai`, and not even if an aliyun CLI profile or credential file already contains one. For a rendering task, confirm in this order:

1. **Ask which region** the user wants to submit in. List the valid ICE regions (`cn-shanghai`, `cn-beijing`, `cn-hangzhou`, `cn-shenzhen`, `cn-zhangjiakou`, `ap-southeast-1`) and point out the constraints: AI features need `cn-shanghai` / `cn-beijing` / `cn-hangzhou` — that is every `AI_*` clip and effect **and every `SubmitIProductionJob` function** (§7.1), all 14 of them; a MediaId input must be submitted in the asset's own region. If the task is still unknown, the user may defer — but then revisit this step before building any Timeline.
2. **Ask which output bucket**, filtered to the confirmed region: `aliyun ossutil ls` lists every bucket with its region — show the user only the ones in the chosen region and let them pick. The output bucket must be in the same region as the job. Skip this step for offline Config generation or `AddTemplate`; return to it before the first template render.
3. Only after both are confirmed, ask what video the user wants to make (§3 onward). If the task turns out to need a different region (e.g. AI features in a non-AI region, or a MediaId living elsewhere), go back to step 1 and re-confirm — with the user.

**A blocked region is a question, never a fallback.** When the region the user named cannot serve the request, say so and stop: name the constraint, list the regions that can serve it, and ask for a region plus a same-region bucket. Do not submit once to confirm what this document already states — `iproduction` refuses the call locally before any API request, and a 400 from the service costs a round trip to learn nothing. Do not pick the replacement yourself either: switching region, bucket or product on your own after a failure is a second decision the user never made, and it lands their output somewhere they did not ask for. "直接提交" / "just submit it" waives the **plan** confirmation (§2.2); it never waives this one.

**Multi-clip edits go through an EDL.** Whenever the job is "assemble N ranges of source material" (highlight, promo, episode stitch, montage), write `edl.json` — one entry per kept range with `source`/`in`/`out`/`beat`/`quote`/`reason` — and run `compile` (`18-edl-and-compile.md`). It emits the Timeline and runs the §5 checklist mechanically, so iteration means editing one number instead of regenerating the whole Timeline. Decoration does **not** buy an exemption: mute, background blur, filters and transitions are per-range `effects`, an ambient overlay is a top-level `EffectTracks`, BGM is an `audio` entry — all EDL fields (`18-edl-and-compile.md` §1). A back-to-back stitch that also mutes, blurs, adds transitions and lays a music bed is still a stitch, so it still compiles. Hand-write a Timeline only when there is no range list to begin with: single-clip jobs, avatar narration, slideshow templates.

When generating a Timeline directly, work through: what output type → which tracks → which clips per track → do clips need `In`/`Out`/`TimelineIn`/`TimelineOut` (plain back-to-back stitching does not) → which effects/transitions/volume → emit JSON.

**Ask before composing when the request is under-specified** in a way that changes the visual result — most importantly the background (a narration/avatar video with no background renders on black). Do not silently pick a look the user did not ask for.

### 2.2 Confirm the plan before submitting

Once the material is read and the EDL drafted, describe the plan in **4–8 sentences of plain language** and stop. Cover: the shape of the cut, which moments are kept and which are dropped, the estimated runtime and how that compares to the source, the look (transitions / grade / watermark — and say when there is none), subtitle and audio treatment, and the output spec. Then wait.

Ask the questions the *material* raises, not a fixed checklist — the right question is different every time. But two are almost always worth asking because guessing them wrong wastes a render: **target length** and **whether a watermark is wanted** (it is off by default — `compile` invents nothing the EDL did not ask for, `18-edl-and-compile.md` §2).

**What counts as confirming.** Prose in the reply the user can read. Not your internal task list or TODO items, not the compiled EDL, not the `submit` command with `--yes` — that flag silences the *script's* stdin prompt about output path and overwrite risk and has nothing to do with this step (§7). Going `compile` → `submit` in one motion means the user first hears about the cut when the bill arrives. **So do not write one task item that covers both** — "state the plan, then submit" is a single item that a single batch of tool calls can tick off without the plan ever existing. Make the plan its own step, finish it, send it, and only then reach for `submit`. If nobody can answer — a scripted or non-interactive run — the plan still gets written out before the command; a missing human removes the reply, not the step.

This step is worth more here than in a local editor. A producing job costs money and minutes, and a rejected deliverable costs the whole round trip: a real 79 s source cut to 66 s was rejected as "too long, not a highlight" and had to be redone at 30 s (`19-editor-brief.md` §4). One paragraph up front would have caught it.

On feedback, revise the **EDL** and recompile — never hand-patch the Timeline (`18-edl-and-compile.md` §5).

### 2.3 Session memory — `project.md`

For any project that will span more than one session, keep `project.md` next to the EDL in the scratch dir (Hard Rule 1) — never in the user's project tree — and append one `## Session N — YYYY-MM-DD` section per session covering: **Environment** (region, output bucket, MediaIds in play), **Strategy** (one paragraph), **Decisions** (cuts, lengths, look, and why — plus what the user rejected), **Artifacts** (JobIds, output object paths, analysis job ids worth reusing), **Outstanding** (deferred items). When the user wants the record kept, paste it into the chat or write it where they ask — that is their file, not an intermediate.

Two things make this pay for itself in this skill specifically. **§2.1 stops re-interrogating the user** — read the last session and open with "last time: `cn-beijing` / `my-bucket`, continue?" instead of asking again. And **analysis results stop being re-bought**: an ASR or snapshot job already run on an unchanged source should be looked up, not resubmitted. Record what was rejected too — a strategy the user already turned down is the most expensive thing to rediscover.

On startup, if `project.md` exists, summarize the last session in one sentence before proposing anything.

### 2.4 Upstream analysis results — what this skill consumes

The earlier stages of the chain belong to other capabilities. When they hand you data, treat it as authoritative and do not re-derive it:

| Upstream result | Where it plugs in |
|---|---|
| Cut candidates / highlight windows (`from`/`to` + why) | `ranges[]` of the EDL — `in`/`out` as given, the rationale into `reason` (`18-edl-and-compile.md` §1) |
| Transcript / dialogue timeline with timestamps | replaces or cross-checks step 4's `asr` pass |
| Subtitle file (SRT / WebVTT) | `subtitles[]` of the EDL, or `decompile --inline-srt` on an expanded Timeline (`21-timeline-export.md`) |
| Labels / tags / person appearances | decides **which** windows to keep; the frame-exact seam still comes from ASR punctuation + gaps (`17-snapshot-and-asr.md` §1.5) |
| Speaker attribution | which `VoiceId` carries which line, and glossary names (`17-snapshot-and-asr.md` §1.7) |
| Cloned `VoiceId` (already trained — this skill does not train voices) | `customizedVoice` on the `AI_TTS` clip (`07-smart-media-features.md`, `09-voice-and-avatar-catalog.md`) |

Two rules:

- **Upstream timestamps are candidate-level, not frame-exact.** Snap every window onto a real seam — punctuation + gap ≥ 0.3 s, a shot boundary from upstream labels / `omni_segment.py` / a snapshot filmstrip (§1.4), the `silencedetect` audio tail — before compiling. A coarse window copied verbatim amputates dialogue (`18-edl-and-compile.md` §1.5).
- **Missing analysis is a question, not a guess.** When the request needs content knowledge you do not have (which moments matter, who speaks), ask the user to run the upstream capability and hand over the result. Do not invent windows and do not silently fall back to a whole-video cut.

---

## 3. Requirement → Reference Routing

Find the rows matching the capabilities the request needs, read them, then build the Timeline.

The rows are **capabilities, not scenarios**. There is no "highlight reel" document and no "video translation" document: a scenario is a composition, and you compose it from the rows below — usually two or three of them plus `18-edl-and-compile.md`. If no single row matches the request, that is the normal case, not a failure.

| User asks for | Read | Key Types / fields |
|---|---|---|
| Anything (track & clip fundamentals, duration control, alignment) | `01-timeline-basics.md` | `VideoTracks`/`AudioTracks`/`SubtitleTracks`/`EffectTracks`, `In`/`Out`/`TimelineIn`/`TimelineOut`, `MainTrack`, `MaxDuration`, `ClipId`/`ReferenceClipId`, `FECanvas` |
| Voiceover, narration, BGM, mixing, mute, volume, loop audio, denoise, normalize loudness, extract audio | `02-multi-track-audio.md` | multiple `AudioTracks`, `Volume`(`Gain`), `AFade`, `LoopMode`, `ADenoise`, `ALoudNorm`, `AEqualize` |
| Titles, subtitles, end credits, scrolling text, styled/bubble text, subtitle background, subtitle animation, persistent corner title, text positioned over an erased burned-in band, **re-timing a whole track after a rewrite or translation** (line width & dwell recompute, glossary, dub cover) | `03-subtitles-and-titles.md` (§1 positions, §11 re-timing) | `Type: "Text"`/`"Subtitle"`, `Content`, `Alignment`+`X`/`Y`, `FontSize`, `SubtitleEffects`, `AaiMotion*`, `Scroll*`, `AdaptMode`, `subtitle_localize.py` |
| Transitions, filters, color grading, VFX, masks, Ken Burns, zoom, blurred/solid background, watermark/logo, picture-in-picture, split screen | `04-effects-and-transitions.md` | `Transition`/`DLTransition`, `Filter`, `VFX`, `Flip`, `KenBurns`, `Zoom`, `Background`, `GlobalImage`, `EffectTracks` |
| Photos into video, image carousel, slideshow, photo album, opening/ending title cards (a still held for N seconds) | `05-slideshow-template.md` | `Type: "Image"` + `Duration`, `Transition`, `KenBurns`, BGM |
| **Assembling N ranges into a cut** (highlight, promo, episode stitch, montage); recording *why* each cut was made; validating a Timeline before submitting | `18-edl-and-compile.md` | `compile` subcommand, `edl.json` (`sources`/`ranges`/`audio`/`subtitles`), BLOCK vs WARN checklist |
| Stitching multiple clips, multi-episode concatenation, cropping material, mixed material types (stills + video), landscape→portrait, sticker/GIF overlay, speed change, flip/rotate/crop/freeze, batch remix variants | `06-multi-clip-editing.md` | `In`/`Out`/`MaxOut`, `Speed`, `Flip`, `Rotate`, `Crop`, `FreezeFrame`, `Clip`+`RandomClip`, `AdaptMode` |
| Text-to-speech, speech recognition subtitles, karaoke highlighting, **dubbing / re-voicing a line into an existing shot**, fitting a rewritten line to its shot duration, reading-follow narration, digital avatar / newscast, green-screen or real-scene background removal, SSML | `07-smart-media-features.md` | `AI_TTS`, `AI_ASR`(+`AlignmentText`, `NeedHighlighting`), `AI_Avatar`, `AI_Matting`, `AI_RealMatting`, `Harmonization`, `SpeechRate`, `customizedVoice`, per-line micro-render |
| Output resolution/bitrate/codec/format, VOD or S3 output, cover image, completion callback | `08-output-and-job-config.md` | `OutputMediaConfig`, `EditingProduceConfig`, `MediaMetadata`, `UserData.NotifyAddress` |
| Picking a voice or an avatar image; using a supplied cloned `VoiceId` | `09-voice-and-avatar-catalog.md` (+ `07-smart-media-features.md` for the wiring) | `Voice` values (multi-emotion / CosyVoice / dialects / multi-language), `customizedVoice`, `AvatarId` values |
| User has no script for TTS/avatar narration | `10-narration-script-examples.md` | `Content` script styles (story commentary / live commerce) |
| Checking the finished video, frame sampling, quality complaints ("the output looks wrong"), **looking at one moment** (is this seam clean, did that line finish, what is the picture doing here), seam verification after a multi-range cut | `11-output-verification.md` (§6 seams, §7 re-voiced output) | `frame_qa.py` whole-video review, snapshot sampling (`--time` in ms, `--count 1` to pin one instant), frame-QA blind spots, `timeline_view.py` (filmstrip + waveform, shared axis; `--seams edl.json`) |
| **Reading a video before editing it**: dialogue timeline with timestamps, whole-video filmstrip / contact sheet, a frame at a given instant, time↔pixel map for aligning analyses, shot/dialogue segmentation as a second opinion | `17-snapshot-and-asr.md` (§1.6 ground truth — one audio pass, two cloud passes — + `omni_segment.py`, §1.7 attribution, §1.8 the transcript is a draft) | `asr` / `snapshot` subcommands; `EditingConfig.SentenceMaxLength`, `FrameType: normal`, `Sprite`/`WebVtt`, `--cover`, `--start-time`/`--duration` |
| **One readable view of all analyses**; deciding where a cut may sit | `17-snapshot-and-asr.md` §1.5 | `pack_material.py` → `material_packed.md` (gaps + punctuation + silence on one axis) |
| **Delegating range selection**; choosing the shape of a cut (highlight / stitch / demo / explainer / interview / montage) | `19-editor-brief.md` | sub-agent brief template, structural archetypes, length discipline |
| **One algorithm on one file**: smart cover, video summary, remove logo/TV bug/watermark, erase burned-in subtitles, extract subtitles to SRT, green-screen matting, face beauty, landscape→portrait reframe, chorus/beat detection, audio quality check, speech denoise, audio mixing, vocal/accompaniment split | `13-intelligent-production.md` | `iproduction` / `iproduction-status`, `FunctionName`, `Input`/`Output`, `JobParams`, output placeholders |
| Requests needing content knowledge this skill does not compute: video labels, action events, person appearances, keyword timelines, highlight candidates, speaker attribution | §2.4 — ask for the upstream result, never guess it | EDL `ranges[]` (`in`/`out`/`reason`), `subtitles[]` from an SRT, seam snapping via `17-snapshot-and-asr.md` §1.5 |
| **The timeline the engine actually computed** (after `AI_ASR`/`AI_TTS`/`AI_Avatar`/`VideoDetext` ran); fine-tuning a finished AI result; iterating on structure *after* AI ran without re-running it; handing a cut to Premiere | `21-timeline-export.md` | `export-timeline` / `export-timeline-status` / `decompile` (+`--inline-srt`), `ExportType`, `ProjectId` vs `Timeline`, srt subtitle track |
| Create, generate, inspect, or render a reusable normal template; TemplateId / ClipsParam; variable media slots; intros/outros or default watermark templates | `22-normal-templates.md` | `template_editor.py generate/create/get/expand/submit`, `AddTemplate`, scalar `$Param`, `ArrayItems` / `Array` |
| **Real-job field notes**: IMS bucket registration before submit, MediaId-only ASR input, STS vs long-term-AK signed-URL delivery, anti-truncation splice rules, no-motion look preset, fillable-template / ClipsParam engineering | `23-production-pitfalls.md` | `aliyun ice get-storage-list`, ASR input form, splice margins, ClipsParam slots |
| Permission errors, RAM setup | `ram-policies.md` | `ice:*`, `oss:*` actions |

AI features (`AI_*`) run only in some regions — submit in `cn-shanghai`, `cn-beijing` or `cn-hangzhou`.

---

## 4. Material URLs

- **Local file** → upload it via the oss-upload skill, then use the returned OSS URL.
- **Already a URL** → use it directly. A bare URL carries no metadata: when the EDL needs a numeric `out` (`18-edl-and-compile.md`), measure it with `ffprobe "<url>"` — it streams over HTTP and writes nothing (Hard Rules 1–2). If ffprobe is not installed, say so and ask; do not hand-roll an MP4/moov parser in its place, guessing the duration is worse still.
- **Copy every URL verbatim.** `MediaURL`/`FileURL` must be character-for-character identical to the user's input or earlier tool output. Never "normalize" an object key — retyping one `_` as `-`, changing letter case, or trimming a trailing digit yields `InvalidMaterial.NotFound: The specified clips url not found`.
- **MediaId instead of a URL** (32-char hex asset id) → run `media-info` (§8) first to confirm file name, type, region and **duration** (`GetMediaInfo` returns it in `FileInfoList[0].FileBasicInfo.Duration`, so no ffprobe pass is needed). Submit the job in the asset's own region (or an AI-capable region if the asset's region lacks the AI feature) and prefer an output bucket in that same region.

---

## 5. Pre-Submit Checklist

Every rule below comes from a real failed job. Scan this list before submitting — a violation fails the producing job (or silently produces a wrong result).

**Most of this list is now checked mechanically.** `compile` and `submit` both run it: rules with a recorded failure **block**, the rest **warn** (`18-edl-and-compile.md` §3). ICE has no server-side dry-run endpoint; the Timeline checker and normal-template `expand` command are local re-implementations, so they can miss a new engine rule. Read the list anyway for anything they cannot see (intent, material choice, §5-E parameter discipline).

### A. Correct clip Types and placement

| Rule | Correct | Wrong (fails) |
|---|---|---|
| AI features are prefixed `AI_` | `AI_ASR`, `AI_TTS`, `AI_Matting`, `AI_RealMatting`, `AI_Avatar` | bare `ASR` / `TTS` / `Matting` |
| `AI_Avatar` is a **clip Type** in `VideoTrackClips` | `{"Type":"AI_Avatar","AvatarId":...,"Voice":...,"Content":...}` | putting it in another clip's `Effects` → `InvalidTimelineFormat: ... MediaId is empty` |
| Matting is an **effect** in the clip's `Effects` | `{"Type":"AI_RealMatting"}` | a matting clip Type, or `SubType: "Matting"` |
| Green-screen matting parameter | `{"Type":"AI_Matting","Color":"green"}` | `ColorType` / `"GreenScreen"` |
| Real-scene (no green screen) matting | `AI_RealMatting` | `AI_Matting` (poor edges) |
| Mirror/flip is a dedicated effect | `{"Type":"Flip","Direction":"horizontal"}` | `VFX` with `hflip`/`vflip` → `InvalidTimelineFormat: Invalid vfx subType` |
| Subtitle text field | `Content` | `Text` |

**`AI_ASR` has two valid placements** — pick by intent:
- In a clip's `Effects` on `VideoTracks`/`AudioTracks`: `{"Type":"AI_ASR","AlignmentText":"...", <style fields>}` — subtitles are driven by *that clip's own* audio and rendered in the same job. **Preferred one-step pattern for narration / avatar videos**, and the only placement where `NeedHighlighting`/`HighlightingStyle` work.
- As a clip in `SubtitleTracks` with `MediaURL` pointing at the source video — plain recognition of an existing video's speech.

Always use built-in `AI_ASR` for speech→subtitles; never transcribe audio yourself or hand-time `Type: "Text"` clips against synthesized speech.

**One `AI_Avatar` clip per script.** Put the whole narration in a single clip's `Content` — splitting per sentence makes the avatar repeat its opening gesture on every sentence.

### B. Audio

- **Mute/volume uses `Gain`**: `{"Type":"Volume","Gain":0}` (0 = mute, 1 = original, >1 amplify, max 10, prefer ≤3). `{"Volume": 0}` inside a Volume effect fails the job.
- **`LoopMode` is for audio clips only**: use one `AudioTrackClips` clip with `LoopMode: true` + `In`/`Out` + `TimelineIn`/`TimelineOut`. To repeat video, use adjacent copies (or a template `ArrayItems` expansion) and trim the last copy to the target duration.
- **Audio clips on one track must not overlap** in time; use separate tracks to layer sounds.

### C. Visual and effects

- **One effect kind per EffectTrack**: each `EffectTracks` entry may hold only one effect type in its `EffectTrackItems`. Filter and VFX go in **separate** EffectTrack entries; mixing them fails the job. (Multiple items of the *same* type are fine.)
- **`GlobalImage` needs an explicit `Duration`** when the timeline contains no real video — otherwise it shows only on the first frame. With real video present it automatically spans the whole output.
- **Background must fill the screen when asked**: set `"Width": 1, "Height": 1` (canvas-relative) on the background clip. `AdaptMode` alone can leave it letterboxed.
- **Regular `Transition` shortens the output** by its `Duration` (clips overlap); use `DLTransition` to keep the total duration unchanged.

### D. Timeline structure

- **At least one video or audio clip**: `VideoTracks` and `AudioTracks` cannot both be empty — a subtitle-only timeline fails with `TimelineFormatError: Both video tracks and audio tracks are empty.` Subtitles render *on top of* something, so **a text-only deliverable cannot be built** and what to add is the user's call, not yours (§2.1). If they said nothing about a background, ask which they want. If they explicitly ruled out image, video and audio, say the request is impossible as stated and ask which constraint to relax. **Never generate or upload an asset to clear this check** — a black PNG or a silent WAV both override an explicit instruction and leave an object in the user's bucket nobody asked for.
- Higher-index video tracks render **on top of** lower-index ones.
- Omitting `TimelineIn`/`TimelineOut` concatenates clips back-to-back in array order.

### E. Parameter discipline

- **Only set parameters the user asked for.** Do not invent values for optional style/effect parameters — wrong defaults silently break the intended result:
  - `outer_alpha=1.0` on a mask makes the mask look like it did nothing; `blur_intensity=1.0` blurs the entire inside.
  - `Width`/`Height` on a matted-person overlay rescales the person, breaking "same person, different background".
  - Guessed `Gain` values quietly change the mix.

  Omit these fields so engine defaults apply, or copy a proven combination from the reference docs.
- **URLs verbatim** (§4).

---

## 6. Minimal Timeline Example

Worked examples — full, simplified and duration-controlled — are in `references/01-timeline-basics.md`. **Hand-writing a Timeline is allowed only for a single-clip Timeline or an exported one (§7.2).** With two or more clips: write an EDL, then `compile -e edl.json -O timeline.json` (§2 step 5, `18-edl-and-compile.md`). The EDL is usually a few lines and compile is one offline command; it is also the only thing that runs the §5 checklist mechanically — importing `validate_timeline` / `lint_timeline` in a script of your own does not run it.

---

## 7. Submit the Job

**Stop — is the §2.2 plan already in your reply?** If the last thing you sent the user was a command, not a paragraph describing the cut, do not run this. `compile` and `submit` in one batch of tool calls is the failure this section exists to prevent.

```bash
# Submit and wait for completion (--yes skips the script's stdin prompt, not §2.2)
python "$SKILL_DIR/scripts/video_editor.py" submit \
  --timeline timeline.json \
  --output-config output.json \
  --region <region confirmed in §2.1> \
  --wait --yes
```

`--region` is required and has no default. Drop `--wait` to submit without polling; `--client-token` makes a retry idempotent. Every flag: `video_editor.py submit --help`.

> **There are two different confirmations and `--yes` only covers one of them.** Without `--yes` the script asks `Do you want to proceed? [y/N]` on stdin and **aborts in a non-interactive shell**, so an agent essentially always passes it. That flag skips only the script's own prompt about output path, resolution, region and overwrite risk. It is *not* the §2.2 plan confirmation — no flag can be, because §2.2 happens in the conversation, before this command exists. Reach `submit` only with the plan already in your visible reply.

`OutputMediaConfig`:
```json
{
  "MediaURL": "https://{your-bucket}.oss-cn-shanghai.aliyuncs.com/{your-target-video-path}",
  "Width": 1080,
  "Height": 1920
}
```
If the user did not state a resolution, use 1080×1920 (portrait) or 1920×1080 (landscape). More fields (bitrate, codec, VOD/S3 output, callbacks): `08-output-and-job-config.md`.

Submitting returns a `JobId`.

### 7.0 Normal Timeline templates

For reusable editing structures, read `references/22-normal-templates.md`. Generate Config locally, show the user its fixed assets and replacement slots, then create the persistent template only after confirmation. Before rendering an unfamiliar one, `get` its `ClipsParam` and `expand` locally — never guess console-generated numeric slot IDs, and remember a slot named `VideoDuration` describes only the field it replaces (references/22 §Parameter Rules).

```bash
python "$SKILL_DIR/scripts/template_editor.py" generate --preset video-concat -o template_config.json
```

Now stop and put the Config in front of the user: its fixed assets, its replacement slots, and the `ClipsParam` contract those slots imply. `AddTemplate` creates a persistent cloud resource, so this is the confirmation the §7 note says `--yes` cannot supply.

```bash
python "$SKILL_DIR/scripts/template_editor.py" create --name "Video Concatenation Template" \
  --config template_config.json --region <confirmed region> --yes
```

Template rendering is a normal producing job, so the §2.2 confirmation, same-region output bucket, polling, §9 verification and ≤3 self-fix rounds all apply (`references/22-normal-templates.md` §Workflow).

### 7.1 Intelligent production jobs (single-media algorithms)

One algorithm, one input file, no Timeline. **Read `references/13-intelligent-production.md` before submitting** — the 14 function names, their `JobParams`, the required output placeholders and the result shapes are not guessable.

```bash
# Smart cover images from a media asset into OSS
python "$SKILL_DIR/scripts/video_editor.py" iproduction \
  --function Cover --input <mediaId-or-oss://bucket/object> \
  --output 'oss://<bucket>/covers/{source}-{sequenceId}.png' \
  --job-params '{"Model":""}' \
  --region <region confirmed in §2.1> --wait --yes

# Poll / re-read a job
python "$SKILL_DIR/scripts/video_editor.py" iproduction-status --job-id <job_id> --region <region>
```

- **`SubmitIProductionJob` has no ClientToken** — a blind retry bills a second job. Query before resubmitting.
- Input bucket, output bucket, media asset and job must all live in the **same region**.
- **All 14 functions are AI features**: `cn-shanghai` / `cn-beijing` / `cn-hangzhou` only. Any other region — `cn-shenzhen`, `cn-zhangjiakou`, `ap-southeast-1` — makes `iproduction` fail locally with a `ValidationError` before it reaches the API; the service itself would only answer `InvalidParameter.FunctionNotSupported`. That refusal is the end of the road for this request: go back to §2.1 and ask the user for a region and a same-region bucket, never substitute one.
- Verify the result (§9) exactly as for a timeline job — an erasure or beauty job reports `Success` whether or not it changed anything.

### 7.2 Project export — the AI-expanded Timeline

The Timeline you submit holds AI **declarations** (`AI_ASR`, `AI_TTS`, `AI_Avatar`, `VideoDetext`); the real addresses and timing only exist after the engine ran them. When the user wants the *computed* timeline, export it — `references/21-timeline-export.md` has the commands and flags.

```bash
python "$SKILL_DIR/scripts/video_editor.py" export-timeline \
  --project-id <ProjectId from GetMediaProducingJob> \
  --bucket <scratch bucket, same region> --prefix export/ep01 \
  --region <region confirmed in §2.1> --output timeline_expanded.json --wait --yes
```

**Pass the `ProjectId`, not a `Timeline`** — the ProjectId expands the render that already happened, while an unrendered Timeline makes the export **run and bill** its AI tasks. This one Timeline may be hand-edited (the exception to §11) because it has no EDL behind it, but `decompile`-ing it back into an EDL is better: same loop as everything else, offline, and it never re-runs the AI.

---

## 8. Poll and Report

```bash
# Query once (region = the region the job was submitted in)
python "$SKILL_DIR/scripts/video_editor.py" status --job-id <job_id> --region <region>

# Wait for completion
python "$SKILL_DIR/scripts/video_editor.py" status --job-id <job_id> --region <region> --wait
# Add --details to print the submitted ClipsParam and Timeline when diagnosing a template render.

# Resolve a MediaId to a signed (authenticated) URL and media details (region = the asset's region)
python "$SKILL_DIR/scripts/video_editor.py" media-info --media-id <media_id> --region <region>

# Verified V4 signed URL for private-bucket hand-off (supports AK and STS)
zsh "$SKILL_DIR/scripts/oss_sign_clean.sh" oss://<bucket>/<object> [ttl-seconds] [region-or-endpoint]
```

Status values: `Init`, `Queuing`, `Processing` = still running; `Success` = done; `Failed` = inspect the message for the cause.

On `Success`, `status` prints the job's `MediaId`, `MediaURL`, and duration. Run `media-info` with that `MediaId` to get a **signed URL** — output buckets are normally private, so the plain OSS URL is not viewable.

**Two URLs, two jobs.** The `media-info` URL is for *you*, right now: it expires in roughly an hour and some STS-signed ones cannot be fetched at all — fine for the §9 inspection you are about to do, not fine for anything the user has to open later. What you hand over comes from `oss_sign_clean.sh`: V4, carries the STS token, region-scoped, and curl-verified before it prints. A failed verification is not a deliverable (`23-production-pitfalls.md` §3). If the signer itself fails, say so plainly, pass the `media-info` URL labelled short-lived and unverified, and give the re-sign command — never let a raw URL go out wearing the verified one's clothes.

**That URL is the deliverable — but not yet the answer.** It reaches the user only after §9. `media-info` handing back a duration and a resolution is metadata, not verification: it cannot tell a muted BGM from a mixed one. Report it as a playback link with its expiry and the one-liner that re-signs it; never download the finished video to the user's machine (Hard Rule 1). Fetching a local copy happens only on an explicit user request.

---

## 9. Verify the Output

`Success` only means a file was written. Wrong material, black frames, clipped subtitles and silent audio all report `Success`. **Verify every deliverable before reporting it.** Full guidance: `references/11-output-verification.md`.

Pick the first path that works:

| Order | Path | Command | Requires |
|---|---|---|---|
| 1 | Cloud snapshot frames, **you** read them (**preferred**) | `video_editor.py snapshot --mode normal -i <output MediaId or oss:// object> -r <region> --time <ms> --count 12 --interval 5 -O "oss://<bucket>/qa/f-{Count}.jpg" --wait`, then `snapshot-urls` for signed links | AK/SK + output bucket |
| 2 | Whole video + model | `frame_qa.py --video "<signed URL>" --mode full` | `DASHSCOPE_API_KEY` |
| 3 | Cloud filmstrip over the whole output | `video_editor.py snapshot --mode webvtt --cover <duration>` → read the sprite tiles (§9 seam check below) | AK/SK + output bucket |

Frames first — cost stays flat regardless of duration (an 89 MB / 78 s video → ~500 KB of JPEG, ~3-5k tokens), while whole-video review tokenises every second. Short transitions need denser sampling than a 5 s interval: `--interval` is **seconds** and only spaces frames inside one job, while `--time` is **milliseconds**, so any instant gets its own job (`--time <ms> --count 1`) — a suspect seam at ±0.1 s and ±0.2 s is four one-frame jobs (`11-output-verification.md` §6). `frame_qa.py` reviews only **cloud** material (`--video <signed URL>`, or signed frame URLs via `--frames`) and never downloads anything (Hard Rules 1–2).

**No `DASHSCOPE_API_KEY`?** Do not skip verification and do not block on the key. Paths 1 and 3 need no key at all — inspect signed frame URLs with a URL-capable vision/browser tool. Do not pass an HTTP URL to a file reader that requires a local absolute path; if necessary, `curl` the frame into the scratch dir and inspect that file. You are very likely a multimodal model, so treat your own vision as the reviewer. Point the user at §1.3 once, then continue. Vision is the key-free path for *picture* questions only — an audio-led deliverable goes to the ffmpeg listening path below, not to frames. **Cannot read images yourself?** Then the key is not optional: hand the same signed frame URLs to a model (`frame_qa.py --frames "<url>" …`) and report its findings as a model review, not as your own. Only with neither vision nor a key, report the output as *unverified* and say why.

**The user waives verification ("别检查了" / "just send the URL")?** Honor it — it is their call, and path 1 costs a job and a minute they may not want to spend. But the waiver covers *running* the checks, not *reporting* them: hand over the URL labelled **unverified**, say plainly that `Success` only proves bytes were written, name what you skipped at their request (frames, audio tail, rendered duration against intent), and give the one command that would run it (`snapshot`, path 1 above) so a change of mind costs ten seconds. The reply must never read as a verified deliverable (Hard Rule 5).

**Escalate to `--mode full`** when the deliverable's value lies in audio or motion — TTS narration, `AI_Avatar` lip sync, BGM mixing, `KenBurns`/`Scroll*` animation. Frame sampling cannot hear audio or see sync and stutter. For narration-led output, compare the rendered duration with the intended narration duration; a shorter render truncates narration, while an unexplained longer render can leave a black/silent tail. Either mismatch is a failed deliverable even when the job says `Success`. A transition shorter than your sweep interval is not out of reach — aim one-frame jobs at it — but that costs a job per instant, so sweep first and pinpoint only what looks wrong.

**`--mode full` needs the key. An audio-led deliverable still has one key-free path: point ffmpeg at the signed output URL and read the signal, not the picture.** That is analysis, not the local mixing/rendering Hard Rule 2 bars — it streams, and the only files written are analysis artifacts in scratch (§1.4). `volumedetect` or `astats` over the output settles whether the mix bed is at the requested level, whether the source audio survived, and whether the tail goes silent early. With neither key nor ffmpeg, report the **audio as unverified** and name which one is missing — a frame sweep is not a substitute, since the frames look identical whether the BGM is at 20% or muted.

**Multi-range cuts** additionally need seam-focused verification (dialogue intact at every cut; if a watermark was requested, placed and uncut) — `11-output-verification.md` §6. Model QA rarely catches a chopped line. The tool for it is `timeline_view.py --seams edl.json`: one image per seam, both sides, filmstrip and audio waveform on a shared time axis. That pairing is what catches the dominant failure — **a line whose audio runs past the visual cut** — which a frame alone cannot show, since the frame at the cut is just a face.

**A plain whole-file stitch needs no source frames.** Material identity is already proven twice: the URL is copied verbatim (§4) and ICE fails loudly with `InvalidMaterial.NotFound` when it cannot resolve one. Snapshot the **output** at head, seam and tail, and compare the rendered duration against the sum of the source durations — that catches a dropped file, a swapped order and a black seam. Pixel-matching output frames against source snapshots buys a billed job per anchor to answer a question the Timeline already settled. Buy source frames only when the edit *transformed* the material — crop, matte, erasure, speed change — and you need to see what it started from.

**Non-video IProduction deliverables** (§7.1) do not fit `frame_qa.py`: read an extracted SRT and check timings and text against the source; read a detection JSON / `Result` and sanity-check ranges against the media duration; for audio outputs use `--mode full`, which listens. Video outputs (erasure, beauty, H→V, matting) go through the normal paths above — sample frames in the region that was supposed to change.

### 9.1 Self-fix loop — capped at 3 rounds

Verification is not a report you hand over, it is a loop you close first:

1. Verify. If everything passes, present the deliverable.
2. If something fails, fix the source of truth — the **EDL**, or the template Config/ClipsParam for a normal-template render — then recompile/expand, resubmit, and re-verify. Change the hypothesis, not just the parameter type.
3. **Stop after 3 rounds.** If issues remain, label the result **not delivered**, name the unresolved defects, and include the evidence; never turn an unexplained mismatch into “template behavior” or a completed result.

Re-verify **the thing that failed**, at higher resolution than the pass that caught it: a seam flagged at 1 fps gets 4–8 fps subtitle-band strips (`11-output-verification.md` §6), not another 1 fps sweep. Only claim a defect is fixed once the previously failing check passes.

Do not show the user a preview you have not verified. If you would not ship it, do not present it.

Then report: the Timeline that was actually submitted (summarize multi-stage pipelines; when the result depends on how a track was mounted — a subtitle track from an extracted SRT, a dubbed audio track, a watermark/effect layer — state the mount itself, e.g. `SubtitleTracks[].FileURL` → the SRT object, not just the JobId), the output info (bucket / object path / region / MediaId / duration / resolution / JobId), the signed viewing URL (note that it expires), **which verification path was used, its findings, and what it could not check**, and how many self-fix rounds it took.

---

## 10. Error → Fix

Look the message up in `references/25-error-index.md`: every row names the cause, the shortest fix and the section that explains it. Failures that report `Success` and still ruin the deliverable are §11 instead.

---

## 11. Anti-Patterns

`references/25-error-index.md` lists things that **fail loudly**. These are the ones that return `Success` and still produce a bad deliverable — or waste a round trip. Each was paid for once.

**Process**

- **Editing before the plan is confirmed.** A render costs money; a paragraph does not (§2.2). The usual shape is `compile` straight into `submit --yes` in the same turn, with the internal task list mistaken for a plan the user saw (§2.2 "What counts as confirming").
- **Reporting an output you have not looked at as though you had.** `Success` only means bytes were written (§9). The usual shape is `status` → `media-info` → "Output verified": a duration and a resolution are metadata, and on an audio deliverable they are silent about the mix (§8, §9). When the user waived the checks, say so and label the deliverable unverified — the waiver buys them the skip, not a clean bill of health (§9).
- **Looping on the same defect past 3 rounds.** Name it and hand it over (§9.1).
- **Hand-patching the Timeline after a verification failure.** It diverges from the decisions that produced it and the next round has nothing to reason from — fix the EDL (`18-edl-and-compile.md` §5). The single exception is an **exported** Timeline (§7.2): an AI expansion has no EDL behind it, so editing it directly is the only way to fine-tune the result.
- **Fine-tuning the timeline you submitted instead of the one that was computed.** Its `AI_*` entries are placeholders — the aligner's sentence boundaries and the real durations are not in it. Export first (§7.2).
- **Re-running analysis on an unchanged source.** ASR and snapshot outputs are immutable functions of immutable inputs; cache them (§2.3).
- **Downloading the media to look at it, or writing your working files into the user's project.** Stream it, snapshot it, and keep scratch in scratch (Hard Rule 1). Same for the finished video: the deliverable is the playback URL (§8), not a file on their disk.
- **Asking the user for region/bucket again when `project.md` already records them** (§2.3).
- **Probing a region to discover a constraint this document states, then moving the job yourself.** Three `InvalidParameter.FunctionNotSupported` calls in `cn-shenzhen` taught nothing §7.1 does not already say; switching to `cn-shanghai` and a different bucket afterwards decided two things the user did not ask for. Stop at the first refusal and ask (§2.1).

**Reading the material**

- **`FrameType: intra` on a snapshot job.** Silently delivers ⅓ of the frames and still reports `Success` (`17-snapshot-and-asr.md` §2.2).
- **Trusting an undocumented API field because it appeared in a response example.** `SubmitASRJob` accepts and ignores them without error (`17-snapshot-and-asr.md` §1.3).
- **Computing filmstrip tile coordinates from your request parameters.** The server rewrites them; read the VTT (`17-snapshot-and-asr.md` §2.3).
- **Inventing content knowledge the upstream owns.** Highlight candidates, labels and speaker attribution arrive as data (§2.4); a guessed window is a render billed on a coin flip. Ask for the upstream result, and use `SubmitASRJob` for the dialogue timeline.
- **`qwen-omni-turbo` for timestamps.** Quantized and hallucinated even on 40 s clips (`17-snapshot-and-asr.md` §1.6).

**Cutting**

- **Judging a sentence boundary by the silence gap alone.** Measured: 2 of 16 gap-qualified candidates sat mid-sentence. Require trailing punctuation *and* gap ≥ 0.3 s (`17-snapshot-and-asr.md` §1.5).
- **Cutting `Out` at the visual scene change.** Dialogue audio routinely bridges the cut; follow the audio tail (`18-edl-and-compile.md` §1.5).
- **Trimming inside a dialogue block to hit a target length.** Drop whole blocks instead (`18-edl-and-compile.md` §1.5).
- **A "highlight" that keeps most of the source.** 79 s → 66 s was rejected; 30 s passed. Default to 30–40 % (`19-editor-brief.md` §4).
- **Offering "as long as possible" as a length option.** Cap the top option at half the source.

**Composing**

- **A local ffmpeg render to save a round trip** — `concat` the pieces, `-filter_complex` the overlay, burn the subtitle in, `atempo` the dub. It writes a deliverable ICE never produced, so nothing downstream can reproduce or re-edit it, and it is barred outright (Hard Rule 2). Fix the EDL or the Timeline and re-submit; if no ICE job can express the edit, report that instead.
- **Inventing optional parameters the user never asked for.** Wrong defaults break the intended result silently — `outer_alpha=1.0` makes a mask look like a no-op; `Width`/`Height` on a matted person rescales them (§5-E).
- **`X`/`Y` on a Text clip.** Semantics are unreliable; use `Alignment` alone and check a frame (`03-subtitles-and-titles.md`).
- **A watermark nobody asked for.** Off by default (§2.2).
- **Transitions on a multi-range cut.** They blur frames and swallow line tails; hard cuts unless asked (`18-edl-and-compile.md` §1.5).
- **Splitting an `AI_Avatar` script across clips.** The avatar repeats its opening gesture every sentence (§5-A).
- **Hand-timing `Text` clips against synthesized speech.** Use `AI_ASR` with `AlignmentText` and let the engine align (§5-A).
- **`HighlightingStyle.FontColor` as RGB hex.** It is **BGR in byte order, no `#` prefix** — the opposite of the normal `FontColor`/`OutlineColour` fields (`#RRGGBB`) on the same clip. `"00FFFF"` renders **yellow**; `"FFFF00"` renders cyan; `"#FFFF00"` renders black (parse failure). Always verify the colour in a sampled frame (`07-smart-media-features.md`).
- **Reusing the source subtitle timings for a translated track.** Spanish/German run 10–30 % longer than English; the source cue durations are what makes translated text overflow the frame or flash by unread. Recompute wrap and dwell per language, and extend every cue to cover its dubbed audio (`03-subtitles-and-titles.md` §11).
- **Speeding up the dub as the first fix for an overlong line.** The ladder is **rewrite the translation → raise `SpeechRate` → `Speed` on the audio clip in an ICE re-render (cap ≈1.5)** — never a local `atempo` (Hard Rule 2). A 34-char line rewritten to 21 chars fit its 2 s shot at natural speed; the sped-up version was rejected as racing (`07-smart-media-features.md`). And never change the picture speed to fit the audio.
- **Trusting an ASR reading of a dub you have not length-checked.** Recognition hallucinates the *completed* sentence over a truncated take, and invents words in short windows — it will hide the very defect you are checking for. Measure the audio, then read it (`11-output-verification.md` §7).
- **Wiring a supplied `VoiceId` to the wrong speaker's lines, or trying to train one yourself.** Attribution is adjudicated by who is on screen moving their mouth, not by a timbre guess (`17-snapshot-and-asr.md` §1.7); and a cloned voice is an input the user hands over (§2.4), never a job this skill submits (`07-smart-media-features.md`).

## 12. File Map

| Path | Purpose |
|---|---|
| `scripts/requirements.txt` | Python dependencies |
| `related_apis.yaml` | Dependent Alibaba Cloud APIs |
| `references/manifest.json` | Skill name + version — the UA `skill-version/` source, read before the first cloud call (§1.5) |
| `scripts/video_editor.py` | Executor: `compile` (offline EDL → Timeline + checklist) / `submit` / `status` / `media-info` / `asr` / `asr-status` / `snapshot` / `snapshot-urls` / `iproduction` / `iproduction-status` / `export-timeline` / `export-timeline-status` / `decompile` (offline expanded Timeline → EDL) |
| `scripts/template_editor.py` | Normal-template executor: offline common Config presets and local `expand` / `AddTemplate` / `GetTemplate` / TemplateId + ClipsParam producing jobs |
| `scripts/frame_qa.py` | Model review of **cloud** material only: the whole video (`--video`, §9) or signed snapshot frame URLs (`--frames`) — it never samples locally (Hard Rules 1–2) |
| `scripts/pack_material.py` | Merge ASR + WebVTT + `silencedetect` into `material_packed.md` — one time axis, cut markers, cached |
| `scripts/timeline_view.py` | Filmstrip + audio waveform on a shared axis; `--seams edl.json` for per-seam verification |
| `scripts/omni_segment.py` | qwen3.5-omni-plus shot/dialogue segmentation — a second opinion on the ASR transcript (`17-snapshot-and-asr.md` §1.6) |
| `scripts/oss_sign_clean.sh` | Verified OSS V4 signed URL for private-bucket hand-off; supports AK and STS (§8) |
| `scripts/subtitle_localize.py` | Localization cue generator: wrap + dwell recompute + glossary assertions + SRT, enforces `sub_end` ⊇ measured dub (`03-subtitles-and-titles.md` §11) |
| `references/` | Capability knowledge base (§3 routing), `25-error-index.md`, `ram-policies.md` |
| `evals/scenarios/` | Evaluation scenarios |
