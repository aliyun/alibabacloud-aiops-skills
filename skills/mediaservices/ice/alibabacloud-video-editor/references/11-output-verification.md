# Output Verification (Frame QA)

How to check a produced video before handing it to the user. A producing job that
reports `Success` only means the engine wrote a file — it does not mean the edit
looks right. Wrong material, black frames, clipped subtitles and silent audio all
come back as `Success`.

Verification reads **cloud snapshot frames** — ffmpeg does not extract them and
nothing is downloaded to the user's machine (SKILL.md Hard Rules 1–2).
`scripts/frame_qa.py` remains for model review of cloud material only: the whole
video, or signed snapshot frame URLs when you cannot see images yourself.

---

## 1. Pick a verification path

Try them in this order.

| Order | Path | Command | Cost | Use when |
|---|---|---|---|---|
| 1 | **Snapshot frames + your own vision** (preferred) | `video_editor.py snapshot --mode normal …` → `snapshot-urls` → read the signed frames | one job, ~6–12 s | Default for every output, any duration |
| 2 | **Snapshot filmstrip over the whole output** | `video_editor.py snapshot --mode webvtt --cover <duration>` → read the sprite tiles | one job, ~6–12 s | Structure at a glance: black frames, wrong material, a band that should have changed |
| 3 | **Whole video + model** | `frame_qa.py --video <url> --mode full` | ~7k+ tokens for 7s | Audio, sync or motion must be checked |

Frames first: an 89 MB / 78 s video becomes ~500 KB of JPEG, so cost stays flat as
duration grows. Whole-video review tokenises every second — a 7-second clip already
costs more than 16 frames of a 78-second one.

**Narration-led output needs a tail check, not just two early frames.** `media-info` now runs `ffprobe` on its signed URL and prints each video/audio stream duration. Then inspect a frame at `target - 0.5 s`; if the output exceeds the narration target, also inspect `output - 0.5 s`. Finally run the audio-only silence pass below — stream duration proves the track exists, not that its tail contains speech. A longer container, missing/short audio stream, black final frame, or unreported tail silence is unresolved even when the job status is `Success`.

```bash
# media-info prints container metadata, signed URL, and per-stream durations
python "$SKILL_DIR/scripts/video_editor.py" media-info -m <MediaId> -r <region>

# Required before claiming “no silent tail”; streams audio and writes no media
ffmpeg -v info -i "<signed output URL>" -map 0:a:0 \
  -af "silencedetect=noise=-50dB:d=0.25,volumedetect" -f null - 2>&1
```

If the last `silence_start` has no following `silence_end`, silence runs to the file end. Compare that start with the intended narration endpoint and report it together with `mean_volume`/`max_volume`; do not infer audio health from image snapshots.

**Paths 1–2 need no `DASHSCOPE_API_KEY`** — read the signed frame URLs with your
own vision (most agents are multimodal). Only path 3 needs the key. If you cannot
see images at all, the key stops being optional: send the same signed URLs to a
model — `frame_qa.py --frames "<url>" "<url>" …` — and report it as a model
review, not as your own. With neither vision nor a key, tell the user how to set
the key (SKILL.md §1.3) and report the output as unverified.

---

## 2. Commands

```bash
# Default: take cloud snapshot frames from the finished output, then read them
python "$SKILL_DIR/scripts/video_editor.py" snapshot \
  -i <output MediaId or oss://bucket/out/result.mp4> -r <region> \
  --mode normal --time 0 --count 16 --interval 5 --width 960 \
  -O "oss://<bucket>/qa/out-{Count}.jpg" --wait
python "$SKILL_DIR/scripts/video_editor.py" snapshot-urls -j <job_id> -r <region>

# Denser sampling — short transitions are missed at a 5 s interval
#   … --interval 1 --count 30 …

# One instant (a seam, a cue midpoint): --time is MILLISECONDS
#   … --time 12400 --count 5 --interval 1 …

# Whole output as one filmstrip with a time↔pixel map
#   … --mode webvtt --cover <duration> -O "oss://<bucket>/qa/out.vtt" --wait

# Audio, sync or motion — the only path that needs a DashScope key
python "$SKILL_DIR/scripts/frame_qa.py" --video "<signed output URL>" --mode full \
  --prompt "Is the avatar centred and is the subtitle inside the safe area?"

# You cannot see images yourself: hand the same signed frame URLs to a model
python "$SKILL_DIR/scripts/frame_qa.py" --frames "<signed url 1>" "<signed url 2>"
```

| Parameter (`snapshot`) | Default | Notes |
|---|---|---|
| `-i, --input` | — | `oss://` object or MediaId of the **output**; a fresh output object may need registering first (`23-production-pitfalls.md`) |
| `--mode` | `webvtt` | `normal` = separate frames, `sprite` = one tiled image, `webvtt` = tiles + time map |
| `--time` | `0` | Start time in **milliseconds** |
| `--interval` | `2` | Seconds **between frames inside one job**. `--time` is milliseconds, so any sub-second instant is reachable — as its own `--count 1` job (§3) |
| `--count` | `40` | Frames to emit |
| `--width` / `--height` | source | Raise `--width` to 960 before concluding that small text is illegible |
| `-O, --output` | — | `oss://bucket/prefix`; `normal` needs `{Count}` in the object name, `webvtt` must end `.vtt` |

The frames stay in OSS — read them through the signed URLs `snapshot-urls`
returns. A signed URL is not a local path: do not pass it to a file reader that
requires an absolute filesystem path. Use a URL-capable vision/browser tool, or
`curl -fL "<signed frame URL>" -o "$SCRATCH/frame.jpg"` and inspect that scratch
file with an image-capable tool. Nothing lands in the user's project.

