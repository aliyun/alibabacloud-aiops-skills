#!/usr/bin/env python3
"""
万相文生图 V2 (wan2.x-t2i)
默认模型：wan2.2-t2i-flash

用法:
  python text_to_image.py --prompt "一位优雅的女性站在樱花树下" --download
  python text_to_image.py --prompt "..." --model wan2.6-t2i --size 960*1696 --n 1
  python text_to_image.py --prompt "..." --negative-prompt "低质量,模糊" --download
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

# wan2.6 支持同步调用；wan2.5及以下需要异步
_SYNC_MODELS = {"wan2.6-t2i"}

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


def _wait_task(task_id: str, interval: int = 5, max_wait: int = 300) -> dict:
    """Poll async task until SUCCEEDED."""
    url = f"{BASE_URL}/api/v1/tasks/{task_id}"
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(url, headers=_headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("output", {}).get("task_status", "UNKNOWN")
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] status={status}")
        if status == "SUCCEEDED":
            return data.get("output", {})
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise RuntimeError(f"Task failed: {json.dumps(data, ensure_ascii=False)}")
        time.sleep(interval)
    raise TimeoutError(f"Task {task_id} timed out")


def text_to_image(
    prompt: str,
    model: str = "wan2.2-t2i-flash",
    size: str = "1280*1280",
    n: int = 1,
    negative_prompt: str = "",
    prompt_extend: bool = True,
    seed: int = None,
) -> list[str]:
    """
    Call 万相 text-to-image API. Returns list of image URLs.

    Args:
        prompt:          正向提示词
        model:           模型名，默认 wan2.2-t2i-flash
        size:            分辨率，格式 宽*高，默认 1280*1280
        n:               生成张数 1~4，默认 1
        negative_prompt: 反向提示词
        prompt_extend:   是否开启提示词智能改写，默认 True
        seed:            随机种子（可选）
    """
    is_sync_model = model in _SYNC_MODELS

    payload = {
        "model": model,
        "input": {
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ]
        },
        "parameters": {
            "size": size,
            "n": n,
            "prompt_extend": prompt_extend,
            "watermark": False,
        },
    }
    if negative_prompt:
        payload["parameters"]["negative_prompt"] = negative_prompt
    if seed is not None:
        payload["parameters"]["seed"] = seed

    if is_sync_model:
        # Synchronous (wan2.6)
        endpoint = f"{BASE_URL}/api/v1/services/aigc/multimodal-generation/generation"
        print(f"[t2i] sync call  model={model}  size={size}  n={n}")
        r = requests.post(endpoint, headers=_headers(), json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        images = []
        for choice in data.get("output", {}).get("choices", []):
            for item in choice.get("message", {}).get("content", []):
                if item.get("type") == "image":
                    images.append(item["image"])
        if not images:
            raise RuntimeError(f"No images in response: {json.dumps(data, ensure_ascii=False)}")
        return images
    else:
        # Async (wan2.5 and below) — also works for wan2.6
        endpoint = f"{BASE_URL}/api/v1/services/aigc/image-generation/generation"
        print(f"[t2i] async call  model={model}  size={size}  n={n}")
        r = requests.post(endpoint, headers=_headers(async_mode=True), json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"No task_id: {json.dumps(data, ensure_ascii=False)}")
        print(f"  task_id={task_id}")
        out = _wait_task(task_id)
        results = out.get("results", [])
        images = [r["url"] for r in results if r.get("url")]
        if not images:
            raise RuntimeError(f"No image URLs in result: {out}")
        return images


def main():
    p = argparse.ArgumentParser(description="万相文生图 V2")
    p.add_argument("--prompt", required=True, help="正向提示词")
    p.add_argument("--model", default="wan2.2-t2i-flash",
                   help="模型名 (default: wan2.2-t2i-flash)，可选: wan2.6-t2i, wan2.5-t2i-preview, wan2.2-t2i-plus 等")
    p.add_argument("--size", default="1280*1280",
                   help="分辨率 宽*高 (default: 1280*1280)，推荐: 960*1696(9:16), 1696*960(16:9)")
    p.add_argument("--n", type=int, default=1, help="生成张数 1~4 (default: 1)")
    p.add_argument("--negative-prompt", default="", help="反向提示词")
    p.add_argument("--no-prompt-extend", action="store_true", help="关闭提示词智能改写")
    p.add_argument("--seed", type=int, default=None, help="随机种子")
    p.add_argument("--download", action="store_true", help="下载生成图片到本地")
    p.add_argument("--output-dir", default=".", help="图片保存目录 (default: 当前目录)")
    args = p.parse_args()

    images = text_to_image(
        prompt=args.prompt,
        model=args.model,
        size=args.size,
        n=args.n,
        negative_prompt=args.negative_prompt,
        prompt_extend=not args.no_prompt_extend,
        seed=args.seed,
    )

    print(f"\n✅ Generated {len(images)} image(s):")
    out_dir = resolve_under_cwd(args.output_dir, field="--output-dir")
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, url in enumerate(images):
        print(f"  [{i+1}] {url}")
        if args.download:
            safe_url = validate_http_https_url(url, field="image URL")
            filename = out_dir / f"t2i_{int(time.time())}_{i+1}.png"
            with urllib.request.urlopen(safe_url, timeout=300) as response:
                with open(filename, 'wb') as f:
                    f.write(response.read())
            size_kb = filename.stat().st_size // 1024
            print(f"       → saved {filename} ({size_kb}KB)")

    return images


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
