#!/usr/bin/env python3
"""
LivePortrait 人像视频生成 — 两步流水线

SECURITY NOTES:
- subprocess: used ONLY to invoke system ffmpeg (audio/video format
  conversion). All arguments are constructed from user-supplied local
  file paths; no shell=True, no dynamic code execution.
- OSS credentials (ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET): read from env,
  used ONLY to upload media files to the user's own OSS bucket and
  generate time-limited signed GET URLs. Never logged or sent elsewhere.
- All API calls go to dashscope.aliyuncs.com (Alibaba Cloud official).
  Step 1: liveportrait-detect  图像检测（同步）
  Step 2: liveportrait         视频生成（异步）

输入：
  - 人像图片（jpeg/jpg/png/bmp/webp）
  - 音频文件（wav/mp3，<15MB，1s~3min）
    OR 视频文件（自动提取音频）

用法:
  python live_portrait.py --image ./portrait.jpg --audio ./speech.mp3 --download
  python live_portrait.py --image ./portrait.jpg --video ./speech.mp4 --download
  python live_portrait.py --image-url https://... --audio-url https://... --download
  python live_portrait.py --image ./portrait.jpg --audio ./speech.mp3 \\
      --template active --mouth-strength 1.2 --head-strength 0.8 --download
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import requests

from input_validation import (
    mk_temp_path_for_ffmpeg,
    resolve_under_cwd,
    validate_http_https_url,
)

BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com")
_OSS_SIGNED_URL_EXPIRES = int(os.environ.get("OSS_SIGNED_URL_EXPIRES", str(3 * 24 * 3600)))


# ── helpers ────────────────────────────────────────────────────────────────────

USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-avatar-video"


def _headers(async_mode: bool = False) -> dict:
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("DASHSCOPE_API_KEY not set")
    h = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if async_mode:
        h["X-DashScope-Async"] = "enable"
    return h


def _wait_task(task_id: str, interval: int = 5, max_wait: int = 600) -> dict:
    url = f"{BASE_URL}/api/v1/tasks/{task_id}"
    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = requests.get(url, headers=_headers(), timeout=30)
            r.raise_for_status()
            data = r.json()
            out = data.get("output", {})
            status = out.get("task_status", "UNKNOWN")
            elapsed = int(time.time() - start)
            print(f"  [{elapsed}s] status={status}")
            if status == "SUCCEEDED":
                return out
            if status in ("FAILED", "CANCELED", "UNKNOWN"):
                raise RuntimeError(f"Task failed: {json.dumps(data, ensure_ascii=False)}")
        except RuntimeError:
            raise
        except Exception as e:
            print(f"  [poll error] {e}")
        time.sleep(interval)
    raise TimeoutError(f"Task {task_id} timed out after {max_wait}s")


def _find_ffmpeg() -> str:
    for p in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if shutil.which(p):
            return p
    raise RuntimeError("ffmpeg not found. Install: apt install ffmpeg")


def upload_to_oss(local_path: str, expires: int = _OSS_SIGNED_URL_EXPIRES) -> str:
    """Upload local file to OSS, return signed GET URL (default 3 days)."""
    import oss2
    auth = oss2.Auth(
        os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
        os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
    )
    bucket_name = os.environ["OSS_BUCKET"]
    endpoint = os.environ.get("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
    endpoint = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
    bucket = oss2.Bucket(auth, f"https://{endpoint}", bucket_name)
    key = f"human-avatar/{Path(local_path).name}"
    print(f"[oss] uploading {Path(local_path).name} …")
    bucket.put_object_from_file(key, local_path)
    url = bucket.sign_url("GET", key, expires)
    print(f"[oss] signed_url ok ({expires // 3600}h)")
    return url


def convert_image(src: str) -> str:
    """Convert image to jpg if format not natively supported (e.g. heic)."""
    p = Path(src)
    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
        return src
    ff = _find_ffmpeg()
    dst = mk_temp_path_for_ffmpeg(".jpg", "lp_img_")
    subprocess.run([ff, "-y", "-i", src, "-q:v", "2", dst], check=True, capture_output=True)
    print(f"[convert] image {p.name} → {Path(dst).name}")
    return dst


def extract_audio_from_video(video_path: str) -> str:
    """
    Extract audio from video file to mp3.
    LivePortrait requires wav or mp3, <15MB, 1s~3min.
    """
    ff = _find_ffmpeg()
    dst = mk_temp_path_for_ffmpeg(".mp3", "lp_audio_")
    print(f"[ffmpeg] extracting audio from {Path(video_path).name} …")
    subprocess.run(
        [ff, "-y", "-i", video_path, "-vn",
         "-ar", "44100", "-ac", "1", "-b:a", "128k",
         "-t", "180",    # cap at 3min
         dst],
        check=True, capture_output=True
    )
    size_mb = Path(dst).stat().st_size / 1024 / 1024
    duration = float(subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "a:0",
         "-show_entries", "stream=duration", "-of", "csv=p=0", dst],
        capture_output=True, text=True
    ).stdout.strip() or "0")
    print(f"[ffmpeg] extracted: {Path(dst).name}  {size_mb:.1f}MB  {duration:.1f}s")
    if duration < 1:
        raise ValueError(f"Extracted audio is too short ({duration:.1f}s), minimum is 1s")
    if size_mb > 14.5:
        raise ValueError(f"Extracted audio is too large ({size_mb:.1f}MB), max 15MB")
    return dst


def convert_audio(src: str) -> str:
    """Convert audio to mp3 if not wav/mp3."""
    p = Path(src)
    if p.suffix.lower() in (".wav", ".mp3"):
        return src
    ff = _find_ffmpeg()
    dst = mk_temp_path_for_ffmpeg(".mp3", "lp_audio_")
    subprocess.run(
        [ff, "-y", "-i", src, "-vn", "-ar", "44100", "-ac", "1", "-b:a", "128k", dst],
        check=True, capture_output=True
    )
    print(f"[convert] audio {p.name} → {Path(dst).name}")
    return dst


# ── Step 1: detect ─────────────────────────────────────────────────────────────

def lp_detect(image_url: str) -> None:
    """
    POST /face-detect — check image meets LivePortrait requirements (sync).
    Raises ValueError if check fails.
    """
    print(f"\n[step1] liveportrait-detect …")
    r = requests.post(
        f"{BASE_URL}/api/v1/services/aigc/image2video/face-detect",
        headers=_headers(async_mode=False),
        json={"model": "liveportrait-detect", "input": {"image_url": image_url}},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    out = data.get("output", {})
    passed = out.get("pass", False)
    msg = out.get("message", "")
    if passed:
        print(f"  ✅ detect passed")
    else:
        raise ValueError(f"Image failed LivePortrait detect: {msg}")


# ── Step 2: generate ────────────────────────────────────────────────────────────

def lp_generate(
    image_url: str,
    audio_url: str,
    template_id: str = "normal",
    eye_move_freq: float = 0.5,
    video_fps: int = 24,
    mouth_move_strength: float = 1.0,
    paste_back: bool = True,
    head_move_strength: float = 0.7,
) -> str:
    """
    POST /video-synthesis/ — generate LivePortrait video (async).
    Returns video_url.
    """
    print(f"\n[step2] liveportrait generate  template={template_id}  fps={video_fps} …")
    payload = {
        "model": "liveportrait",
        "input": {
            "image_url": image_url,
            "audio_url": audio_url,
        },
        "parameters": {
            "template_id": template_id,
            "eye_move_freq": eye_move_freq,
            "video_fps": video_fps,
            "mouth_move_strength": mouth_move_strength,
            "paste_back": paste_back,
            "head_move_strength": head_move_strength,
        },
    }
    r = requests.post(
        f"{BASE_URL}/api/v1/services/aigc/image2video/video-synthesis/",
        headers=_headers(async_mode=True),
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id: {json.dumps(data, ensure_ascii=False)}")
    print(f"  task_id={task_id}")

    out = _wait_task(task_id, interval=5, max_wait=600)
    video_url = (out.get("results") or {}).get("video_url")
    if not video_url:
        raise RuntimeError(f"No video_url in result: {out}")
    duration = (out.get("usage") or {}).get("video_duration", "?")
    print(f"  ✅ video_url={video_url}  duration={duration}s")
    return video_url


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="LivePortrait: portrait image + audio/video → animated portrait video"
    )
    # image
    img_grp = p.add_mutually_exclusive_group()
    img_grp.add_argument("--image", help="本地图片（自动上传 OSS）")
    img_grp.add_argument("--image-url", help="图片公网 URL")

    # audio / video
    audio_grp = p.add_mutually_exclusive_group()
    audio_grp.add_argument("--audio", help="本地音频文件（wav/mp3，自动上传 OSS）")
    audio_grp.add_argument("--audio-url", help="音频公网 URL")
    audio_grp.add_argument("--video", help="本地视频文件，自动提取音频并上传 OSS")

    # generation params
    p.add_argument("--template", default="normal", choices=["normal", "calm", "active"],
                   help="动作模板：normal(默认)/calm(播报)/active(演唱)")
    p.add_argument("--eye-freq", type=float, default=0.5,
                   help="眨眼频率 0~1 (default: 0.5)")
    p.add_argument("--fps", type=int, default=24,
                   help="输出帧率 15~30 (default: 24)")
    p.add_argument("--mouth-strength", type=float, default=1.0,
                   help="嘴部动作幅度 0~1.5 (default: 1.0)")
    p.add_argument("--head-strength", type=float, default=0.7,
                   help="头部动作幅度 0~1 (default: 0.7)")
    p.add_argument("--no-paste-back", action="store_true",
                   help="仅输出人脸区域（不贴回原图）")
    p.add_argument("--skip-detect", action="store_true",
                   help="跳过图像检测步骤")

    p.add_argument("--download", action="store_true", help="下载生成的视频到本地")
    p.add_argument("--output", default="lp_output.mp4", help="输出文件名 (default: lp_output.mp4)")
    args = p.parse_args()

    tmp_files = []

    try:
        # ── image URL ──────────────────────────────────────────────────────
        image_url = args.image_url
        if image_url:
            image_url = validate_http_https_url(image_url, field="--image-url")
        if not image_url:
            if not args.image:
                p.error("需要 --image 或 --image-url")
            converted = convert_image(args.image)
            if converted != args.image:
                tmp_files.append(converted)
            image_url = upload_to_oss(converted)

        # ── audio URL ──────────────────────────────────────────────────────
        audio_url = args.audio_url
        if audio_url:
            audio_url = validate_http_https_url(audio_url, field="--audio-url")
        if not audio_url:
            if args.video:
                extracted = extract_audio_from_video(args.video)
                tmp_files.append(extracted)
                audio_url = upload_to_oss(extracted)
            elif args.audio:
                converted_audio = convert_audio(args.audio)
                if converted_audio != args.audio:
                    tmp_files.append(converted_audio)
                audio_url = upload_to_oss(converted_audio)
            else:
                p.error("需要 --audio, --audio-url 或 --video 之一")

        # ── Step 1: detect ─────────────────────────────────────────────────
        if not args.skip_detect:
            lp_detect(image_url)

        # ── Step 2: generate ───────────────────────────────────────────────
        video_url = lp_generate(
            image_url=image_url,
            audio_url=audio_url,
            template_id=args.template,
            eye_move_freq=args.eye_freq,
            video_fps=args.fps,
            mouth_move_strength=args.mouth_strength,
            paste_back=not args.no_paste_back,
            head_move_strength=args.head_strength,
        )

        print(f"\n✅ Done! video_url = {video_url}")

        if args.download:
            out_path = resolve_under_cwd(args.output, field="--output")
            safe_url = validate_http_https_url(video_url, field="result video URL")
            print(f"Downloading → {out_path} …")
            with urllib.request.urlopen(safe_url, timeout=300) as response:
                with open(out_path, 'wb') as f:
                    f.write(response.read())
            size_kb = out_path.stat().st_size // 1024
            print(f"Saved {out_path} ({size_kb}KB)")

    finally:
        for f in tmp_files:
            try:
                os.unlink(f)
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
