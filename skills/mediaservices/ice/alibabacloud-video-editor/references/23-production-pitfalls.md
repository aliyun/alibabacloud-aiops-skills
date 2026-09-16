# 23 Production Pitfalls — field notes from real jobs

Hard-won, verified pitfalls that cut across the other references. Read when a
job touches assets, delivery, splicing, or templates. Project-specific
templates and parameters live in the calling project, not here.

## 1 Assets & region

- **Bucket must be registered with IMS** before any ICE job touches it.
  Unregistered bucket → snapshot/ASR rejected with `InvalidStorage.NotFound`
  at submit. Check with `aliyun ice get-storage-list --region <region>`; ask
  the user which registered bucket to use (do not silently pick one).
- **ASR input must be a MediaId.** Submitting an `oss://` URL as ASR input
  fails *silently*: job State=Failed with ErrorCode/Message both None, while
  snapshot jobs on the same bucket succeed. Fix: `register-media-info`
  (returns MediaId) and re-submit ASR with the MediaId.
- MediaId inputs and the output bucket must share the submit region.

## 2 Shell & tooling

- Run skill scripts with the skill's own `.venv/bin/python`; the system
  python3 lacks the SDK deps.
- **zsh does not word-split.** `for x in $list`, `set -- $spec`, and
  unquoted expansions silently misbehave ("== not found", broken loops).
  Iterate with `while read -r ...; do ...; done <<'EOF'` blocks instead.
- `scripts/oss_sign_clean.sh` prints the verified URL with a `URL: ` prefix;
  capture that line rather than assuming bare URL output.
- **Cropping a still with `sips --cropOffset` does not anchor top-left** as the
  man page says (measured on macOS: a watermark sliver survived into a render).
  Do not reach for a local image tool at all — crop in the Timeline with the
  `Crop` effect on the `Image`/video clip (`06-multi-clip-editing.md`), and
  **read a snapshot frame of the result** before calling it done. A still that
  genuinely must be pre-cropped is an asset the user or upstream hands over
  (SKILL.md Hard Rule 2).

## 3 Signed-URL delivery (private buckets)

- **STS expiry is separate from URL expiry.** A URL signed with temporary
  credentials stops working when the STS token expires even if its own expiry is
  later. Sign immediately before delivery; never reuse a URL from an old session.
- Use `oss_sign_clean.sh`, which delegates to `aliyun ossutil presign` with V4,
  includes the STS security token when present, supplies the bucket region, and
  verifies the result with a ranged GET (HTTP 206/200). A failed verification is
  not a deliverable.
- `--expires-duration` caps at `1w`; pass the correct region because V4 scopes the
  signature to it. The signer accepts either `cn-shanghai` or the legacy endpoint
  spelling `oss-cn-shanghai.aliyuncs.com`, and each object needs its own URL.
- **Ceilings worth knowing:** `media-info` STS URLs expire within ~1 h and some
  cannot be fetched by the model service at all; snapshot outputs get
  `GetSnapshotUrls --timeout 129600` — **36 h, verified**
  (`17-snapshot-and-asr.md` §2.7).
- Always state the expiry and hand over a one-liner to re-sign.

## 4 Splice segments — un-cut dialogue beats everything

For recaps/previews quoted from other episodes:

- `In` = sentence-start word Begin − 0.2…0.4 s (and ≥0.2 s after the
  previous sentence's End); `Out` = sentence-final word End **+ ≥0.5 s**
  (never below 0.4 s); the sentence must end at `. ? !` — never at a comma
  or mid-sentence. Extending `Out` into the gap before the next sentence is
  free; a last preview segment may run to the source's final frame.
- If a hook sentence cannot be quoted without truncation, **drop it or swap
  it** — never tighten the margin.
- **Close the loop after rendering**: run ASR on the finished output and, for
  every segment window, check the expected tail words (with punctuation)
  appear and end ≥0.3 s before the window edge.
- ASR artifacts cause false misses — judge by word-list time continuity:
  word-final sounds split into extra tokens ("straight" → "straight ed"),
  and fast-speech mishears at segment heads.
- When the user reports one truncated segment, re-audit **all** segments
  against the word-level table; sub-0.1 s margins elsewhere will surface.

## 5 Look baseline — "no motion" is a first-class preset

- When the client says effects are dizzying, remove **all** motion: card
  Zoom, `DLTransition`, `EffectTracks` VFX, and text `AaiMotion*` effects.
  Cards and seams become hard cuts; text must be fully visible the instant
  its window opens (no typewriter).
- The motion presets this sits beside, all verified on real jobs: **Gentle**
  (`KenBurns` on cards, ambient VFX such as `sparklestarfield` /
  `meteorshower`, `typewriter1_in` + `blur_in` text, `fade` transitions),
  **Punchy** (`Zoom` 1.0→1.3 rush, `heartbeat` VFX, `heartbeat_display` text,
  `glitchdisplace` in / `burn` out), and **Punchy-but-watchable** (Punchy with
  `heartbeat` confined to ~1 s windows so the rest of each card stays clean).
  Effect names and their parameters: `04-effects-and-transitions.md`.
- Constraints that hold in every preset: no transition on the last clip;
  `DLTransition`, not `Transition`, on a card so the flash does not shorten the
  timeline; `Alignment + Y` only, never pixel X/Y pairs.

## 6 Timeline & template engineering

- The submitted Timeline must contain **only engine-known fields**. A
  convenience comment field (e.g. `"_template": "..."`) can be rejected —
  carry metadata in filenames/docs instead.
- Fillable JSON templates: **numeric placeholders unquoted**
  (`"TimelineIn": {{T_END}}`), string placeholders quoted
  (`"MediaId": "{{EP}}"`). Quoted numeric placeholders survive replacement
  as strings and may be rejected or mis-parsed; assert no `{{` residue and
  json-validate after filling.
- Normal templates (`AddTemplate`, Type=Timeline; see 22): `$param:default`
  parameterizes **any** field, including timeline numerics and text Content;
  `submit-media-producing-job --template-id` **requires** a non-empty
  `ClipsParam` (pass `{}` to ride on defaults); `$param:NULL` deletes the
  field when omitted; variable segment counts need `Sys_ArrayObject`
  arrays. Verify storage with `get-template` (Config round-trips verbatim).
- **Video `LoopMode` can be silently ignored.** A normal-template job returned
  `Success` with `TimelineOut: 35.856`, but a 15 s video clip still produced a
  15 s file and truncated the longer narration. Use `LoopMode` only on audio;
  repeat video as adjacent clips / `ArrayItems`, trim the final copy, and treat
  any output shorter than the required narration as **not delivered**.

## 7 Verification additions (no-motion edition)

- Duration must equal the designed `T_END` ±0.1 s (ffprobe on the signed URL).
- `volumedetect`: mean ≈ −20 dB, max ≤ 0 dB — catches silent/mis-spliced audio.
- Frame points: card mid-frame (static, text complete), **every seam
  ±0.3 s** (no glitch/burn residue, no zoom drift), label first frame (text
  already complete — proves no typewriter), last frame (ending card intact).
  The full seam pass: `11-output-verification.md` §6.
- Compare same-phase frames across versions when judging an effect-strength
  change — a job that silently ignored a parameter renders identically to one
  that applied it, so a single version proves nothing.