---

## 3. Sampling guidance

- **Default `--interval 5`** suits narration, slideshow and single-scene output.
- **Cuts and transitions**: a `DLTransition` lasts 0.3-1 s, so a 5 s grid almost
  always misses it. Aim at it — `--time <ms of the cut> --count 5 --interval 1` —
  when the transition itself is the deliverable.
- **Long video**: one job emits at most `--count` frames and nothing widens the
  interval for you, so cover the duration by raising `--interval`, and inspect a
  specific stretch with a second job pointed at it via `--time`.
- **Small text**: raise `--width` to 960 before concluding that subtitles are
  illegible; a narrow frame blurs small fonts on its own.
- **Subtitle tracks**: a cue shorter than your `--interval` falls between frames,
  so give it its own job — `--time <cue midpoint in ms> --count 1`. Sample at
  **cue midpoints**, never at switch instants: a motion-in effect's first 0.25 s
  is nearly invisible, so a frame at the cue start proves nothing.
- **Jobs that alter only part of the picture** (`VideoDetext`, `VideoDelogo`, a
  crop): sample *inside* the region that should have changed, and confirm an
  unrelated detail survived — a tattoo, a prop, on-screen text outside the band.

---

## 4. What frames cannot catch

Frame sampling is blind to anything between the sampled instants. Escalate to
`--mode full` (or accept the gap and say so) for:

- audio: silent narration, missing BGM, wrong volume balance
- audio/video sync, including lip sync on `AI_Avatar` output
- stutter, dropped frames, wrong playback speed
- animation that only reads as motion: `KenBurns`, `Scroll*`, subtitle animation
- transitions shorter than the sampling interval

A frames-only pass therefore verifies *composition*, not *playback*. For any
output whose value is in the audio (TTS narration, avatar newscast, BGM mixing),
run one `--mode full` check as well.

`--mode full` has its own ceiling: measured, a vertical 1080×1920 output over
~60 s comes back **HTTP 400 "video too long"**. When it does, fall back to
`volumedetect` / `silencedetect` on the signed URL for the audio claims — and
report which check you actually ran instead of implying a whole-video review.

---

## 5. Reading the result

The model returns content description, broken-frame findings, text legibility,
consistency and a 1-10 score. Act on it:

- **Material mismatch** (content is not what the user asked for) → a `MediaURL`
  points at the wrong file; re-check §4 of SKILL.md and resubmit.
- **Black or empty frames** → usually a missing background (`GlobalImage` without
  `Duration`, or a narration-only timeline). See SKILL.md §5-C.
- **Subtitles clipped or unreadable** → adjust `FontSize`/`Alignment` and
  resubmit; re-verify at `--width 960` first to rule out sampling blur.
- **Style jumps** → an unintended `Filter`/`VFX` on one clip only.

Two caveats when reporting:

- The model can misread a scene (e.g. a physical model of a launch pad read as a
  control room). Treat a single odd observation as a prompt to look again, not as
  proof of a defect.
- Always tell the user which path verified the output — frames or whole video —
  and name the blind spots from §4 that remain unchecked.

---

## 6. Seams — the pass generic QA misses

Model QA rarely reports a chopped line or a misplaced watermark, so any output
assembled from cuts (`18-edl-and-compile.md`) needs a seam pass of its own after
every submit:

1. **Re-sign the output URL** — signatures expire (~2 h), and a 403 mid-check
   reads as a missing frame.
2. **Subtitle bands over the whole output** — a snapshot job at `--interval 1`
   (`--mode normal`, `--width 960`), read through its signed URLs; no local crop,
   ffmpeg does not touch the picture. At *every* seam the frame before must show a
   completed line or no subtitle, and the frame after must show the next line's
   first frame or no subtitle.
3. **Suspect seams get one-frame jobs at millisecond offsets** — seam −0.2 / −0.1 /
   +0.1 / +0.2 s is four `--count 1` jobs, and that is how a defect living inside
   0.25 s becomes visible: `--time` is the millisecond knob, `--interval` only
   spaces frames within a job. Look for (a) the next line's beginning bleeding in,
   (b) residual frames of the next source shot, (c) any requested watermark:
   present, uncut, correctly placed.
4. **`timeline_view.py --seams edl.json`** renders one image per seam, both
   sides, with the audio track alongside — which is how you catch dialogue that
   runs past the visual cut.
5. **Only report "fixed" after the previously failing seam passes this check.**

---

## 7. Re-voiced output — a dub or narration replacing the original dialogue

Frames cannot hear it, and `--mode full` over a whole episode is out of reach
(§4). Four cheap checks instead:

1. **Per-line window ASR.** For every cue, cut `[line_start - 0.05,
   next_line_start - 0.08]` from the *rendered output* and recognize it in the
   target language. One pass catches a wrong language, a missing tail, a line
   bleeding into the next window, and silence.
2. **Timbre spot-check** against the vocals stem (`iproduction -f MusicDemix`):
   "ignore the language — same voice?". With no omni key there is no automatic
   substitute: switch to human listening, or deliver with the gap stated plainly.
3. **Subtitle frames at cue midpoints**: text present, inside the frame, at the
   band position, and still on screen while the line is spoken.
4. **Bed loudness** (`volumedetect`) over a dialogue-free stretch — confirms the
   accompaniment survived (measured −23.5 dB mean).

**ASR hallucination hides truncation.** Recognizing a cut-off take returned the
*complete* sentence, and short windows invented words that were never
synthesized. So when a window looks wrong, recognize the trimmed wav itself and
length-check it; never accept a "complete" reading of a take you have not
measured. The reverse also holds — a suspicious ASR result is not proof of a
defect, so confirm against the audio before paying for a re-render.
