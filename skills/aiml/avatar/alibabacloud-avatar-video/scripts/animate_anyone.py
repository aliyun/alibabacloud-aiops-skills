#!/usr/bin/env python3
"""
AnimateAnyone Gen2 — 三步流水线

SECURITY NOTES:
- subprocess: used ONLY to invoke system ffmpeg for video/image format
  conversion (e.g. webm→mp4, heic→jpg). No shell=True, no eval/exec.
- OSS credentials: read from environment variables, used ONLY to upload
  user media to their own OSS bucket. Never transmitted to third parties.
- All API calls target dashscope.aliyuncs.com (Alibaba Cloud official).
  Step 1: animate-anyone-detect-gen2   图像检测（同步）
  Step 2: animate-anyone-template-gen2 动作模板生成（异步，得到 template_id）
  Step 3: animate-anyone-gen2          视频生成（异步，得到 video_url）

支持多种输入格式，通过 ffmpeg 自动转换：
  图片: webp/heic/tif/bmp → jpg
  视频: webm/avi/mov/mkv/flv → mp4 (H.264, ≥24fps)

用法:
  python animate_anyone.py --image ./face.jpg --video ./dance.webm --download
  python animate_anyone.py --image-url https://... --video-url https://... --download
  python animate_anyone.py --image ./face.jpg --template-id AACT.xxx --download  # 跳过模板生成
"""

import argparse
import json
import os
import re
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

# ── ffmpeg helpers ─────────────────────────────────────────────────────────────

def _find_ffmpeg() -> str:
    """Find ffmpeg in PATH or common install locations."""
    for p in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if shutil.which(p):
            return p
    raise RuntimeError("ffmpeg not found. Install: apt install ffmpeg / brew install ffmpeg")


def convert_image(src: str) -> str:
    """
    Convert image to jpg if not already jpg/jpeg/png.
    Returns path to (possibly new) file. Temp files are tracked for cleanup.
    """
    p = Path(src)
    if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
        return src
    ff = _find_ffmpeg()
    dst = mk_temp_path_for_ffmpeg(".jpg", "aa_img_")
    subprocess.run([ff, "-y", "-i", src, "-q:v", "2", dst],
                   check=True, capture_output=True)
    print(f"[convert] {p.name} → {Path(dst).name}")
    return dst


def convert_video(src: str) -> str:
    """
    Convert video to mp4 (H.264) with ≥24fps if not already compatible.
    Returns path to (possibly new) file.
    Requirements: mp4/avi/mov, H.264 or H.265, fps≥24, bitrate reasonable.
    """
    p = Path(src)
    # probe fps
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,r_frame_rate,width,height",
         "-of", "json", src],
        capture_output=True, text=True
    )
    codec, fps_num, fps_den = "unknown", 25, 1
    try:
        info = json.loads(probe.stdout)
        stream = info.get("streams", [{}])[0]
        codec = stream.get("codec_name", "unknown")
        fr = stream.get("r_frame_rate", "25/1").split("/")
        fps_num, fps_den = int(fr[0]), max(int(fr[1]), 1)
    except Exception:
        pass
    fps = fps_num / fps_den

    need_convert = (
        p.suffix.lower() not in (".mp4", ".avi", ".mov")
        or codec not in ("h264", "hevc", "h265")
        or fps < 24
    )
    if not need_convert:
        return src

    ff = _find_ffmpeg()
    dst = mk_temp_path_for_ffmpeg(".mp4", "aa_vid_")
    # ensure ≥24fps, H.264
    vf = f"fps=max(fps\\,24)" if fps < 24 else None
    cmd = [ff, "-y", "-i", src, "-c:v", "libx264", "-preset", "fast",
           "-crf", "22", "-c:a", "aac", "-movflags", "+faststart"]
    if vf:
        cmd += ["-vf", f"fps=24"]
    cmd.append(dst)
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[convert] {p.name} → {Path(dst).name}  codec={codec} fps={fps:.1f}→converted")
    return dst


# ── OSS upload ─────────────────────────────────────────────────────────────────

def upload_to_oss(local_path: str, expires: int = _OSS_SIGNED_URL_EXPIRES) -> str:
    """Upload file to OSS and return signed GET URL (default 3 days)."""
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
    print(f"[oss] signed_url ok ({expires//3600}h)")
    return url


# ── DashScope helpers ──────────────────────────────────────────────────────────

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


def wait_task(task_id: str, interval: int = 10, max_wait: int = 1800) -> dict:
    """Poll until task SUCCEEDED/FAILED, return full output dict."""
    url = f"{BASE_URL}/api/v1/tasks/{task_id}"
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(url, headers=_headers(), timeout=60)
        r.raise_for_status()
        data = r.json()
        out = data.get("output", {})
        status = out.get("task_status", "UNKNOWN")
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] task_id={task_id[:16]}… status={status}")
        if status == "SUCCEEDED":
            return out
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise RuntimeError(f"Task failed: {json.dumps(data, ensure_ascii=False)}")
        time.sleep(interval)
    raise TimeoutError(f"Task {task_id} timed out after {max_wait}s")


# ── Step 1: Image detect ───────────────────────────────────────────────────────

