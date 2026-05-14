#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Image-to-Video - Generate video from image + audio

Uses wan2.6-i2v model to generate video from reference image and audio
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


def create_task(prompt: str, img_url: str, audio_url: str = None, duration: int = 10) -> str:
    """Create an image-to-video task."""
    print("Creating image-to-video task...")

    payload = {
        "model": "wan2.6-i2v",
        "input": {
            "prompt": prompt,
            "img_url": img_url
        },
        "parameters": {
            "resolution": "720P",
            "duration": duration,
            "prompt_extend": True,
            "watermark": False,
            "negative_prompt": "",
            "seed": 12345
        }
    }

    # Add audio URL if provided
    if audio_url:
        payload["input"]["audio_url"] = audio_url

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
    print("(Image-to-video is an async task, please wait patiently)")
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


def generate_video(prompt: str, img_url: str, audio_url: str = None, duration: int = 10, resolution: str = "720P"):
    """Generate image-to-video."""
    # Parameter validation
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    if not isinstance(img_url, str) or not img_url.startswith(("http://", "https://")):
        raise ValueError("img_url must be a valid HTTP/HTTPS URL")
    if audio_url is not None:
        if not isinstance(audio_url, str) or not audio_url.startswith(("http://", "https://")):
            raise ValueError("audio_url must be a valid HTTP/HTTPS URL")
    if not isinstance(duration, int):
        raise ValueError(f"duration must be an integer, got {type(duration).__name__}")
    if duration < 1 or duration > 30:
        raise ValueError(f"duration must be between 1 and 30 seconds, got {duration}")
    VALID_RESOLUTIONS = ("720P", "1080P")
    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTIONS}, got {resolution}")

    print("=" * 60)
    print("  Image-to-Video")
    print("=" * 60)
    print()
    print(f"Prompt: {prompt[:80]}...")
    print(f"Image URL: {img_url}")
    if audio_url:
        print(f"Audio URL: {audio_url}")
    print(f"Duration: {duration}s")
    print(f"Resolution: {resolution}")
    print()

    task_id = create_task(prompt, img_url, audio_url, duration)
    if task_id:
        video_url = poll_result(task_id)

        # Cost estimate
        if video_url:
            print()
            print("=" * 60)
            print("💰 Cost Estimate")
            print("=" * 60)
            # wan2.6-i2v pricing
            if "1080" in resolution:
                cost_per_second = 0.5 if audio_url else 0.25
            else:
                cost_per_second = 0.3 if audio_url else 0.15

            video_type = "with audio" if audio_url else "silent"
            total_cost = cost_per_second * duration
            print(f"Model: wan2.6-i2v")
            print(f"Resolution: {resolution}")
            print(f"Video type: {video_type}")
            print(f"Unit price: ¥{cost_per_second}/sec")
            print(f"Video duration: {duration} sec")
            print(f"Estimated cost: ¥{total_cost:.2f}")
            print("\n📊 View detailed billing:")
            print("   https://usercenter2.aliyun.com/finance/expense-center/overview")
            print("=" * 60)

        return video_url


if __name__ == "__main__":
    print("Image-to-Video - HTTP API (wan2.6-i2v)")
    print()
    print("Usage:")
    print("  from image_to_video import generate_video")
    print('  generate_video(prompt="Video description", img_url="https://...", duration=10)')
    print()
    print("Required parameters:")
    print("  prompt   - Video description")
    print("  img_url  - Reference image URL (publicly accessible)")
    print()
    print("Optional parameters:")
    print("  audio_url  - Audio URL (optional, generates video with audio when provided)")
    print("  duration   - Video duration (seconds), default 10")
    print('  resolution - Resolution, default "720P", option "1080P"')
    print("  audio_url  - Audio URL (optional, generates video with audio when provided)")
    print("  duration   - Video duration (seconds), default 10")
    print('  resolution - Resolution, default "720P", option "1080P"')
    print('  resolution - Resolution, default "720P", option "1080P"')
