#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reference-to-Video - Generate video from multiple reference materials

Uses wan2.6-r2v-flash model to generate multi-character video from multiple reference videos/images
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


def create_task(prompt: str, reference_urls: list, duration: int = 10) -> str:
    """Create a reference-to-video task."""
    print("Creating reference-to-video task...")

    payload = {
        "model": "wan2.6-r2v-flash",
        "input": {
            "prompt": prompt,
            "reference_urls": reference_urls
        },
        "parameters": {
            "size": "1280*720",
            "duration": duration,
            "audio": True,
            "shot_type": "multi",
            "watermark": True
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
    print("(Reference-to-video is an async task, please wait patiently)")
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


def generate_video(prompt: str, reference_urls: list, duration: int = 10):
    """Generate reference-to-video."""
    # Parameter validation
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    if not isinstance(reference_urls, list) or len(reference_urls) == 0:
        raise ValueError("reference_urls must be a non-empty list")
    for i, url in enumerate(reference_urls):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError(f"reference_urls[{i}] must be a valid HTTP/HTTPS URL")
    if not isinstance(duration, int):
        raise ValueError(f"duration must be an integer, got {type(duration).__name__}")
    if duration < 1 or duration > 30:
        raise ValueError(f"duration must be between 1 and 30 seconds, got {duration}")

    print("=" * 60)
    print("  Reference-to-Video")
    print("=" * 60)
    print()
    print(f"Prompt: {prompt[:80]}...")
    print(f"Reference material count: {len(reference_urls)}")
    for i, url in enumerate(reference_urls, 1):
        print(f"  [{i}] {url}")
    print(f"Duration: {duration}s")
    print()

    task_id = create_task(prompt, reference_urls, duration)
    if task_id:
        result_url = poll_result(task_id)

        # Cost estimate
        if result_url:
            print()
            print("=" * 60)
            print("💰 Cost Estimate")
            print("=" * 60)
            # wan2.6-r2v-flash pricing
            # Default 720P with audio
            cost_per_second = 0.3
            # Calculate input video duration (max 5 seconds)
            input_duration = min(5 * len([u for u in reference_urls if u.endswith('.mp4')]), 5)
            total_duration = input_duration + duration
            total_cost = cost_per_second * total_duration
            print(f"Model: wan2.6-r2v-flash")
            print(f"Resolution: 720P (with audio)")
            print(f"Unit price: ¥{cost_per_second}/sec")
            print(f"Input video duration: {input_duration} sec (billed max 5 sec)")
            print(f"Output video duration: {duration} sec")
            print(f"Total billed duration: {total_duration} sec")
            print(f"Estimated cost: ¥{total_cost:.2f}")
            print("\n📊 View detailed billing:")
            print("   https://usercenter2.aliyun.com/finance/expense-center/overview")
            print("=" * 60)

        return result_url


if __name__ == "__main__":
    print("Reference-to-Video - Multi-material (wan2.6-r2v-flash)")
    print()
    print("Usage:")
    print("  from reference_to_video import generate_video")
    print('  generate_video(prompt="...", reference_urls=["url1", "url2"], duration=10)')
    print()
    print("Required parameters:")
    print("  prompt          - Video description, use Character1, Character2 etc. to reference materials")
    print("  reference_urls  - List of reference materials (can include video and image URLs)")
    print()
    print("Optional parameters:")
    print("  duration - Video duration (seconds), default 10")
    print()
    print("Optional parameters:")
    print("  duration - Video duration (seconds), default 10")
    print("  duration - Video duration (seconds), default 10")
