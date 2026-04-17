#!/usr/bin/env python3
"""EMO 口播视频（DashScope）
流程：face-detect -> video-synthesis -> 轮询 tasks/{task_id}
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import requests

from input_validation import resolve_under_cwd, validate_http_https_url

BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com")


USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-avatar-video"


def _headers(async_mode: bool = False):
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("Missing DASHSCOPE_API_KEY")
    h = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if async_mode:
        h["X-DashScope-Async"] = "enable"
    return h


_OSS_SIGNED_URL_EXPIRES = int(os.environ.get("OSS_SIGNED_URL_EXPIRES", str(3 * 24 * 3600)))  # 默认 3 天


def upload_to_oss(local_path: str, expires: int = _OSS_SIGNED_URL_EXPIRES) -> str:
    """上传文件到 OSS，返回签名 URL（私有 bucket）。有效期默认 3 天。"""
    import oss2

    auth = oss2.Auth(
        os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
        os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
    )
    bucket_name = os.environ["OSS_BUCKET"]
    endpoint = os.environ.get("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
    # normalize: strip any existing scheme prefix to avoid double https://
    endpoint = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
    bucket = oss2.Bucket(auth, f"https://{endpoint}", bucket_name)
    key = f"human-avatar/{Path(local_path).name}"
    bucket.put_object_from_file(key, local_path)
    # 签名 URL，DashScope 可直接下载，过期时间默认 3 天
    signed_url = bucket.sign_url("GET", key, expires)
    return signed_url


def emo_detect(image_url: str, ratio: str = "1:1"):
    url = f"{BASE_URL}/api/v1/services/aigc/image2video/face-detect"
    payload = {
        "model": "emo-detect-v1",
        "input": {"image_url": image_url},
        "parameters": {"ratio": ratio},
    }
    r = requests.post(url, headers=_headers(), json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    out = data.get("output", {})
    if not out.get("check_pass"):
        raise RuntimeError(f"EMO detect failed: {out.get('message', out)}")
    return out["face_bbox"], out["ext_bbox"]


def emo_submit(image_url: str, audio_url: str, face_bbox, ext_bbox, style_level: str = "normal"):
    url = f"{BASE_URL}/api/v1/services/aigc/image2video/video-synthesis"
    payload = {
        "model": "emo-v1",
        "input": {
            "image_url": image_url,
            "audio_url": audio_url,
            "face_bbox": face_bbox,
            "ext_bbox": ext_bbox,
        },
        "parameters": {"style_level": style_level},
    }
    r = requests.post(url, headers=_headers(async_mode=True), json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {json.dumps(data, ensure_ascii=False)}")
    return task_id


def wait_task(task_id: str, interval: int = 15, max_wait: int = 1800):
    url = f"{BASE_URL}/api/v1/tasks/{task_id}"
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(url, headers=_headers(), timeout=60)
        r.raise_for_status()
        data = r.json()
        status = data.get("output", {}).get("task_status")
        print(f"status={status}")
        if status == "SUCCEEDED":
            return data.get("output", {}).get("results", {}).get("video_url")
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise RuntimeError(json.dumps(data, ensure_ascii=False))
        time.sleep(interval)
    raise TimeoutError("Task timeout")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image-url")
    p.add_argument("--audio-url")
    p.add_argument("--image")
    p.add_argument("--audio")
    p.add_argument("--ratio", default="1:1", choices=["1:1", "3:4"])
    p.add_argument("--style-level", default="normal", choices=["normal", "calm", "active"])
    p.add_argument("--download", action="store_true")
    p.add_argument("--output", default="emo_output.mp4")
    args = p.parse_args()

    image_url = args.image_url
    if image_url:
        image_url = validate_http_https_url(image_url, field="--image-url")
    elif args.image:
        image_url = upload_to_oss(args.image)
    audio_url = args.audio_url
    if audio_url:
        audio_url = validate_http_https_url(audio_url, field="--audio-url")
    elif args.audio:
        audio_url = upload_to_oss(args.audio)
    if not image_url or not audio_url:
        p.error("Need --image-url/--image and --audio-url/--audio")

    face_bbox, ext_bbox = emo_detect(image_url, ratio=args.ratio)
    task_id = emo_submit(image_url, audio_url, face_bbox, ext_bbox, style_level=args.style_level)
    print(f"task_id={task_id}")
    video_url = wait_task(task_id)
    print(f"video_url={video_url}")

    if args.download and video_url:
        out_path = resolve_under_cwd(args.output, field="--output")
        safe_url = validate_http_https_url(video_url, field="result video URL")
        with urllib.request.urlopen(safe_url, timeout=300) as response:
            with open(out_path, 'wb') as f:
                f.write(response.read())
        print(f"saved={out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
