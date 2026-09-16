#!/usr/bin/env python3
"""Normalize every analysis signal into one readable timeline: material_packed.md

The agent reads this instead of cross-referencing an ASR JSON, a WebVTT and a
silencedetect transcript by hand. Joining heterogeneous sources on a time axis
is arithmetic, and arithmetic across files is where an LLM slips; laying them
out on one axis turns it into reading.

Inputs (all optional except --asr):
  --asr      segments.json from `video_editor.py asr --json`
  --vtt      WebVTT URL or path from `video_editor.py snapshot --mode webvtt`
             → contributes tile/frame markers on the same axis
  --silence  output of `ffmpeg -af silencedetect ... 2>&1`
             → contributes real audio-energy gaps, which ASR cannot see

Usage (working files live in the scratch dir, never in the user's project —
SKILL.md Hard Rule 1; `-o` defaults there too):
    python pack_material.py --asr "${TMPDIR:-/tmp}/video-editor/s1/asr.json"
    python pack_material.py --asr "${TMPDIR:-/tmp}/video-editor/s1/asr.json" \
        --vtt "https://.../strip.vtt" \
        --silence "${TMPDIR:-/tmp}/video-editor/s1/silence.txt" --source-name ep01

Cached: re-running with identical inputs reuses the previous output unless
--force is given. Analysis of an unchanged source is an immutable result
(SKILL.md §2.3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

SENTENCE_FINAL_PUNCT = "，。？！、；,.?!;"

VTT_CUE = re.compile(
    r"(\d\d):(\d\d):(\d\d)\.(\d+)\s*-->\s*(\d\d):(\d\d):(\d\d)\.(\d+)\s*\n"
    r"\s*(\S+?)#xywh=(\d+),(\d+),(\d+),(\d+)"
)
SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")


def read_source(location: str) -> str:
    """Read a local path or an http(s) URL. Never writes the payload to disk."""
    if location.startswith(("http://", "https://")):
        # curl over subprocess keeps this dependency-free (no requests import)
        result = subprocess.run(
            ["curl", "-fsSL", "--max-time", "60", location],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise SystemExit(f"could not fetch {location[:80]}…: {result.stderr[:200]}")
        return result.stdout
    return Path(location).read_text(encoding="utf-8")


def parse_vtt(text: str) -> list[dict]:
    """Return [{start, end, tile, x, y, w, h}] from a snapshot WebVTT.

    Coordinates come from the file, never from the request parameters — the
    server rewrites them (references/17-snapshot-and-asr.md §2.3). The tile
    depicts the cue's START instant, not its midpoint (§2.4).
    """
    cues = []
    for m in VTT_CUE.finditer(text):
        g = m.groups()

        def secs(h, mi, s, ms):
            return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / (10 ** len(ms))

        cues.append({
            "start": secs(g[0], g[1], g[2], g[3]),
            "end": secs(g[4], g[5], g[6], g[7]),
            "tile": g[8],
            "x": int(g[9]), "y": int(g[10]), "w": int(g[11]), "h": int(g[12]),
        })
    return cues


def parse_silence(text: str) -> list[tuple[float, float]]:
    """Pair silence_start / silence_end lines from silencedetect output."""
    starts = [float(x) for x in SILENCE_START.findall(text)]
    ends = [float(x) for x in SILENCE_END.findall(text)]
    spans = []
    for i, start in enumerate(starts):
        end = ends[i] if i < len(ends) else None
        spans.append((start, end if end is not None else start))
    return spans


def load_asr(location: str) -> list[dict]:
    """Accept either `asr --json` output or a raw GetSmartHandleJob response."""
    data = json.loads(read_source(location))
    if isinstance(data, dict):
        raw = (data.get("JobResult") or {}).get("AiResult") or data.get("Output")
        if not raw:
            raise SystemExit("ASR input is a dict but carries no JobResult.AiResult")
        data = json.loads(raw)
    if not isinstance(data, list):
        raise SystemExit("ASR input must be a JSON array of segments")

    segments, prev_end = [], None
    for item in data:
        content = str(item.get("content", ""))
        start = float(item.get("from", 0.0))
        end = float(item.get("to", 0.0))
        segments.append({
            "content": content,
            "from": start,
            "to": end,
            "gap_before": None if prev_end is None else round(start - prev_end, 3),
            "sentence_end": content[-1:] in SENTENCE_FINAL_PUNCT,
        })
        prev_end = end
    return segments


def silence_at(spans: list[tuple[float, float]], start: float, end: float
               ) -> Optional[tuple[float, float]]:
    """The silence span overlapping [start, end], if any."""
    for s_start, s_end in spans:
        if s_start < end and s_end > start:
            return (s_start, s_end)
    return None


def build(
    segments: list[dict],
    cues: list[dict],
    silences: list[tuple[float, float]],
    source_name: str,
    gap_threshold: float,
) -> str:
    lines: list[str] = []
    total = segments[-1]["to"] if segments else 0.0
    cuttable = [
        i for i in range(1, len(segments))
        if segments[i - 1]["sentence_end"]
        and segments[i]["gap_before"] is not None
        and segments[i]["gap_before"] >= gap_threshold
    ]

    lines.append(f"# {source_name} — packed material")
    lines.append("")
    lines.append(f"- dialogue: **{len(segments)} segments**, last ends at {total:.2f}s")
    lines.append(f"- cuttable seams (trailing punctuation **and** gap >= "
                 f"{gap_threshold}s): **{len(cuttable)}** of {max(len(segments) - 1, 0)}")
    if cues:
        lines.append(f"- filmstrip: **{len(cues)} tiles** covering "
                     f"0–{cues[-1]['end']:.0f}s, {cues[0]['w']}x{cues[0]['h']} each, "
                     f"in `{cues[0]['tile']}`")
    else:
        lines.append("- filmstrip: none supplied")
    lines.append(f"- audio-energy silences: "
                 f"{len(silences) if silences else 'none supplied'}")
    lines.append("")
    lines.append(
        "Legend:\n"
        "- `CUT ` — safe seam: the previous segment closed a sentence, the gap "
        f"is >= {gap_threshold}s, **and** the audio really goes quiet there.\n"
        "- `CUT?` — the speech gap qualifies but the audio does **not** fall "
        "silent: ambient sound, music, or a tail bleeding across. Verify with "
        "`timeline_view.py` before cutting (references/18 §1.5).\n"
        "- `\u00b7` before the text — the segment does **not** end on punctuation, "
        "so `SentenceMaxLength` truncated it mid-sentence. Never cut after it, "
        "however wide the gap (references/17-snapshot-and-asr.md §1.5).\n"
        "- `~silence` — a real audio-energy gap from `silencedetect`. A clip "
        "`Out` follows the audio tail, not the speech gap and not the visual cut."
    )
    lines.append("")
    lines.append("```")

    cue_idx = 0
    for i, seg in enumerate(segments):
        # Emit any filmstrip tiles that fall before this segment starts
        while cue_idx < len(cues) and cues[cue_idx]["start"] <= seg["from"]:
            cue = cues[cue_idx]
            lines.append(
                f"  --- tile {cue_idx + 1:>3} @ {cue['start']:07.2f}s  "
                f"crop {cue['w']}x{cue['h']}+{cue['x']}+{cue['y']} ---"
            )
            cue_idx += 1

        gap = seg["gap_before"]
        if gap is None:
            gap_txt = " " * 12
        else:
            sil = silence_at(silences, segments[i - 1]["to"], seg["from"]) if i else None
            gap_txt = f"gap {gap:5.2f}" + ("~silence" if sil else "        ")

        prev_closed = segments[i - 1]["sentence_end"] if i else True
        qualifies = bool(i) and prev_closed and gap is not None and gap >= gap_threshold
        if not qualifies:
            mark = "    "
        elif not silences:
            mark = "CUT "          # no silence data — cannot confirm
        elif silence_at(silences, segments[i - 1]["to"], seg["from"]):
            mark = "CUT "          # speech gap AND real audio silence
        else:
            # Speech stopped but the audio did not: ambient sound, music or a
            # bleeding tail. Cutting here can still clip something (ref 12 §1).
            mark = "CUT?"
        punct = " " if seg["sentence_end"] else "\u00b7"  # · = mid-sentence fragment
        lines.append(
            f"  [{i:>3}] {seg['from']:>7.2f}-{seg['to']:<7.2f} {gap_txt} {mark} "
            f"{punct}{seg['content']}"
        )

    while cue_idx < len(cues):
        cue = cues[cue_idx]
        lines.append(
            f"  --- tile {cue_idx + 1:>3} @ {cue['start']:07.2f}s  "
            f"crop {cue['w']}x{cue['h']}+{cue['x']}+{cue['y']} ---"
        )
        cue_idx += 1

    lines.append("```")
    lines.append("")

    if cuttable:
        lines.append("## Cuttable seams")
        lines.append("")
        lines.append("| before segment | at | gap | audio silent? | closing line |")
        lines.append("|---|---|---|---|---|")
        for i in cuttable:
            if not silences:
                verdict = "unknown"
            elif silence_at(silences, segments[i - 1]["to"], segments[i]["from"]):
                verdict = "yes"
            else:
                verdict = "**no — verify**"
            lines.append(
                f"| [{i}] | {segments[i]['from']:.2f}s | "
                f"{segments[i]['gap_before']:.2f}s | {verdict} | "
                f"{segments[i - 1]['content']} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Merge ASR / WebVTT / silencedetect into one packed timeline"
    )
    ap.add_argument("--asr", required=True,
                    help="segments.json from `video_editor.py asr --json`, "
                         "or a raw GetSmartHandleJob response")
    ap.add_argument("--vtt", default=None, help="WebVTT URL or path")
    ap.add_argument("--silence", default=None,
                    help="File holding silencedetect output")
    ap.add_argument("--source-name", default="material")
    ap.add_argument("--gap-threshold", type=float, default=0.3)
    ap.add_argument("-o", "--output",
                    default=str(Path(tempfile.gettempdir()) / "video-editor"
                                / "material_packed.md"),
                    help="Defaults to the scratch dir — never the user's project")
    ap.add_argument("--force", action="store_true",
                    help="Rebuild even when the cached output matches the inputs")
    args = ap.parse_args()

    fingerprint = hashlib.sha256(
        "|".join(str(x) for x in (
            args.asr, args.vtt, args.silence, args.gap_threshold
        )).encode()
    ).hexdigest()[:16]

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stamp_path = out_path.with_suffix(out_path.suffix + ".fingerprint")
    if not args.force and out_path.exists() and stamp_path.exists():
        if stamp_path.read_text(encoding="utf-8").strip() == fingerprint:
            print(f"{out_path} is current for these inputs (--force to rebuild)")
            return

    segments = load_asr(args.asr)
    if not segments:
        raise SystemExit("no ASR segments — nothing to pack")
    cues = parse_vtt(read_source(args.vtt)) if args.vtt else []
    silences = parse_silence(read_source(args.silence)) if args.silence else []

    out_path.write_text(
        build(segments, cues, silences, args.source_name, args.gap_threshold),
        encoding="utf-8",
    )
    stamp_path.write_text(fingerprint + "\n", encoding="utf-8")

    print(f"{out_path}: {len(segments)} segments, {len(cues)} tiles, "
          f"{len(silences)} silences")
    if not cues:
        print("  no --vtt supplied; the filmstrip axis is missing")
    if not silences:
        print("  no --silence supplied; audio-energy tails are invisible — "
              "clip Out decisions rest on speech gaps alone (references/18 §1.5)")


if __name__ == "__main__":
    main()
