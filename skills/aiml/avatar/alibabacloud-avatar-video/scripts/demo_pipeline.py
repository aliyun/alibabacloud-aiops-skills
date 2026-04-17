#!/usr/bin/env python3
"""
Human Avatar Demo Pipeline

统一入口，调用本 Skill 的三个脚本：
- EMO: portrait_animate.py
- AA: animate_anyone.py
- 灵眸: avatar_video.py

示例：
  # EMO（本地图片+本地音频）
  python demo_pipeline.py --mode emo --image ./face.jpg --audio ./speech.mp3 --download

  # AA（URL）
  python demo_pipeline.py --mode aa --image-url https://... --video-url https://... --download

  # 灵眸（模板+文案）
  python demo_pipeline.py --mode lingmou --template-id BSxxxx --text "大家好" --download
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from input_validation import resolve_under_cwd, validate_http_https_url

ROOT = Path(__file__).resolve().parent


def run_cmd(cmd):
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        sys.exit(proc.returncode)


def build_emo_cmd(args):
    cmd = [sys.executable, str(ROOT / "portrait_animate.py")]
    if args.image_url:
        cmd += ["--image-url", args.image_url]
    if args.audio_url:
        cmd += ["--audio-url", args.audio_url]
    if args.image:
        cmd += ["--image", args.image]
    if args.audio:
        cmd += ["--audio", args.audio]
    cmd += ["--ratio", args.ratio, "--style-level", args.style_level, "--output", args.output]
    if args.download:
        cmd += ["--download"]
    return cmd


def build_aa_cmd(args):
    cmd = [sys.executable, str(ROOT / "animate_anyone.py")]
    if args.image_url:
        cmd += ["--image-url", args.image_url]
    if args.video_url:
        cmd += ["--video-url", args.video_url]
    if args.image:
        cmd += ["--image", args.image]
    if args.video:
        cmd += ["--video", args.video]
    cmd += ["--output", args.output]
    if args.download:
        cmd += ["--download"]
    return cmd


def build_lingmou_cmd(args):
    cmd = [
        sys.executable,
        str(ROOT / "avatar_video.py"),
        "--template-id",
        args.template_id,
        "--name",
        args.name,
        "--resolution",
        args.resolution,
        "--fps",
        str(args.fps),
        "--output",
        args.output,
    ]
    if args.watermark:
        cmd += ["--watermark"]
    if args.text_file:
        cmd += ["--text-file", args.text_file]
    else:
        cmd += ["--text", args.text]
    if args.download:
        cmd += ["--download"]
    return cmd


def validate_args(args):
    if args.download:
        resolve_under_cwd(args.output, field="--output")
    if args.mode == "emo":
        if not ((args.image_url or args.image) and (args.audio_url or args.audio)):
            raise SystemExit("EMO 需要 image(+url|file) 和 audio(+url|file)")
        if args.image_url:
            validate_http_https_url(args.image_url, field="--image-url")
        if args.audio_url:
            validate_http_https_url(args.audio_url, field="--audio-url")
    elif args.mode == "aa":
        if not ((args.image_url or args.image) and (args.video_url or args.video)):
            raise SystemExit("AA 需要 image(+url|file) 和 video(+url|file)")
        if args.image_url:
            validate_http_https_url(args.image_url, field="--image-url")
        if args.video_url:
            validate_http_https_url(args.video_url, field="--video-url")
    elif args.mode == "lingmou":
        if not args.template_id:
            raise SystemExit("灵眸模式必须提供 --template-id")
        if not (args.text or args.text_file):
            raise SystemExit("灵眸模式必须提供 --text 或 --text-file")


def print_env_hint(mode):
    print("\n[env-check]")
    if mode in ("emo", "aa"):
        print("- 需要 DASHSCOPE_API_KEY（北京地域）")
    if mode in ("emo", "aa") and not (os.getenv("DASHSCOPE_API_KEY")):
        print("  ! 未检测到 DASHSCOPE_API_KEY")
    if mode == "lingmou":
        print("- 需要 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        if not os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"):
            print("  ! 未检测到 ALIBABA_CLOUD_ACCESS_KEY_ID")
        if not os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET"):
            print("  ! 未检测到 ALIBABA_CLOUD_ACCESS_KEY_SECRET")


def main():
    p = argparse.ArgumentParser(description="Human Avatar Demo Pipeline")
    p.add_argument("--mode", required=True, choices=["emo", "aa", "lingmou"])

    # 通用
    p.add_argument("--download", action="store_true")
    p.add_argument("--output", default="demo_output.mp4")

    # EMO / AA 共用输入
    p.add_argument("--image-url")
    p.add_argument("--image")

    # EMO
    p.add_argument("--audio-url")
    p.add_argument("--audio")
    p.add_argument("--ratio", default="1:1", choices=["1:1", "3:4"])
    p.add_argument("--style-level", default="normal", choices=["normal", "calm", "active"])

    # AA
    p.add_argument("--video-url")
    p.add_argument("--video")

    # 灵眸
    p.add_argument("--template-id")
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.add_argument("--name", default="OpenClaw Avatar Video")
    p.add_argument("--resolution", default="720p", choices=["720p", "1080p"])
    p.add_argument("--fps", type=int, default=30, choices=[15, 30])
    p.add_argument("--watermark", action="store_true")

    args = p.parse_args()
    validate_args(args)
    print_env_hint(args.mode)

    if args.mode == "emo":
        cmd = build_emo_cmd(args)
    elif args.mode == "aa":
        cmd = build_aa_cmd(args)
    else:
        cmd = build_lingmou_cmd(args)

    run_cmd(cmd)


if __name__ == "__main__":
    main()
