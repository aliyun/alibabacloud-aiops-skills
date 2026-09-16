# 18 EDL & compile — the editorial decision layer

An **EDL** records *cut decisions*: which source, which range, which beat, and **why**. `video_editor.py compile` turns it into an ICE Timeline and runs the SKILL.md §5 pre-submit checklist mechanically.

Why this layer exists: the Timeline is a *render target*, not a thinking medium. It is deep, verbose, and holds no room for rationale. Revising "make the third clip shorter" means regenerating 300 lines of JSON and re-checking twelve rules from memory. Revising an EDL means changing one number and re-running `compile`.

`compile` is **offline** — no credentials, no region required, no API call, nothing billed. Run it as often as you like.

## 1 EDL format

```json
{
  "version": 1,
  "sources": {
    "ep01": { "media_id": "f1e2d3c4b5a6f7e8d9c0b1a2f3e4d5c6", "duration": 89.584 },
    "bgm":  { "url": "https://bucket.oss-cn-beijing.aliyuncs.com/m1.wav" }
  },
  "ranges": [
    { "source": "ep01", "in": 6.06, "out": 16.21,
      "beat": "HOOK",
      "quote": "Can it handle the work we do to make a living from this land?",
      "reason": "The question mark is a sentence boundary followed by 4.03s of silence; both conditions are met." }
  ],
  "audio": [
    { "source": "bgm", "gain": 0.25, "loop": true,
      "in": 0, "out": 17.06, "timeline_in": 0, "timeline_out": 17.06 }
  ],
  "subtitles": [
    { "type": "Text", "Content": "Show Title", "Alignment": "TopRight",
      "FontSize": 80, "FontColor": "#FFD700" }
  ]
}
```

### `sources`

Name → material. Exactly one of `media_id` **or** `url` (both ⇒ error). Optional `duration` in seconds unlocks two checks that cannot run without it: range-exceeds-source, and the highlight length ratio. Optional `image: true` marks a still so it compiles to `Type: "Image"`.

Copy `url` **verbatim** (SKILL.md §4) — one changed character yields `InvalidMaterial.NotFound`.

### `ranges`

Play order = array order. `in`/`out` are seconds in the **source**.

| Field | Required | Purpose |
|---|---|---|
| `source` | yes | key into `sources` |
| `in` / `out` | yes | source range; `out > in` |
| `beat` | no | structural role (`HOOK`, `PROBLEM`, `TURN`, …) — carried for reasoning, dropped at compile |
| `quote` | no | the line this range carries |
| `reason` | no but **warned** | why *this* take/boundary. This is what makes the next iteration auditable |
| `speed`, `duration` | no | passed through to the clip |
| `effects` | no | clip `Effects` array, passed through and linted |

Put clip decoration directly on each range. A transition belongs to the **earlier** range; the last range has none:

```json
{"source":"h1","in":0,"out":10.78,"reason":"whole clip","effects":[
  {"Type":"Volume","Gain":0},
  {"Type":"Background","SubType":"Blur","Radius":0.1},
  {"Type":"DLTransition","SubType":"linearblur","Duration":0.5}
]}
```

Use the same field for blur, filters, VFX, mute and transitions; `compile` passes the array through and runs the §5 checks. Put timeline-wide atmosphere effects in top-level `EffectTracks` (below), not in a hand-written Timeline.

### `audio` / `subtitles`

`audio` entries become one `AudioTracks` entry. `gain` compiles to `{"Type": "Volume", "Gain": …}` (SKILL.md §5-B: the key is `Gain`, never `Volume`). `loop: true` compiles to `LoopMode`.

`subtitles` entries pass through to `SubtitleTrackClips` almost verbatim — only `type` is lowercase-renamed to `Type`, so use ICE's own field names (`Content`, `Alignment`, `FontSize`) directly.

`EffectTracks`, `FECanvas` and `MaxDuration` at the EDL top level pass straight through.

## 1.5 Where a cut may sit — boundary rules

`in`/`out` are the only numbers that decide whether a cut reads as editing or as damage. Every rule below was paid for by a real failed render.