def aa_detect(image_url: str) -> dict:
    """
    POST /aa-detect — 检测图像是否符合 AA 要求（同步）。
    Returns output dict with check_pass, bodystyle.
    """
    print(f"\n[step1] aa-detect …")
    r = requests.post(
        f"{BASE_URL}/api/v1/services/aigc/image2video/aa-detect",
        headers=_headers(async_mode=False),
        json={"model": "animate-anyone-detect-gen2", "input": {"image_url": image_url}},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    out = data.get("output", {})
    check_pass = out.get("check_pass", False)
    bodystyle = out.get("bodystyle", "")
    reason = out.get("reason", "")
    if check_pass:
        print(f"  ✅ detect passed  bodystyle={bodystyle}")
    else:
        print(f"  ❌ detect FAILED  reason={reason}")
        raise ValueError(f"Image failed AA detect: {reason}")
    return out


# ── Step 2: Template generation ────────────────────────────────────────────────

def aa_template(video_url: str) -> str:
    """
    POST /aa-template-generation/ — 从视频提取动作模板（异步）。
    Returns template_id str.
    """
    print(f"\n[step2] aa-template-generation …")
    r = requests.post(
        f"{BASE_URL}/api/v1/services/aigc/image2video/aa-template-generation/",
        headers=_headers(async_mode=True),
        json={"model": "animate-anyone-template-gen2", "input": {"video_url": video_url}},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in template response: {json.dumps(data, ensure_ascii=False)}")
    print(f"  task_id={task_id}")
    out = wait_task(task_id, interval=10)
    template_id = out.get("template_id")
    if not template_id:
        raise RuntimeError(f"No template_id in result: {out}")
    duration = (out.get("usage") or {}).get("video_duration", "?")
    print(f"  ✅ template_id={template_id}  duration={duration}s")
    return template_id


# ── Step 3: Video generation ────────────────────────────────────────────────────

def aa_generate(image_url: str, template_id: str,
                use_ref_img_bg: bool = False, video_ratio: str = "9:16") -> str:
    """
    POST /video-synthesis/ — 基于图像 + 动作模板生成视频（异步）。
    Returns video_url str.
    """
    print(f"\n[step3] aa-generate  use_ref_img_bg={use_ref_img_bg}  video_ratio={video_ratio} …")
    payload = {
        "model": "animate-anyone-gen2",
        "input": {"image_url": image_url, "template_id": template_id},
        "parameters": {"use_ref_img_bg": use_ref_img_bg, "video_ratio": video_ratio},
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
        raise RuntimeError(f"No task_id in generate response: {json.dumps(data, ensure_ascii=False)}")
    print(f"  task_id={task_id}")
    out = wait_task(task_id, interval=15, max_wait=1800)
    video_url = out.get("video_url")
    if not video_url:
        raise RuntimeError(f"No video_url in result: {out}")
    print(f"  ✅ video_url={video_url}")
    return video_url


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="AnimateAnyone Gen2: image+video → animated video (3-step pipeline)"
    )
    p.add_argument("--image-url", help="图片公网 URL（已上传 OSS 等）")
    p.add_argument("--video-url", help="动作视频公网 URL（已上传 OSS 等）")
    p.add_argument("--image", help="本地图片路径（自动转换格式并上传 OSS）")
    p.add_argument("--video", help="本地动作视频路径（自动转换格式并上传 OSS）")
    p.add_argument("--template-id", help="已有 template_id，跳过 Step 2")
    p.add_argument("--use-ref-img-bg", action="store_true",
                   help="以输入图片为背景生成（默认用视频背景）")
    p.add_argument("--video-ratio", default="9:16", choices=["9:16", "3:4"],
                   help="视频画幅（use_ref_img_bg=true 时有效）")
    p.add_argument("--download", action="store_true", help="下载输出视频")
    p.add_argument("--output", default="aa_output.mp4", help="输出文件名")
    p.add_argument("--skip-detect", action="store_true", help="跳过图像检测步骤")
    args = p.parse_args()

    _AA_TEMPLATE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,256}$")

    tmp_files = []

    try:
        # ── prepare image URL ──────────────────────────────────────────────
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

        # ── prepare video URL ──────────────────────────────────────────────
        video_url = args.video_url
        if video_url:
            video_url = validate_http_https_url(video_url, field="--video-url")
        if args.template_id and not _AA_TEMPLATE_ID_RE.fullmatch(args.template_id.strip()):
            raise ValueError(f"Invalid --template-id format: {args.template_id!r}")
        if not video_url and not args.template_id:
            if not args.video:
                p.error("需要 --video 或 --video-url 或 --template-id")
            converted = convert_video(args.video)
            if converted != args.video:
                tmp_files.append(converted)
            video_url = upload_to_oss(converted)

        # ── Step 1: detect ─────────────────────────────────────────────────
        if not args.skip_detect:
            aa_detect(image_url)

        # ── Step 2: template ───────────────────────────────────────────────
        template_id = args.template_id
        if not template_id:
            template_id = aa_template(video_url)

        # ── Step 3: generate ───────────────────────────────────────────────
        final_url = aa_generate(
            image_url, template_id,
            use_ref_img_bg=args.use_ref_img_bg,
            video_ratio=args.video_ratio,
        )

        print(f"\n✅ Done! video_url = {final_url}")

        if args.download:
            out_path = resolve_under_cwd(args.output, field="--output")
            safe_url = validate_http_https_url(final_url, field="result video URL")
            print(f"Downloading → {out_path} …")
            with urllib.request.urlopen(safe_url, timeout=300) as response:
                with open(out_path, 'wb') as f:
                    f.write(response.read())
            size = out_path.stat().st_size
            print(f"Saved {out_path} ({size//1024}KB)")

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
