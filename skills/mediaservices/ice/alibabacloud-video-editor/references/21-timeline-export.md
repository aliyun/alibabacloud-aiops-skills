# 21 Exporting the AI-expanded Timeline (SubmitProjectExportJob)

Use this when the user needs **the timeline the engine actually computed**, not the one that was submitted. A submitted Timeline holds AI *declarations* — `AI_ASR`, `AI_TTS`, `AI_Avatar`, `VideoDetext` — that are placeholders: the real media addresses, the real durations and the real per-sentence timing only exist after the workflow ran. `SubmitProjectExportJob` with `ExportType=BaseTimeline` replays that expansion and hands back the resolved Timeline.

The canonical trigger: a job whose timeline the engine rewrote (`AI_ASR` alignment, `AI_TTS`, `VideoDetext` erasure) finished, and the user now wants to nudge the subtitle timing, restyle a line or trim a clip. Fine-tuning the *submitted* timeline is fine-tuning a placeholder — the sentence boundaries the aligner chose are not in it.

## 1 When to export, and when not to

| Situation | Do this |
|---|---|
| "Give me the real / final / computed timeline"; "I want to adjust the result" | Export (`ExportType=BaseTimeline`) |
| The user wants the ASR sentence text with timings | Export, then read the **srt file** (§2) — or use `asr` (`17-snapshot-and-asr.md`) when no render exists yet |
| The user wants to hand the cut to an editor in Premiere | Export with `ExportType=AdobePremierePro`, deliver `ProjectUrl` |
| You are assembling N ranges and iterating on the cut | **Do not export** — iterate on the EDL (`18-edl-and-compile.md`). Export is for reading a finished result, not for authoring |
| Nothing AI ran (plain concat, filters, transitions only) | Export adds nothing the submitted Timeline does not already say |

Export is billable: if the source still declares an unfinished AI task, the export **runs it** (sub-job mode) before converting. Exporting a Timeline you never rendered therefore costs an ASR / TTS / detext run.

## 2 What the expansion actually does

Only four task types are expanded — `AI_TTS`, `AI_ASR`, `AI_Avatar`, `VideoDetext` (plus URL pull-in for remote materials). Everything else (transitions, filters, VFX, text clips you wrote yourself) is mapped through unchanged.

| Declaration in the submitted Timeline | Shape in the exported Timeline |
|---|---|
| `AI_TTS` clip | An ordinary audio clip: `MediaURL` → the synthesized audio, `Type` dropped, `VirginDuration` filled in |
| `AI_Avatar` clip | An ordinary video clip: `MediaId` removed, `MediaURL` → the rendered take (`MaskVideoUrl` added when the take is not webm) |
| `VideoDetext` (erasure) | Same clip, `MediaURL` → the erased video |
| `AI_ASR` effect on a video/audio clip | **Moved out** of that clip's `Effects` into a separate subtitle track (§2.1) |
| Remote-URL material | `MediaURL` → the transferred copy, original kept in `OriginalMediaURL` |

Every clip also comes back with resolved geometry and timing: `TimelineIn`/`TimelineOut`, `In`/`Out`, `Speed`, `Duration`, `VirginDuration`, `X`/`Y`/`Width`/`Height`.

Measured on a verified run (cn-beijing, one 12 s video clip carrying `AI_ASR`, `ExportType=BaseTimeline`):

- `Init` → `Success` in **~10 s**. A short ASR does not make the export slow; a long one will, since the export blocks on it.
- The video clip kept its `MediaId` **and** gained the resolved `MediaURL`, `VirginDuration: 89.584` (the whole source, not the 12 s slice), `Title`, `Speed`, `X`/`Y`/`Width`/`Height`.
- The ASR effect vanished from the clip's `Effects` and became a `SubtitleTracks[0]` clip spanning `0.0–11.38 s` — the **last cue's end**, not the clip length.
- Style survived, but **`Alignment: "TopCenter"` came back as the numeric code `"8"`**, and `BorderStyle`, `FontColorOpacity`, `FontFace`, `X: 0.0`, `Visible: true` were filled in with defaults. Treat the exported style block as engine output: do not assume a value round-trips unchanged, and frame-check after any re-render.
- `ProjectId` is **`null`** when the source was an inline `Timeline` — the export does not create a project. Only a `ProjectId` source echoes one back.

### 2.1 ASR subtitles arrive as an srt file, not as text clips

This is the one shape that surprises people. With `ExportType=BaseTimeline` the recognized sentences of one clip are merged into **a single srt file** uploaded to the scratch bucket, and the subtitle track holds one clip pointing at it:

