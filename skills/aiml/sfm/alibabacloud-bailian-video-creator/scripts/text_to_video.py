#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Text-to-Video - Multi-shot video generation

Uses wan2.6-t2v model to generate multi-shot videos
Based on HTTP API implementation (compatible with all dashscope versions)
"""

import sys
import time
import hashlib
import requests
from api_key import get_api_key

# Set UTF-8 encoding output
sys.stdout.reconfigure(encoding='utf-8')

# Set API URL (Beijing region)
BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

# Get API Key
api_key = get_api_key()


def create_task(prompt: str, duration: int = 10, size: str = "1280*720") -> str:
    """Create a video generation task."""
    print("Creating video generation task...")

    # Generate idempotency token to prevent duplicate task creation on retry
    client_token = hashlib.sha256(f"{prompt}|{duration}|{size}".encode()).hexdigest()[:64]

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
            json={
                "model": "wan2.6-t2v",
                "input": {
                    "prompt": prompt
                },
                "parameters": {
                    "size": size,
                    "shot_type": "multi",  # Multi-shot mode
                    "duration": duration,
                    "prompt_extend": True,  # Smart prompt rewriting
                    "watermark": True,
                    "negative_prompt": "",
                    "seed": 12345
                }
            },
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
    print("(Video generation is an async task, please wait patiently)")
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
                timeout=10
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


def generate_video(prompt: str, duration: int = 10, size: str = "1280*720"):
    """Generate a multi-shot video."""
    # Parameter validation
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    if not isinstance(duration, int):
        raise ValueError(f"duration must be an integer, got {type(duration).__name__}")
    if duration < 1 or duration > 30:
        raise ValueError(f"duration must be between 1 and 30 seconds, got {duration}")
    VALID_SIZES = ("1280*720", "1920*1080")
    if size not in VALID_SIZES:
        raise ValueError(f"size must be one of {VALID_SIZES}, got {size}")

    print("=" * 60)
    print("  Text-to-Video - Multi-shot Mode")
    print("=" * 60)
    print()
    print(f"Prompt: {prompt[:100]}...")
    print(f"Duration: {duration}s")
    print(f"Resolution: {size}")
    print()

    # Cost estimation and confirmation
    print("=" * 60)
    print("💰 Cost Estimate")
    print("=" * 60)
    if "1080" in size:
        cost_per_second = 1.0
        resolution = "1080P"
    else:
        cost_per_second = 0.6
        resolution = "720P"

    estimated_cost = cost_per_second * duration
    print(f"Model: wan2.6-t2v")
    print(f"Resolution: {resolution}")
    print(f"Unit price: ¥{cost_per_second}/sec")
    print(f"Video duration: {duration} sec")
    print(f"Estimated cost: ¥{estimated_cost:.2f}")
    print("=" * 60)

    print()
    task_id = create_task(prompt, duration, size)
    if task_id:
        video_url = poll_result(task_id)

        # Actual cost
        if video_url:
            print()
            print("=" * 60)
            print("💰 Actual Cost")
            print("=" * 60)
            total_cost = cost_per_second * duration
            print(f"Video duration: {duration} sec")
            print(f"Actual cost: ¥{total_cost:.2f}")
            print("\n📊 View detailed billing:")
            print("   https://usercenter2.aliyun.com/finance/expense-center/overview")
            print("=" * 60)

        return video_url


if __name__ == "__main__":
    print("Text-to-Video - Multi-shot Mode (wan2.6-t2v)")
    print()
    print("Usage:")
    print("  from text_to_video import generate_video")
    print('  generate_video(prompt="Video description (with shot list)", duration=10, size="1280*720")')
    print()
    print("Required parameters:")
    print("  prompt   - Video description, recommended to include shot list (e.g., 'Shot 1 [0-2s]...')")
    print()
    print("Optional parameters:")
    print("  duration - Video duration (seconds), default 10")
    print('  size     - Resolution, default "1280*720", option "1920*1080"')
    print('  size     - Resolution, default "1280*720", option "1920*1080"')
