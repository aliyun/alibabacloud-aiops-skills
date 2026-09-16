# 19 Editor brief & structural archetypes

Two things this document provides: a **brief template** for delegating "pick the best ranges out of this material" to a sub-agent, and a set of **structural archetypes** to shape the result. Both exist because "cut a highlight" is under-specified until you decide what shape the output has.

Use the brief when the selection work is substantial — long material, many candidate moments, several episodes. For a 30-second clip with three lines, just do it inline.

## 1 Structural archetypes

Pick one, adapt it, or invent one. These are shapes that have shipped, not a taxonomy.

| Archetype | Shape | Fits |
|---|---|---|
| **Short-drama highlight** | THREAT → ESCALATION → ACTION CLIMAX → EMOTIONAL CLOSER | Vertical short drama, promo cuts. The proven skeleton: 2–3 strongest lines + one action peak + one closer (scream, kneel, reversal). Everything else — setup banter, henchmen, transitional fights — goes (§4) |
| **Episode stitch** | TITLE CARD → EP1 … EPN → END CARD | Full-episode concatenation (`06-multi-clip-editing.md`) bookended by title cards (`03-subtitles-and-titles.md`, `04-effects-and-transitions.md`) |
| **Problem → solution demo** | HOOK → PROBLEM → SOLUTION → BENEFIT → EXAMPLE → CTA | Product launch, feature demo, tech explainer |
| **Narration explainer** | INTRO → SETUP → STEPS → GOTCHAS → RECAP | Tutorial, `AI_TTS` / `AI_Avatar` voiceover pieces (`07-smart-media-features.md`) |
| **Live-commerce cut** | HOOK → PAIN → PRODUCT REVEAL → PROOF → OFFER | E-commerce clips sliced out of a long stream |
| **Interview** | (QUESTION → ANSWER → FOLLOW-UP) × N | Talking heads, multi-take material |
| **Montage / mood** | ARRIVAL → HIGHLIGHTS → QUIET BEAT → DEPARTURE | Travel, event recap, photo slideshow (`05-slideshow-template.md`) |

Every value below the archetype — how many beats, how long each runs, whether there is a closer at all — is a taste call on the material, not a rule.

## 2 The brief

The structure is load-bearing; the specifics are examples. Fill in and hand to a sub-agent.

```
You are cutting a <type> video. Choose the best range for each beat and
assemble them in beat order, not in source order.

INPUTS
  - material_packed.md — the dialogue timeline with cut markers.
    `CUT ` = safe seam. `CUT?` = the speech gap qualifies but the audio does
    not fall silent — verify before using. A segment prefixed `·` does not end
    on punctuation: it was truncated mid-sentence, never cut after it.
  - <filmstrip PNG or tile URL>, for what the picture is doing
  - Story context: <2 sentences>
  - Speakers: <name, role, delivery>
  - Structure: <archetype from §1, or your own>
  - Target runtime: <seconds>  (source is <N>s)

RULES
  - Every `in` and `out` must sit on a seam marked CUT in material_packed.md.
    A CUT? seam needs a timeline_view.py check first; say so in the reason.
  - Never split a dialogue block to hit the runtime. Drop whole blocks.
  - If a gap is under 0.3s, keep the whole block or make the two ranges
    contiguous (out == in) — the engine rounds tails by ~0.2s.
  - Start `in` AT a shot change, never a few frames after one, or the previous
    shot's residue leaks in.
  - Keep the peaks: the threat, the signature line, the reversal, the laugh.
    Extend past a punchline to include the reaction — the reaction is the beat.
  - If over budget, drop a beat and report it. Do not trim inside blocks.

OUTPUT
  An EDL (references/18-edl-and-compile.md §1) — JSON, no prose:
  {"sources": {...}, "ranges": [
     {"source": "...", "in": 0.0, "out": 0.0, "beat": "...",
      "quote": "...", "reason": "..."}]}

  `reason` states why THIS range and THIS boundary: which seam, whether the
  audio was confirmed silent, what the alternative was. One line.

Then report the total runtime, its ratio to the source, and any beat you
dropped. Do not ask questions — if something is ambiguous, take the most
obvious reading and note it in the reason.
```

Two rules for the sub-agent prompt itself: make it **self-contained** (a sub-agent has none of your context — inline the paths, the numbers, the archetype), and give it **one job**. Selection and rendering are separate tasks; do not ask for both.

## 3 What to hand over, and what not to

Hand over `material_packed.md` and a filmstrip. Do **not** hand over the raw ASR JSON — it is an order of magnitude more tokens for strictly less information, since the packed view already carries gaps, punctuation flags and silence verdicts on one axis (`pack_material.py`).

Do not hand over your own cut list "for reference". It anchors the sub-agent onto your first idea, which is exactly the judgement you were delegating.

## 4 Length discipline

Decide the target *before* selecting, and say it out loud to the user (SKILL.md §2.2). Defaults that have held up:

- Highlight / promo: **30–40 %** of the source; 20–25 % for short-video platforms.
- When offering the user length options, cap the longest at **half** the source. Never offer "as long as possible".
- Real case: a 79 s single-scene source cut to 66 s (84 %) was rejected as "too long, not a highlight"; the 30 s version (38 %) passed.

`compile` warns when the kept duration exceeds 50 % of the known source duration, but only if the EDL declares `duration` on each source — so declare it.

## 5 After the EDL comes back

1. `compile -e edl.json` — fix blockers, judge warnings (`18-edl-and-compile.md` §3).
2. Confirm the plan with the user in plain language (SKILL.md §2.2).
3. Submit, then verify the seams with `timeline_view.py --seams edl.json` — one image per seam, both sides (`11-output-verification.md` §6 for the whole pass).
4. On a fix, edit the EDL and recompile. Never hand-patch the Timeline.