```json
{"Type": "Subtitle", "SubType": "srt", "FileUrl": "<srt address>"}
```

- The per-sentence text and timing live **inside the srt file** — the clip has no `Content` at all. Fetch the srt to read or edit the wording.
- **`FileUrl` is the only copy of that address.** `ExportResult.SrtList` is documented but came back **empty** on a verified run — do not rely on it; read `FileUrl` off the subtitle clip (`export-timeline` prints them in full).
- **`FileUrl` is an unsigned `http://` OSS URL** and output buckets are private, so fetching it directly returns 403. Sign it first: `zsh scripts/oss_sign_clean.sh oss://<bucket>/<object>`.
- The source clip no longer declares ASR: the `Type: "Text"`, `FromAiAsr: true` effect is stripped from its `Effects`, and its styling is carried over onto the subtitle track.
- Subtitle tracks the user wrote by hand are untouched; the ASR track is **appended** as an extra track.
- "One `Text` clip per sentence with visible `Content`" is a different export type's behaviour (Jianying / PR), not `BaseTimeline`.

## 3 Run it

```bash
# Expand the project a producing job created (the usual case)
python "$SKILL_DIR/scripts/video_editor.py" export-timeline \
  --project-id <ProjectId from GetMediaProducingJob> \
  --bucket <scratch bucket in the same region> --prefix export/ep01 \
  --region <region confirmed in §2.1> \
  --output timeline_expanded.json --wait --yes

# Expand a Timeline that was never rendered (runs — and bills — its AI tasks)
python "$SKILL_DIR/scripts/video_editor.py" export-timeline \
  --timeline timeline.json \
  --bucket <bucket> --region <region> \
  --output timeline_expanded.json --wait --yes

# Re-read a job / pick up one that outlived --max-wait
python "$SKILL_DIR/scripts/video_editor.py" export-timeline-status \
  --job-id <job_id> --region <region> --output timeline_expanded.json --wait
```

| Parameter | Description | Required |
|---|---|---|
| `--project-id, -P` / `--timeline, -t` | Source to expand — **exactly one**; the API takes `ProjectId` or `Timeline`, never both | Yes (one) |
| `--bucket, -b` | Bare bucket name for the intermediate files (TTS audio, avatar takes, srt). Same region as the job | Yes |
| `--prefix` | Object path prefix inside the bucket (default: bucket root) | No |
| `--region, -r` | Region ID — **required, no default**; the region the project / media lives in | Yes |
| `--export-type` | `BaseTimeline` (default) or `AdobePremierePro` | No |
| `--output, -O` | Write the expanded Timeline to this JSON file | No |
| `--width` / `--height` | Target resolution; estimated from the source when omitted | No |
| `--wait, -w` | Poll until it finishes — **the Timeline only exists on a finished job** | No |
| `--poll-interval` / `--max-wait` | Default 10 s / 1800 s; the long ceiling is there because the export waits on unfinished AI tasks | No |
| `--yes, -y` | Skip the script's own stdin prompt (non-interactive runs). Not the SKILL.md §2.2 plan confirmation | No |

`ProjectId` is not something you invent: `GetMediaProducingJob` reports the id it auto-created for a submitted job, and that id is what expands into the timeline of exactly that render.

The command prints a per-track, per-clip summary (real spans, resolved sources, srt tracks) and warns if any `AI_*` / `VideoDetext` declaration survived the expansion — which would mean the result is still a placeholder.

## 4 Using the exported timeline

The exported Timeline is a **read** of a finished render. Two legitimate follow-ups:

1. **Report / inspect** — answer "when does line 12 actually appear", "how long is the avatar take", "what did the aligner hear".
2. **Fine-tune and re-render** — hand-edit the expanded Timeline (shift a subtitle, retime a clip, change a style) and `submit` it as a new job. This is the one place where hand-editing a Timeline is correct: there is no EDL behind an AI expansion, and recompiling from the EDL would only regenerate the placeholder again.

When re-submitting an expanded Timeline:

- Its `MediaURL` values are **signed OSS URLs that expire** (~1 h). Re-sign them (`media-info`, or `oss_sign_clean.sh`) before submitting, or the job fails with `InvalidMaterial.NotFound`.
- Editing a `SubType: "srt"` subtitle clip means editing the srt file: download it (signed), change the cue, upload it, point `FileUrl` at the new object. Changing the clip's `Content` does nothing. The unsigned `FileUrl` itself resubmits fine — verified (§5.1) — so only *your* reads need signing. Inlining the cues (§5.1) avoids the whole round trip.
- Do not re-add the `AI_ASR` effect to the video clip; the subtitle track already carries the result. Re-adding it re-runs (and re-bills) recognition and double-stacks subtitles.
- Re-verify the re-rendered output (§9 of SKILL.md) — an expanded timeline is no safer than a hand-written one.