- **Every boundary sits in a gap between two spoken lines.** The cheap filter is trailing punctuation **and** a gap ≥ 0.3 s (`17-snapshot-and-asr.md` §1.5); a gap-only rule mis-cuts 2 of 16 candidates.
- **Gap < 0.3 s → keep the whole dialogue block.** The producing engine rounds clip tails by ~0.2 s, so a narrow gap either leaks the next line's beginning or amputates the current tail.
- **Adjacent ranges inside a dense exchange stay contiguous** (`ranges[i].out == ranges[i+1].in`) so the rounding renders as seamless continuation instead of a chopped line.
- **Prefer ending on a wide silence** (≥ 0.3 s). Including a couple of seconds of ambient tail (rain, engine, digging) to reach one is fine.
- **`out` follows the audio tail, not the visual cut.** Dialogue routinely bridges a source cut — the line ends after the next shot has begun. `silencedetect` is the ground truth here (`17-snapshot-and-asr.md` §1.6).
- **`in` lands *at* a scene-cut point**, never a few frames after one — otherwise the previous shot's residual frames leak in and the edit reads as choppy.
- **Compress by dropping whole blocks**, never by trimming inside one. If a single block is too long, cut at its own internal gap and re-verify that seam.
- **Total duration comes from measured speech, not a guess.** A guessed tail leaves dead air (measured: 54.7 s of speech inside a 66 s guess); derive the last `out` from the ASR end plus the linger you actually want.
- **Upstream candidate windows are ~1–2 s granular** (SKILL.md §2.4) — snap them onto the seams above before they become `in`/`out`. Copying one verbatim amputates dialogue.
- **Hard cuts by default; add transitions only when requested.** Put the requested transition in the earlier range's `effects` array; prefer `DLTransition` when total duration must stay unchanged (§1 example). A transition blurs frames across the seam and can swallow the outgoing line's tail.

Which blocks to keep, how long the result should be, and how to delegate that selection: `19-editor-brief.md`. Verifying the seams you chose: `11-output-verification.md` §6.

## 2 What compile produces

Video ranges land on **one `MainTrack`** with `In`/`Out` and **no** `TimelineIn`/`TimelineOut`, so they play back-to-back in array order (SKILL.md §5-D). Nothing else is invented — no transitions, no filters, no watermark unless the EDL asked for it.

```bash
# Compile, check, and write the Timeline
python "$SKILL_DIR/scripts/video_editor.py" compile -e edl.json -O timeline.json -r cn-beijing

# Checklist only, nothing written
python "$SKILL_DIR/scripts/video_editor.py" compile -e edl.json

# Warnings become blocking
python "$SKILL_DIR/scripts/video_editor.py" compile -e edl.json --strict

# Timeline on stdout, no commentary — for piping
python "$SKILL_DIR/scripts/video_editor.py" compile -e edl.json -q
```

Then present the plan to the user in plain language (SKILL.md §2.2) and submit once it is confirmed: `submit -t timeline.json -o output.json -r <region> --wait`. A clean `compile` is not a green light to render — it only means the checklist passed.

`-r/--region` is optional and only enables the AI-feature region check; when omitted, `compile` says so rather than silently skipping it.

## 3 BLOCK vs WARN — and why the split matters

ICE exposes **no dry-run / validate-timeline endpoint**. This linter is therefore a *local re-implementation* of engine rules, and it will drift as the engine changes. That makes a false positive — refusing a legal Timeline — worse than no check at all: it blocks work with no authority to appeal to.

So the split is deliberate:

- **BLOCK** — only rules where a real failed job is on record. Every message cites the SKILL.md section holding that failure. These would fail at ICE anyway; failing locally in 50 ms is strictly better than failing in the cloud after billing.
- **WARN** — everything else: quality heuristics, "silently produces a wrong result" cases, account-dependent behaviour. Advisory, never fatal.

### Blocking rules

