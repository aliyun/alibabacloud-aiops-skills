#!/usr/bin/env python3
"""
Output Verification Script — check a produced output with a multimodal model.

Two inputs, both cloud-side: the **whole video** URL, or **cloud snapshot frame
URLs**. The whole video hears audio and sees motion, which frames cannot, and it
tokenises every second — so frames come first, and frames come from the cloud
(`video_editor.py snapshot`, SKILL.md §9).

Nothing is downloaded and ffmpeg is never invoked: local frame extraction is
barred by SKILL.md Hard Rules 1–2. Pass signed https URLs for a private bucket.

Usage:
    python frame_qa.py --video https://bucket.oss-cn-shanghai.aliyuncs.com/out.mp4

    # Model reviews cloud frames — for an agent that cannot see images itself
    python frame_qa.py --frames "https://.../f-1.jpg" "https://.../f-2.jpg"

    # Ask about one specific aspect
    python frame_qa.py --video https://.../out.mp4 \
        --prompt "Are the subtitles clipped at the bottom?"

Requirements:
    No ffmpeg, no Alibaba Cloud SDK.

Environment:
    DASHSCOPE_API_KEY   Alibaba Cloud Model Studio (Bailian) API key. Required.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

DASHSCOPE_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_MODEL = "qwen-omni-turbo"

# Inline base64 is only safe for small files; larger ones need an OSS URL.
MAX_INLINE_VIDEO_MB = 10

FRAMES_PROMPT = """These are frames sampled from a produced video in chronological order.
Check the output quality and report:
1. Overall content: what the video shows, and how the key frames progress.
2. Broken frames: fully black, fully white, corrupted, badly blurred, misaligned.
3. Text and subtitles: present, legible, not clipped by the frame edge.
4. Consistency: whether style, aspect ratio and framing stay coherent.
5. A 1-10 quality score and a verdict on whether the video is deliverable.
State clearly if you find nothing wrong."""

FULL_VIDEO_PROMPT = """This is a produced video. Check its output quality and report:
1. Overall content and how it progresses over time.
2. Visual defects: broken/black frames, blur, misalignment, abrupt jumps.
3. Audio: whether narration/BGM is present, audible, and in sync with the visuals.
4. Text and subtitles: legible and correctly timed.
5. A 1-10 quality score and a verdict on whether the video is deliverable.
State clearly if you find nothing wrong."""


class QAError(Exception):
    """Verification could not be carried out."""


def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def call_model(content: list, model: str, api_key: str) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["text"],
        "stream": False,
    }
    request = urllib.request.Request(
        DASHSCOPE_ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:500]
        if exc.code in (401, 403):
            raise QAError(f"DASHSCOPE_API_KEY was rejected (HTTP {exc.code}): {detail}")
        raise QAError(f"Model call failed (HTTP {exc.code}): {detail}")
    except Exception as exc:
        raise QAError(f"Model call failed: {exc}")


def review_full_video(video: str, prompt: str, model: str, api_key: str) -> dict:
    """Send the whole video: a remote URL is passed through, a local file is inlined."""
    if is_url(video):
        url = video
    else:
        if not os.path.isfile(video):
            raise QAError(f"Video not found: {video}")
        size_mb = os.path.getsize(video) / 1024 / 1024
        if size_mb > MAX_INLINE_VIDEO_MB:
            raise QAError(
                f"The video is {size_mb:.1f} MB — too large to inline. Upload it to "
                "OSS and pass the signed URL, or verify with cloud snapshot frames "
                "(SKILL.md §9)."
            )
        with open(video, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode()
        url = f"data:video/mp4;base64,{encoded}"

    content = [{"type": "video_url", "video_url": {"url": url}},
               {"type": "text", "text": prompt}]
    return call_model(content, model, api_key)


def review_images(urls: list, prompt: str, model: str, api_key: str) -> dict:
    """Send cloud snapshot frames to the model as remote URLs — nothing is downloaded."""
    content = [{"type": "image_url", "image_url": {"url": url}} for url in urls]
    content.append({"type": "text", "text": prompt})
    return call_model(content, model, api_key)


def report(response: dict) -> None:
    print(response["choices"][0]["message"]["content"])
    usage = response.get("usage") or {}
    if usage:
        print(f"\n[frame_qa] tokens: {usage.get('total_tokens')} "
              f"(prompt {usage.get('prompt_tokens')}, "
              f"completion {usage.get('completion_tokens')})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a produced output with a multimodal model: the whole "
                    "video, or cloud snapshot frames passed as URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Whole-video check, including audio and motion
  python frame_qa.py --video https://.../out.mp4

  # Model reviews cloud snapshot frames — for an agent that cannot see images.
  # The URLs are the ones `video_editor.py snapshot-urls -j <job_id> -r <region>` prints.
  python frame_qa.py --frames "https://.../f-1.jpg" "https://.../f-2.jpg"

  # Ask about one specific aspect
  python frame_qa.py --video https://.../out.mp4 --prompt "Are the subtitles clipped at the bottom?"

Frames are never sampled locally — that is a cloud job (SKILL.md §9):
  python video_editor.py snapshot --mode normal -i <MediaId> -r <region> \\
      --time <ms> --count 12 --interval 5 -O "oss://<bucket>/qa/f-{Count}.jpg" --wait
        """,
    )
    parser.add_argument("--video", "-v",
                        help="http(s) URL (signed URL for private buckets), or a small local file")
    parser.add_argument("--frames", "-f", nargs="+", metavar="URL",
                        help="Signed snapshot frame URLs in chronological order "
                             "(`snapshot-urls`) — sent to the model as URLs, nothing "
                             "is downloaded")
    parser.add_argument("--mode", "-m", choices=["frames", "full"], default="full",
                        help="kept for old invocations; the input decides (--video / --frames)")
    parser.add_argument("--prompt", "-p", help="Custom review question")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Multimodal model (default {DEFAULT_MODEL})")

    args = parser.parse_args()
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()

    try:
        if bool(args.video) == bool(args.frames):
            raise QAError("pass either --video <url>, or --frames with signed "
                          "snapshot frame URLs")
        if args.mode == "frames" and not args.frames:
            raise QAError(
                "Local frame sampling is gone — it downloaded the video and ran "
                "ffmpeg on it (SKILL.md Hard Rules 1-2). Take frames from a cloud "
                "snapshot job (`video_editor.py snapshot --mode normal ... --time "
                "<ms>`, then `snapshot-urls`) and pass them as --frames, or read "
                "them yourself (SKILL.md §9)."
            )
        if not api_key:
            raise QAError(
                "Model review needs DASHSCOPE_API_KEY (SKILL.md §1.3). Without it, "
                "read the cloud snapshot frames yourself (SKILL.md §9)."
            )

        if args.frames:
            if not all(is_url(url) for url in args.frames):
                raise QAError(
                    "--frames takes signed https URLs from `snapshot-urls` — local "
                    "frame files are barred (SKILL.md Hard Rules 1-2)"
                )
            print(f"[frame_qa] reviewing {len(args.frames)} cloud frame(s) with {args.model}")
            report(review_images(args.frames, args.prompt or FRAMES_PROMPT,
                                 args.model, api_key))
            return 0

        print(f"[frame_qa] reviewing the whole video with {args.model}")
        report(review_full_video(args.video, args.prompt or FULL_VIDEO_PROMPT,
                                 args.model, api_key))
        return 0

    except QAError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
