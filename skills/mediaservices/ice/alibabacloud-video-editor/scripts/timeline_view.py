#!/usr/bin/env python3
"""Composite a filmstrip + audio waveform on ONE shared time axis.

The filmstrip comes from a cloud snapshot (`video_editor.py snapshot --mode
webvtt`), and the tile coordinates come from that job's WebVTT — never from the
request parameters, which the server rewrites (references/17 §2.3). The
waveform is the one thing no ICE API returns, so ffmpeg reads it straight from
an https URL; ffmpeg also crops the sprite tiles and stacks the two rows. That
makes a chart, not media — the single exception SKILL.md Hard Rule 2 allows.
Nothing is downloaded except the tile image and the output PNG.

Why one image: frames show picture, a waveform shows whether a line has
finished speaking. Dialogue audio routinely bridges a visual cut, and that is
the failure a filmstrip alone cannot see (references/18 §1.5). Stacking them on a
shared axis turns the arithmetic of correlating two analyses into looking.

This is a drill-down, not a scan tool. Point it at a decision — a seam, an
ambiguous pause — not at every second of the source.

Outputs default to the scratch dir, never the user's project (SKILL.md Hard
Rule 1).

Usage:
    # One window
    python timeline_view.py --vtt "https://.../strip.vtt" --range 12 24 \
        --audio "https://.../ep01.mp4" -o "${TMPDIR:-/tmp}/video-editor/seam.png"

    # One image per EDL seam, +/- 1.5s
    python timeline_view.py --vtt "https://.../strip.vtt" --seams edl.json \
        --audio "https://.../ep01.mp4"
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

VTT_CUE = re.compile(
    r"(\d\d):(\d\d):(\d\d)\.(\d+)\s*-->\s*(\d\d):(\d\d):(\d\d)\.(\d+)\s*\n"
    r"\s*(\S+?)#xywh=(\d+),(\d+),(\d+),(\d+)"
)

WAVE_HEIGHT = 220
WAVE_COLOR = "0x8CB4FF"

# Working files stay out of the user's project (SKILL.md Hard Rule 1).
SCRATCH = Path(tempfile.gettempdir()) / "video-editor"


def need(tool: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(f"{tool} not found on PATH. macOS: brew install ffmpeg")


def fetch(location: str, dest: Path) -> Path:
    """Fetch a URL to dest, or return the local path unchanged."""
    if not location.startswith(("http://", "https://")):
        return Path(location)
    need("curl")
    result = subprocess.run(
        ["curl", "-fsSL", "--max-time", "120", "-o", str(dest), location],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"could not fetch {location[:90]}…: {result.stderr[:200]}")
    return dest


def read_text_source(location: str, tmp: Path) -> str:
    return fetch(location, tmp / "in.vtt").read_text(encoding="utf-8")


def parse_vtt(text: str) -> list[dict]:
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
    if not cues:
        sys.exit("no #xywh cues found — is this a snapshot WebVTT?")
    return cues


def resolve_tile(vtt_location: str, relative: str, explicit: Optional[str]) -> str:
    """Turn the VTT's relative tile reference into something fetchable.

    A signed VTT URL carries a query string; the tile needs its own signature,
    so a signed URL cannot simply be rebased. Ask for --tile in that case.
    """
    if explicit:
        return explicit
    if not vtt_location.startswith(("http://", "https://")):
        return str(Path(vtt_location).parent / relative)
    parts = urlparse(vtt_location)
    if parts.query:
        sys.exit(
            "the VTT URL is signed, so the tile URL cannot be derived from it "
            "(the tile needs its own signature). Pass --tile with the URL from "
            "`snapshot-urls` (SnapshotUrls[0])."
        )
    return urljoin(urlunparse(parts), relative)


def crop_tiles(tile: Path, cues: list[dict], tmp: Path) -> list[Path]:
    paths = []
    for i, cue in enumerate(cues):
        out = tmp / f"t{i:03d}.png"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", str(tile),
            "-vf", f"crop={cue['w']}:{cue['h']}:{cue['x']}:{cue['y']}", str(out),
        ], check=True)
        paths.append(out)
    return paths


def hstack(paths: list[Path], out: Path) -> None:
    if len(paths) == 1:
        shutil.copy(paths[0], out)
        return
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in paths:
        cmd += ["-i", str(p)]
    cmd += ["-filter_complex", f"hstack=inputs={len(paths)}", str(out)]
    subprocess.run(cmd, check=True)


def waveform(audio: str, start: float, duration: float, width: int,
             out: Path) -> bool:
    """Render an RMS waveform for [start, start+duration). Streams over HTTP."""
    result = subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", audio,
        "-filter_complex",
        f"showwavespic=s={width}x{WAVE_HEIGHT}:colors={WAVE_COLOR}:split_channels=0",
        "-frames:v", "1", str(out),
    ], capture_output=True, text=True)
    if result.returncode != 0 or not out.exists():
        print(f"  waveform failed ({result.stderr.strip()[:160]}) — "
              f"filmstrip only", file=sys.stderr)
        return False
    return True


def vstack(top: Path, bottom: Path, out: Path) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(top), "-i", str(bottom),
        "-filter_complex", "vstack=inputs=2", str(out),
    ], check=True)


def render(vtt_location: str, cues: list[dict], tile_ref: str,
           start: float, end: float, audio: Optional[str], out: Path) -> bool:
    selected = [c for c in cues if c["start"] < end and c["end"] > start]
    if not selected:
        print(f"  no tiles cover {start:.2f}–{end:.2f}s (strip spans "
              f"{cues[0]['start']:.0f}–{cues[-1]['end']:.0f}s)", file=sys.stderr)
        return False

    # The filmstrip axis is quantized to the snapshot Interval, so the waveform
    # must span the tiles' own range — not the requested one — or the two rows
    # would not line up.
    axis_start, axis_end = selected[0]["start"], selected[-1]["end"]
    width = sum(c["w"] for c in selected)

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        tile = fetch(tile_ref, tmp / "tile.jpg")
        strip = tmp / "strip.png"
        hstack(crop_tiles(tile, selected, tmp), strip)

        if audio:
            wave = tmp / "wave.png"
            if waveform(audio, axis_start, axis_end - axis_start, width, wave):
                vstack(strip, wave, out)
            else:
                shutil.copy(strip, out)
        else:
            shutil.copy(strip, out)

    print(f"{out}")
    print(f"  axis {axis_start:.2f}–{axis_end:.2f}s over {width}px "
          f"({len(selected)} tiles x {selected[0]['w']}px)")
    print(f"  x -> time: t = {axis_start:.2f} + x / {width} * "
          f"{axis_end - axis_start:.2f}")
    for i, c in enumerate(selected):
        print(f"    x {i * c['w']:>5}–{(i + 1) * c['w']:<5} = {c['start']:>7.2f}s")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Filmstrip + waveform on one shared time axis")
    ap.add_argument("--vtt", required=True, help="Snapshot WebVTT URL or path")
    ap.add_argument("--tile", default=None,
                    help="Tile image URL or path. Required when the VTT URL is "
                         "signed — use SnapshotUrls[0] from `snapshot-urls`")
    ap.add_argument("--audio", default=None,
                    help="Audio or video URL for the waveform row. Prefer an "
                         "audio-only track: an mp4 interleaves audio with video, "
                         "so a whole-file pass pulls the whole file")
    ap.add_argument("--range", nargs=2, type=float, metavar=("START", "END"),
                    default=None, help="Time window in seconds")
    ap.add_argument("--seams", default=None,
                    help="edl.json — render one image per seam between ranges")
    ap.add_argument("--seam-window", type=float, default=1.5,
                    help="Seconds either side of a seam (default: 1.5)")
    ap.add_argument("-o", "--output", default=str(SCRATCH / "timeline_view.png"),
                    help="Defaults to the scratch dir — never the user's project")
    ap.add_argument("--out-dir", default=str(SCRATCH / "verify"),
                    help="Destination directory in --seams mode "
                         "(defaults to the scratch dir)")
    args = ap.parse_args()

    need("ffmpeg")
    if not args.range and not args.seams:
        sys.exit("pass --range START END, or --seams edl.json")

    with tempfile.TemporaryDirectory() as td:
        vtt_text = read_text_source(args.vtt, Path(td))
    cues = parse_vtt(vtt_text)
    tile_ref = resolve_tile(args.vtt, cues[0]["tile"], args.tile)

    if args.range:
        ok = render(args.vtt, cues, tile_ref, args.range[0], args.range[1],
                    args.audio, Path(args.output))
        sys.exit(0 if ok else 1)

    edl = json.loads(Path(args.seams).read_text(encoding="utf-8"))
    ranges = edl.get("ranges") or []
    if len(ranges) < 2:
        sys.exit("an EDL with fewer than 2 ranges has no seams")

    out_dir = Path(args.out_dir)
    made = 0
    # Seam k sits between ranges[k-1].out and ranges[k].in. Both sides matter:
    # the outgoing tail must be complete and the incoming head must not leak
    # the previous shot (references/18 §1.5).
    for k in range(1, len(ranges)):
        for label, moment in (
            (f"seam{k:02d}a-out", float(ranges[k - 1]["out"])),
            (f"seam{k:02d}b-in", float(ranges[k]["in"])),
        ):
            render(args.vtt, cues, tile_ref,
                   max(0.0, moment - args.seam_window), moment + args.seam_window,
                   args.audio, out_dir / f"{label}.png")
            made += 1
    print(f"\n{made} image(s) in {out_dir} for {len(ranges) - 1} seam(s)")
    print("At each seam check: the outgoing frame shows a completed line or no "
          "subtitle, the waveform has fallen quiet before the cut, and the "
          "incoming frame carries no residue of the previous shot.")


if __name__ == "__main__":
    main()