| Rule | Failure it prevents | Cite |
|---|---|---|
| AI type without the `AI_` prefix (`ASR`/`TTS`/`Avatar`/`Matting`/`RealMatting`), as clip Type or effect Type | job rejects the bare name | §5-A |
| `AI_Avatar` inside `Effects` | `InvalidTimelineFormat: ... MediaId is empty` | §5-A |
| `AI_Avatar` on a non-video track | same | §5-A |
| Matting used as a clip `Type` | matting is an effect | §5-A |
| Effect `SubType: "Matting"` | wrong spelling for `AI_Matting` | §5-A |
| `ColorType` instead of `Color` on matting | parameter ignored / rejected | §5-A |
| `VFX` with SubType `hflip`/`vflip`/`flip`/`mirror` | `InvalidTimelineFormat: Invalid vfx subType` | §5-A |
| `Text` field instead of `Content` on a Text/Subtitle clip | text never renders | §5-A |
| `Volume` key inside a Volume effect | `ProduceFailed` | §5-B |
| Overlapping clips on one audio track | rejected | §5-B |
| One `EffectTracks` entry mixing effect kinds | job fails when Filter + VFX share a track | §5-C |
| Video **and** audio tracks both empty | `TimelineFormatError: Both video tracks and audio tracks are empty.` | §5-D |
| `AI_*` used with `--region` outside `cn-shanghai`/`cn-beijing`/`cn-hangzhou` | feature unavailable in region | SKILL.md §3, `25-error-index.md` |

### Warnings

| Rule | Why it is advisory |
|---|---|
| Gap between adjacent same-source ranges under **0.3 s** | The engine rounds tails by ~0.2 s, so a narrow gap leaks the next line's start or clips the current tail — but the right fix depends on intent (make ranges contiguous, or keep the whole block). §1.5 |
| Kept duration above **50 %** of known source duration | A highlight that keeps most of the source reads as unedited — real case: 79 s → 66 s (84 %) rejected, 30 s (38 %) accepted. `references/19-editor-brief.md` §4. Requires `duration` on every used source |
| Overlapping source ranges | The same footage plays twice — occasionally intentional |
| Range without `reason` | Costs nothing now, costs the next iteration later |
| Regular `Transition` | Shortens the output by its `Duration`; `DLTransition` does not. §5-C |
| `GlobalImage` without `Duration` | Shows on the first frame only *when the timeline has no real video*. §5-C |
| `NeedHighlighting` on an `AI_ASR` in `SubtitleTracks` | Silently has no effect; move `AI_ASR` into a video/audio clip's `Effects`. §5-A |
| Advanced effect id (`OT0001-*` / `OV0001-*`) | Rejected unless the paid package is enabled — account-dependent (`25-error-index.md`) |
| Volume effect with no `Gain` | No-op |
| Clip with both `MediaId` and `MediaURL` | ICE uses one; the other is dead weight |

The same checklist runs automatically inside `submit`, so a Timeline written by hand gets the identical treatment before anything is billed.

## 4 Worked example

An EDL cut from the measured ASR timeline of an 89.584 s vertical short drama (`references/17-snapshot-and-asr.md` §1 supplied the boundaries):

```
EDL
  [ 0] ep01            6.06–16.21   (10.15s)  @  0.00  HOOK       Can it handle the work we do to make a living from this land?
  [ 1] ep01           20.24–21.10   ( 0.86s)  @ 10.15  TURN       Interesting,
  [ 2] ep01           23.98–30.03   ( 6.05s)  @ 11.01  PROBLEM    Urgent notice: heavy rain has made the road impassable.
  total 17.06s across 3 ranges

Pre-submit checklist (SKILL.md §5)
  checklist clean
```

17.06 s of 89.584 s = 19 %, comfortably inside the highlight band. Every boundary sits on a segment that ends with punctuation **and** has a gap ≥ 0.3 s after it — the two-condition rule from `references/17-snapshot-and-asr.md` §1.5.

## 5 Where the EDL sits in the workflow

1. Read the material — `references/17-snapshot-and-asr.md`: ASR for the dialogue timeline, snapshot `WebVtt` for the filmstrip.
2. Decide the cuts — write `edl.json`, one `reason` per range.
3. `compile` — fix blockers, judge warnings.
4. Confirm the plan with the user in plain language (SKILL.md §2).
5. `submit` the compiled Timeline.
6. Verify (SKILL.md §9); on a fix, edit the **EDL**, not the Timeline, and recompile.

Keeping the EDL as the thing you edit is what makes step 6 cheap. A Timeline hand-patched after a verification failure diverges from the decisions that produced it, and the next iteration has nothing to reason from.