## 5 Back to an EDL — `decompile`

Editing the exported Timeline by hand is legal but it is a dead end: the next
structural change has no decision layer to reason from. `decompile` turns the
expanded Timeline into a **fresh EDL**, which puts you back in the sanctioned
loop (`18-edl-and-compile.md`) — and because its sources are now the *expanded
artefacts*, recompiling never re-runs the AI.

Treat it as a new task: the old EDL described a cut of the original material, this
one describes a cut of the AI output. Old rationales do not carry over, which is
why every range comes back without `reason` and the checklist says so.

```bash
# Expanded Timeline → EDL, subtitles inlined as per-cue Text clips
python "$SKILL_DIR/scripts/video_editor.py" decompile \
  -t timeline_expanded.json -O edl_v2.json \
  --inline-srt --style-from timeline_submitted.json

# Then the normal loop, with no AI left to re-run
python "$SKILL_DIR/scripts/video_editor.py" compile -e edl_v2.json -O timeline_v2.json -r <region>
```

`decompile` is **offline and free** like `compile` — no region, no credentials —
except that `--inline-srt` has to sign and fetch the srt. Pass `--srt <file>` to
inline an already-downloaded one and stay fully offline.

| Parameter | Description |
|---|---|
| `--timeline, -t` | The expanded Timeline from `export-timeline` |
| `--output, -O` | Where to write the EDL (default: stdout) |
| `--inline-srt` | Expand the srt track into per-cue `Text` clips (§5.1) |
| `--srt` | Local srt to inline instead of fetching — keeps the run offline |
| `--style-from` | Timeline whose `AI_ASR` effect supplies the cue style — **normally the one you submitted** (§5.1) |
| `--strict` / `--quiet, -q` | Warnings become blocking / print only the EDL |

Every run also **recompiles the EDL and lints the result**, so a decompile that
would not survive `compile` fails immediately instead of at submit time.

### 5.1 Inlining the srt — why, and where the style comes from

Without `--inline-srt` the srt track passes through as a `FileUrl` reference, and
the EDL keeps depending on that file: the cues stay bound to the current time base,
so any structural edit silently desynchronizes them.

With `--inline-srt` each cue becomes a `Text` clip carrying its own `Content`,
`TimelineIn`/`TimelineOut` and style. The EDL is then self-contained: shifting a
subtitle is one number, fixing a mis-heard word is one string, and dropping a
range can drop its cues with it.

This does **not** violate §5-A's ban on hand-timed subtitles: the text and the
timings are the engine's own alignment output, copied verbatim. The rule that stays
in force is the source of the numbers — engine output only, never your estimate
of where a line falls.

**Take the style from the Timeline you submitted, not from the export.** The
export normalizes it: a submitted `Alignment: "TopCenter"` comes back as the
numeric code `"8"`, which ICE's own docs do not list as an input value. With
`--style-from` the round-trip is exact (verified). Without it, `decompile` maps
the code back through the ASS convention (`8` = TopCenter) and warns — only
`8 ↔ TopCenter` is evidenced, the other eight are inference.

**Gaps between cues are copied verbatim, and must stay that way.** A measured srt
had 0 s, 0.111 s and 0.340 s gaps between four cues; srt display is discontinuous
by nature, so "fixing" them into a contiguous run changes what the picture does.
(A reading-follow effect *does* want contiguous windows — that is its own
requirement, not a subtitle one. Do not copy it here.)

Verified on the real export (4 cues): all four `Content`/`TimelineIn`/`TimelineOut`
match the srt exactly, the style from `--style-from` lands on every clip, the last
cue's end equals the srt carrier's `TimelineOut` (11.38 s), and the recompiled
Timeline contains no `FileUrl` and no `AI_*` left. Note the carrier clip starts at
`0.0` while the first cue starts at `6.05` — the carrier spans the track, not the
speech.

**Render equivalence is verified.** Two renders of the same 12 s source — one
from the exported Timeline as-is (srt track), one from the decompiled Timeline
(4 per-cue `Text` clips) — put the same text at the same position with the same
size and outline at every checkpoint, showed nothing during the inter-cue gaps,
and nothing after the last cue. Measured: subtitle-band SSIM 0.9934–0.9973,
consistently **higher** than the non-subtitle picture area (0.9794–0.9920), so the
residual difference is global re-encode noise rather than subtitles. A 4 fps sweep
of all 48 frames found no frame below 0.97 — no on/off drift, no position shift.

