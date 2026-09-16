#!/usr/bin/env python3
"""Bailian qwen3.5-omni segmentation — capability-maximizing extraction.

Two passes per video, matching the model's strengths:
  shots: fps=2 visual pass -> frame-precise cut points
  lines: audio-focused pass -> speech-precise dialogue timeline
Usage: omni_segment.py <video-url-or-path> <out.json> <shots|lines|full> [fps]
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = os.environ.get("OMNI_MODEL", "qwen3.5-omni-plus")

PROMPT_SHOTS = """You are a professional editor doing visual shot segmentation only (ignore the audio).
Compare frames one by one and find the exact moment of every shot change (hard cut), to 0.1 s.
Output pure JSON only: {"cuts":[0.0,6.1,8.4,...]}
Rules: cuts is the ascending list of cut moments (including 0.0); miss no cut, and never report motion within one shot as a cut."""

PROMPT_LINES = """You are a professional dialogue proofreader. Listen to the audio and check it against the on-screen subtitles; output the precise timeline of every spoken line.
start is the moment the first character of the line is voiced, end the moment the last character finishes, both to 0.1 s; text must match the on-screen subtitles character for character; speaker is an appearance description (e.g. "man in green jacket").
Output pure JSON only: {"lines":[{"start":0.0,"end":2.3,"text":"...","speaker":"..."}]}
Rules: the pause between two lines must not be merged into either line; record overlapping dialogue separately."""

PROMPT_FULL = """You are a professional editor doing visual shot segmentation and dialogue proofreading in one pass.
Output pure JSON only: {"shots":[{"start":0.0,"end":6.1,"desc":"one-sentence description of the picture"}],"lines":[{"start":0.0,"end":2.3,"text":"the spoken line verbatim","speaker":"appearance description"}]}
Rules:
1. Split shots at shot changes (hard cuts) covering the whole video; timestamps to 0.1 s; miss no cut; never report motion within one shot as a cut;
2. lines start/end are the voicing start/finish moments to 0.1 s; text matches the on-screen subtitles character for character; pauses are not merged into any line; record overlapping dialogue separately;
3. Shot spans with no dialogue do not enter lines."""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="qwen3.5-omni shot/dialogue segmentation (references/17-snapshot-and-asr.md §1.6).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Requires DASHSCOPE_API_KEY. Override the model with OMNI_MODEL.",
    )
    parser.add_argument("video", help="video https URL, or a local file path (inlined as base64)")
    parser.add_argument("out", help="output path for the model's JSON response")
    parser.add_argument(
        "mode", choices=["shots", "lines", "full"],
        help="shots = visual cut points; lines = dialogue timeline; full = both")
    parser.add_argument(
        "fps", nargs="?", type=float, default=None,
        help="sampling frame rate (default: 2.0 for shots, 1.0 otherwise)")
    args = parser.parse_args()

    video, out_path, mode = args.video, args.out, args.mode
    fps = args.fps if args.fps is not None else (2.0 if mode == "shots" else 1.0)
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        print(
            "DASHSCOPE_API_KEY missing — omni segmentation unavailable.\n"
            "Fallback (references/17-snapshot-and-asr.md §1.6 'No omni'):\n"
            "  cuts    : ffmpeg scene detection (step 3) is the cut ground truth anyway\n"
            "  dialogue: ICE SubmitASRJob (step 0a) is the primary dialogue timeline\n"
            "  ties    : read subtitle-band strips / filmstrip with your own vision (step 5)",
            file=sys.stderr)
        sys.exit(1)
    if video.startswith("http"):
        url = video
    else:
        with open(video, "rb") as fh:
            url = f"data:video/mp4;base64,{base64.b64encode(fh.read()).decode()}"
    video_part = {"type": "video_url", "video_url": {"url": url, "fps": fps}}
    prompt = {"shots": PROMPT_SHOTS, "lines": PROMPT_LINES, "full": PROMPT_FULL}[mode]
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [video_part, {"type": "text", "text": prompt}]}],
        "modalities": ["text"],
        "stream": False,
    }
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()[:800]}", file=sys.stderr)
        sys.exit(1)
    with open(out_path, "w") as fh:
        fh.write(data["choices"][0]["message"]["content"])
    print(f"[omni_segment:{mode}@{fps}fps] saved {out_path}")


if __name__ == "__main__":
    main()
