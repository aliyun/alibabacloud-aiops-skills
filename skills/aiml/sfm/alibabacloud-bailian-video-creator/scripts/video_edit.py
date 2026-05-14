#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Video Editing - Video Repainting

Uses wanx2.1-vace-plus model for video repainting while preserving original motion/structure
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


def create_task(prompt: str, video_url: str, control_condition: str = "depth") -> str:
    """Create a video repainting task."""
    print("Creating video repainting task...")

    payload = {
        "model": "wanx2.1-vace-plus",
        "input": {
            "function": "video_repainting",
            "prompt": prompt,
            "video_url": video_url
        },
        "parameters": {
            "prompt_extend": False,  # Recommended to disable prompt rewriting for video repainting
            "control_condition": control_condition  # posebodyface, posebody, depth, scribble
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
    print("(Video editing is an async task, please wait patiently)")
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


def edit_video(prompt: str, video_url: str, control_condition: str = "depth"):
    """Video repainting edit."""
    # Parameter validation
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    if not isinstance(video_url, str) or not video_url.startswith(("http://", "https://")):
        raise ValueError("video_url must be a valid HTTP/HTTPS URL")
    VALID_CONDITIONS = ("posebodyface", "posebody", "depth", "scribble")
    if control_condition not in VALID_CONDITIONS:
        raise ValueError(f"control_condition must be one of {VALID_CONDITIONS}, got {control_condition}")

    print("=" * 60)
    print("  Video Editing - Video Repainting")
    print("=" * 60)
    print()
    print(f"Prompt: {prompt[:80]}...")
    print(f"Video URL: {video_url}")
    print(f"Control condition: {control_condition}")
    print()

    task_id = create_task(prompt, video_url, control_condition)
    if task_id:
        result_url = poll_result(task_id)

        # Cost estimate
        if result_url:
            print()
            print("=" * 60)
            print("💰 Cost Estimate")
            print("=" * 60)
            cost_per_second = 0.72  # wanx2.1-vace-plus 720P price
            print(f"Model: wanx2.1-vace-plus")
            print(f"Resolution: 720P")
            print(f"Unit price: ¥{cost_per_second}/sec")
            print("Note: Actual cost is calculated based on output video duration")
            print(f"Example: 5 sec video = 5 × ¥{cost_per_second} = ¥{5 * cost_per_second:.2f}")
            print("\n📊 View detailed billing:")
            print("   https://usercenter2.aliyun.com/finance/expense-center/overview")
            print("=" * 60)

        return result_url


if __name__ == "__main__":
    print("Video Editing - Video Repainting (wanx2.1-vace-plus)")
    print()
    print("Usage:")
    print("  from video_edit import edit_video")
    print('  edit_video(prompt="Repainting description", video_url="https://...", control_condition="depth")')
    print()
    print("Required parameters:")
    print("  prompt    - Description of the repainted video")
    print("  video_url - Input video URL (MP4, ≤50MB, ≤5 seconds)")
    print()
    print("Optional parameters:")
    print('  control_condition - Feature extraction method, default "depth"')
    print("    posebodyface - Extract facial expressions and body movements")
    print("    posebody     - Extract body movements only")
    print("    depth        - Extract composition and motion contours (default)")
    print("    scribble     - Extract line art structure")
    print("    posebody     - Extract body movements only")
    print("    depth        - Extract composition and motion contours (default)")
    print("    scribble     - Extract line art structure")
    print("    scribble     - Extract line art structure")
