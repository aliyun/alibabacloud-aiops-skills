#!/usr/bin/env python3
"""Localize a subtitle track: wrap lines, recompute dwell time, check the glossary, emit SRT.

Implements references/03-subtitles-and-titles.md §11. Offline — no credentials, no API calls.

Inputs
  --script        source script JSON: {"duration": <s>, "lines": [{"id","speaker","start","end", ...}]}
  --glossary      glossary JSON with per-language "style_rules" (max_lines, max_chars_per_line,
                  reading_cps, min_duration) and term groups whose entries carry a per-language form
  --translations  {"<line id>": "<translated text>"}
  --lang          target language key used in style_rules and in glossary term entries
  --dub-manifest  optional [{"id": <n>, "dur": <seconds>}, ...] of MEASURED dub audio lengths;
                  when given, every cue is extended to cover its dub (§4, the rule users notice first)

Outputs --out (cue JSON consumed by the timeline builder) and --srt.

Exits non-zero when a wrapped line still exceeds the width/line budget or a glossary term is missing:
that means the translation is too long or has drifted. Shorten or fix the text — the limits are the
deliverable spec, not a suggestion (§6 priority ladder: rewrite > speech rate > atempo).
"""
import argparse
import json
import sys


def wrap(text, max_chars, max_lines):
    """Break on word boundaries. Raises ValueError when the text cannot fit the budget."""
    if len(text) <= max_chars:
        return [text]
    lines, cur = [], ""
    for word in text.split():
        cand = (cur + " " + word).strip()
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    over = [ln for ln in lines if len(ln) > max_chars]
    if over:
        raise ValueError(f"unbreakable segment exceeds {max_chars} chars: {over[0]!r}")
    if len(lines) > max_lines:
        raise ValueError(f"needs {len(lines)} lines, budget is {max_lines}: {text!r}")
    return lines


def srt_time(t):
    hours, minutes = int(t // 3600), int(t % 3600 // 60)
    seconds, millis = int(t % 60), int(round((t - int(t)) * 1000))
    if millis == 1000:
        seconds, millis = seconds + 1, 0
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def check_glossary(glossary, lang, source_text, translated, line_id):
    """Every glossary term present in the source must appear in its pinned target form."""
    problems = []
    for group, entries in glossary.items():
        if group == "style_rules" or not isinstance(entries, dict):
            continue
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            term = entry.get("term") or entry.get("full_name")
            pinned = entry.get(lang)
            if not term or not pinned:
                continue
            if term.lower() in source_text.lower() and pinned not in translated:
                problems.append(f"line {line_id}: {term!r} must stay {pinned!r}")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True)
    ap.add_argument("--glossary", required=True)
    ap.add_argument("--translations", required=True)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--dub-manifest")
    ap.add_argument("--source-key", default="en",
                   help="field on each script line holding the source text (default: en)")
    ap.add_argument("--gap", type=float, default=0.05,
                   help="minimum gap before the next cue, seconds (default: 0.05)")
    ap.add_argument("--tail", type=float, default=0.5,
                   help="seconds reserved before the video end for the last cue (default: 0.5)")
    ap.add_argument("--out")
    ap.add_argument("--srt")
    args = ap.parse_args()

    script = json.load(open(args.script))
    glossary = json.load(open(args.glossary))
    translations = {str(k): v for k, v in json.load(open(args.translations)).items()}
    rules = glossary["style_rules"][args.lang]
    duration = script.get("duration")

    dub = {}
    if args.dub_manifest:
        for entry in json.load(open(args.dub_manifest)):
            dub[str(entry["id"])] = float(entry["dur"])

    lines = script["lines"]
    cues, srt, errors = [], [], []

    for i, line in enumerate(lines):
        lid = str(line["id"])
        source_text = line.get(args.source_key, "")
        if lid not in translations:
            errors.append(f"line {lid}: no translation provided")
            continue
        text = translations[lid]
        errors += check_glossary(glossary, args.lang, source_text, text, lid)

        try:
            wrapped = wrap(text, rules["max_chars_per_line"], rules["max_lines"])
        except ValueError as exc:
            errors.append(f"line {lid}: {exc}")
            continue

        start = float(line["start"])
        if i + 1 < len(lines):
            ceiling = float(lines[i + 1]["start"]) - args.gap
        elif duration is not None:
            ceiling = float(duration) - args.tail
        else:
            ceiling = start + max(rules["min_duration"], len(text) / rules["reading_cps"])

        read_end = start + max(rules["min_duration"], len(text) / rules["reading_cps"])
        want_end = read_end
        if lid in dub:
            want_end = max(want_end, start + dub[lid] + args.gap)
        end = min(want_end, ceiling)

        if lid in dub and end < start + dub[lid]:
            errors.append(
                f"line {lid}: dub is {dub[lid]:.2f}s but only {ceiling - start:.2f}s fits before the "
                f"next cue — shorten the translation (§6 rung 1) or raise SpeechRate (rung 2)")

        cues.append({
            "id": line["id"], "speaker": line.get("speaker"), "source": source_text,
            "text": text, "lines": wrapped,
            "audio_start": round(start, 3),
            "sub_start": round(start, 3), "sub_end": round(end, 3),
        })
        srt.append(f"{line['id']}\n{srt_time(start)} --> {srt_time(end)}\n"
                   + "\n".join(wrapped) + "\n")

    widest = max((len(ln) for c in cues for ln in c["lines"]), default=0)
    print(f"[{args.lang}] {len(cues)} cues, widest line {widest}/{rules['max_chars_per_line']} chars, "
          f"dwell from {rules['reading_cps']} cps"
          + (", extended to cover measured dub" if dub else ""))
    for cue in cues:
        print(f"  #{cue['id']} {cue['sub_start']:7.2f}-{cue['sub_end']:7.2f}  {cue['text']}")

    if errors:
        print(f"\n{len(errors)} problem(s) — fix the translation, not the limits:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if args.out:
        json.dump(cues, open(args.out, "w"), ensure_ascii=False, indent=2)
        print(f"\ncues  -> {args.out}")
    if args.srt:
        open(args.srt, "w").write("\n".join(srt))
        print(f"srt   -> {args.srt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
