#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Image-to-Video - Using DashScope SDK

Uses dashscope VideoSynthesis SDK for image-to-video generation
Supports image + audio to generate video
"""

import sys
import hashlib
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope
from api_key import get_api_key

sys.stdout.reconfigure(encoding='utf-8')

# Set API URL (Beijing region)
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# Set User-Agent
dashscope.default_headers = {"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-video-creator"}

# Get API Key
api_key = get_api_key()


def generate_video(prompt: str, img_url: str, audio_url: str = None, duration: int = 10):
    """
    Generate image-to-video using SDK.

    Args:
        prompt: Video description text
        img_url: Reference image URL
        audio_url: Audio URL (optional)
        duration: Video duration (seconds)
    """
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

    print("="*60)
    print("  Image-to-Video - DashScope SDK")
    print("="*60)
    print(f"Model: wan2.6-i2v-flash")
    print(f"Image: {img_url}")
    if audio_url:
        print(f"Audio: {audio_url}")
    print(f"Prompt: {prompt}")
    print()

    # Generate idempotency token to prevent duplicate task creation on retry
    client_token = hashlib.sha256(f"{prompt}|{img_url}|{audio_url}|{duration}".encode()).hexdigest()[:64]
    dashscope.default_headers["X-DashScope-ClientToken"] = client_token

    # Async call, returns a task_id
    print("Creating task...")
    rsp = VideoSynthesis.async_call(
        api_key=api_key,
        model='wan2.6-i2v-flash',
        prompt=prompt,
        img_url=img_url,
        audio_url=audio_url,
        resolution="720P",
        duration=duration,
        prompt_extend=True,
        watermark=False,
        negative_prompt="",
        seed=12345
    )

    print(f"Response: {rsp}")
    if rsp.status_code == HTTPStatus.OK:
        task_id = rsp.output.task_id
        print(f"✅ Task ID: {task_id}")
    else:
        print(f'❌ Failed, status_code: {rsp.status_code}, code: {rsp.code}, message: {rsp.message}')
        return

    # Get async task info
    print("\nQuerying task status...")
    status = VideoSynthesis.fetch(task=rsp, api_key=api_key)
    if status.status_code == HTTPStatus.OK:
        print(f"Current status: {status.output.task_status}")
    else:
        print(f'Query failed, status_code: {status.status_code}')

    # Wait for async task to complete
    print(f"\nWaiting for task to complete (approximately 2-3 minutes)...")
    rsp = VideoSynthesis.wait(task=rsp, api_key=api_key)

    if rsp.status_code == HTTPStatus.OK:
        video_url = rsp.output.video_url
        print()
        print("="*60)
        print("  ✅ Video generated successfully!")
        print("="*60)
        print()
        print(f"Video URL: {video_url}")
        print()
        print("Tip: Video link has an expiration time, download promptly")
        return video_url
    else:
        print(f'❌ Failed, status_code: {rsp.status_code}, code: {rsp.code}, message: {rsp.message}')
        return None


if __name__ == "__main__":
    print("Image-to-Video - DashScope SDK (wan2.6-i2v-flash)")
    print()
    print("Usage:")
    print("  from image_to_video_sdk import generate_video")
    print('  generate_video(prompt="Video description", img_url="https://...", duration=10)')
    print()
    print("Required parameters:")
    print("  prompt   - Video description")
    print("  img_url  - Reference image URL (publicly accessible)")
    print()
    print("Optional parameters:")
    print("  audio_url - Audio URL (optional, generates video with audio when provided)")
    print("  duration  - Video duration (seconds), default 10")
    print("  duration  - Video duration (seconds), default 10")
