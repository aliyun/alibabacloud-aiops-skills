#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Video Region Edit - Fine-grained editing of specific video regions

Uses wanx2.1-vace-plus model, supports element add/remove/modify and subject/background replacement
"""

import sys
import time
import hashlib
import requests
from api_key import get_api_key

sys.stdout.reconfigure(encoding='utf-8')

# Set API URL (Beijing region)
BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

# Get API Key
api_key = get_api_key()


def create_task(prompt: str, video_url: str, mask_image_url: str,
                mask_frame_id: int = 1, mask_type: str = "tracking",
                expand_ratio: float = 0.05) -> str:
    """Create a video region edit task."""
    print("Creating video region edit task...")

    payload = {
        "model": "wanx2.1-vace-plus",
        "input": {
            "function": "video_edit",
            "prompt": prompt,
            "video_url": video_url,
            "mask_image_url": mask_image_url,
            "mask_frame_id": mask_frame_id
        },
        "parameters": {
            "prompt_extend": False,
            "mask_type": mask_type,  # tracking or fixed
            "expand_ratio": expand_ratio
        }
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/services/aigc/video-generation/video-synthesis",
            headers={
                "X-DashScope-Async": "enable",
                "X-DashScope-ClientToken": client_token,
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-video-creator"
            },
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()

        if "output" in data and "task_id" in data["output"]:
            task_id = data["output"]["task_id"]
            print("[OK] Task created successfully!")
            print(f"Task ID: {task_id}")
            return task_id
        else:
            print(f"[ERROR] Unexpected response format: {data}")
            return None

    except requests.RequestException as e:
        print(f"[ERROR] Failed to create task: {e}")
        return None


def poll_result(task_id: str) -> str:
    """Poll task result."""
    print()
    print("Generating video, this may take a few minutes...")
    print("(Video region edit is an async task, please wait patiently)")
    print()

    max_attempts = 60
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        try:
            resp = requests.get(
                f"{BASE_URL}/tasks/{task_id}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-video-creator"
                },
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()

            output = data.get("output", {})
            status = output.get("task_status", "UNKNOWN")
            print(f"[{attempt}/{max_attempts}] Current status: {status}")

            if status == "SUCCEEDED":
                video_url = output.get("video_url")
                print()
                print("=" * 60)
                print("  [SUCCESS] Video generated successfully!")
                print("=" * 60)
                print()
                print(f"Video URL: {video_url}")
                print()
                print("Tips:")
                print("   - Click URL to play the video in browser")
                print("   - Video link has an expiration time, download promptly")
                return video_url

            elif status in ("FAILED", "CANCELLED"):
                print()
                print("=" * 60)
                print("  [FAILED] Video generation failed")
                print("=" * 60)
                print(f"Error message: {output.get('message', 'Unknown error')}")
                return None

            elif status in ("PENDING", "RUNNING"):
                time.sleep(10)
            else:
                print(f"Unknown status: {status}")
                time.sleep(10)

        except requests.RequestException as e:
            print(f"Polling exception: {e}, retrying in 10 seconds...")
            time.sleep(10)

    print()
    print("Max polling attempts reached, task still in progress")
    print(f"You can check later using Task ID: {task_id}")
    return None


def edit_video_region(prompt: str, video_url: str, mask_image_url: str,
                      mask_frame_id: int = 1, mask_type: str = "tracking",
                      expand_ratio: float = 0.05):
    """Video region edit."""
    # Parameter validation
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    if not isinstance(video_url, str) or not video_url.startswith(("http://", "https://")):
        raise ValueError("video_url must be a valid HTTP/HTTPS URL")
    if not isinstance(mask_image_url, str) or not mask_image_url.startswith(("http://", "https://")):
        raise ValueError("mask_image_url must be a valid HTTP/HTTPS URL")
    if not isinstance(mask_frame_id, int) or mask_frame_id < 1:
        raise ValueError(f"mask_frame_id must be a positive integer (>= 1), got {mask_frame_id}")
    VALID_MASK_TYPES = ("tracking", "fixed")
    if mask_type not in VALID_MASK_TYPES:
        raise ValueError(f"mask_type must be one of {VALID_MASK_TYPES}, got {mask_type}")
    if not isinstance(expand_ratio, (int, float)):
        raise ValueError(f"expand_ratio must be a numeric type, got {type(expand_ratio).__name__}")
    if expand_ratio < 0.0 or expand_ratio > 1.0:
        raise ValueError(f"expand_ratio must be in range [0.0, 1.0], got {expand_ratio}")

    print("=" * 60)
    print("  Video Region Edit")
    print("=" * 60)
    print()
    print(f"Prompt: {prompt[:80]}...")
    print(f"Video URL: {video_url}")
    print(f"Mask URL: {mask_image_url}")
    print(f"Mask frame ID: {mask_frame_id}")
    print(f"Mask type: {mask_type}")
    print(f"Expand ratio: {expand_ratio}")
    print()

    task_id = create_task(prompt, video_url, mask_image_url,
                          mask_frame_id, mask_type, expand_ratio)
    if task_id:
        video_url = poll_result(task_id)
        return video_url


if __name__ == "__main__":
    print("Video Region Edit (wanx2.1-vace-plus)")
    print()
    print("Usage:")
    print("  from video_local_edit import edit_video_region")
    print('  edit_video_region(prompt="Edit description", video_url="https://...", mask_image_url="https://...")')
    print()
    print("Required parameters:")
    print("  prompt         - Description after editing")
    print("  video_url      - Original video URL")
    print("  mask_image_url - Mask image URL (white region = area to edit)")
    print()
    print("Optional parameters:")
    print("  mask_frame_id  - Video frame index for the mask, default 1")
    print('  mask_type      - "tracking" (follow motion, default) or "fixed" (fixed position)')
    print("  expand_ratio   - Mask expansion ratio [0.0, 1.0], default 0.05")
    print()
    print("Optional parameters:")
    print("  mask_frame_id  - Video frame index for the mask, default 1")
    print('  mask_type      - "tracking" (follow motion, default) or "fixed" (fixed position)')
    print("  expand_ratio   - Mask expansion ratio [0.0, 1.0], default 0.05")
    print("  expand_ratio   - Mask expansion ratio [0.0, 1.0], default 0.05")