That comparison also settles a second question: **an unsigned srt `FileUrl`
renders fine when the Timeline is resubmitted** — the engine reads its own
registered bucket. Signing is only needed when *you* want to read the file (§2.1).

Still unknown is the practical cue ceiling: 89.6 s at `SentenceMaxLength=4`
produced 56 segments, so a full episode can reach several hundred `Text` clips,
and no clip-count limit is documented. Inlining a whole episode is untested.

### 5.2 Shapes `decompile` refuses

`compile_edl` is deliberately narrow: one `MainTrack`, one audio track, one
subtitle track, clips laid back-to-back in array order. Rather than flatten a
composition it cannot represent, `decompile` refuses it (all five verified):

| Refusal | Why |
|---|---|
| The Timeline still declares `AI_ASR`/`AI_TTS`/`AI_Avatar`/`VideoDetext` | It is a submitted Timeline, not an expanded one — export it first |
| More than one video / audio / subtitle track | PiP, avatar-over-background, split screen, layered audio have no EDL form |
| A clip whose `TimelineIn` is not where the previous clip ended | `compile` relies on array order; gaps and explicit offsets are not expressible |
| A clip with non-default `X`/`Y`/`Width`/`Height` | An EDL range carries no geometry |
| A clip with neither `MediaId` nor `MediaURL` | Nothing to address |

The refusal set coincides with the scope where EDL never applied anyway
(`18-edl-and-compile.md`: EDL is for "assembling N ranges"; avatar reads, slideshow
templates and pure-effect pieces stay hand-written). So for the cases that matter
— highlight cuts, episode stitches, subtitle replacement — decompile round-trips.

When a shape is refused, keep editing the exported Timeline directly (§4).

### 5.3 What a structural change costs after decompiling

| Change | Re-runs AI? |
|---|---|
| Retime / reword / restyle subtitles (cues inlined) | No |
| Trim or reorder ranges, swap material | No — but the inlined cues are absolute, so re-anchor the ones you moved |
| Re-render with a different resolution / output config | No |
| Add *new* AI work (another `AI_ASR`, a new TTS line) | Yes, for the new work only |

The materialized artefacts — erased video, TTS audio, avatar takes — are plain
material now and survive any amount of restructuring. Only the ASR cues carry a
time base, and after inlining that time base is data in your EDL rather than a
file you cannot edit.

## 6 Pitfall checklist

| Symptom | Cause / fix |
|---|---|
| `ExportResult.Timeline` empty on a `Success` job | `ExportType=AdobePremierePro` returns `ProjectUrl`, not a Timeline — use `BaseTimeline` |
| `ExportResult.SrtList` is empty | Measured behaviour — read the subtitle clip's `FileUrl` instead (§2.1) |
| 403 fetching the srt | `FileUrl` is unsigned and the bucket is private — sign it (§2.1) |
| `ProjectId` is `null` in the response | Expected when the source was an inline `Timeline` (§2) |
| Exported `Alignment` reads `"8"` instead of `"TopCenter"` | The engine normalizes style to numeric codes; do not assume style round-trips (§2) |
| Subtitle track has no visible text | Expected: text is inside the srt file, `Content` is `null` (§2.1) |
| `Status` stuck in `Processing` for minutes | The export is waiting on the source's unfinished AI task; keep polling, `--max-wait` defaults to 1800 s |
| `Pass exactly one of --project-id / --timeline` | Both or neither were given — the API is strictly one-of |
| Re-submitting the expanded Timeline fails with `InvalidMaterial.NotFound` | The embedded signed URLs expired — re-sign before submitting (§4) |
| Duplicated subtitles after re-render | `AI_ASR` re-added on top of the exported subtitle track (§4) |
| Export job billed unexpectedly | Exporting an unrendered Timeline runs its AI tasks; export the `ProjectId` of a finished render instead (§1) |
| `decompile` refuses the Timeline | The composition has no EDL form — see the table in §5.2 and keep editing the Timeline (§4) |
| Inlined cues drift after a structural edit | Cue times are absolute; re-anchor the cues you moved (§5.3) |
| Inlined subtitles render differently from the srt version | Should not happen — equivalence is measured (§5.1). Check the style source first (`--style-from`) |
| Hundreds of inlined cues on a full episode | Untested territory — no documented clip-count limit (§5.1) |
