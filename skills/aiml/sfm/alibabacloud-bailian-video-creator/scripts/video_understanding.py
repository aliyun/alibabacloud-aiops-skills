#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Video Understanding - Analyze video content

Uses qwen3.5-plus model to analyze video content, supports uploading video URL with configurable frame extraction rate
"""

import sys
import dashscope
from api_key import get_api_key

sys.stdout.reconfigure(encoding='utf-8')

# Set API URL (Beijing region)
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

# Set User-Agent
dashscope.default_headers = {"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-video-creator"}

# Get API Key
api_key = get_api_key()


def analyze_video(video_url: str, prompt: str = "What is the content of this video?", fps: int = 2):
    """
    Analyze video content

    Args:
        video_url: Video URL (MP4 format)
        prompt: Analysis question, defaults to asking about video content
        fps: Frame extraction rate, extracts one frame every 1/fps seconds
    """
    # Parameter validation
    if not isinstance(video_url, str) or not video_url.startswith(("http://", "https://")):
        raise ValueError("video_url must be a valid HTTP/HTTPS URL")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    if not isinstance(fps, int) or fps < 1:
        raise ValueError(f"fps must be a positive integer (>= 1), got {fps}")

    print("="*60)
    print("  Video Understanding - Analyze Video Content")
    print("="*60)
    print(f"Video URL: {video_url}")
    print(f"Frame rate: extract one frame every {1/fps:.2f} seconds (fps={fps})")
    print(f"Analysis question: {prompt}")
    print()

    messages = [
        {
            "role": "user",
            "content": [
                {"video": video_url, "fps": fps},
                {"text": prompt}
            ]
        }
    ]

    print("Calling qwen3.5-plus model to analyze video...")
    print("(Depending on video length, this may take 1-3 minutes)")
    print()

    try:
        response = dashscope.MultiModalConversation.call(
            api_key=api_key,
            model='qwen3.5-plus',
            messages=messages
        )

        if response.status_code == 200:
            result = response.output.choices[0].message.content[0]["text"]
            print("="*60)
            print("  ✅ Video analysis complete!")
            print("="*60)
            print()
            print(result)
            return result
        else:
            print(f"❌ Analysis failed")
            print(f"Status code: {response.status_code}")
            print(f"Error message: {response.message}")
            return None

    except Exception as e:
        print(f"❌ Exception: {e}")
        return None


if __name__ == "__main__":
    print("Video Understanding - Analyze Video Content (qwen3.5-plus)")
    print()
    print("Usage:")
    print("  from video_understanding import analyze_video")
    print('  analyze_video(video_url="https://...", prompt="What is the content of this video?", fps=2)')
    print()
    print("Required parameters:")
    print("  video_url - Video URL (MP4 format, publicly accessible, recommended ≤5 minutes)")
    print()
    print("Optional parameters:")
    print('  prompt - Analysis question, default "What is the content of this video?"')
    print("  fps    - Frame extraction rate, default 2 (one frame per 0.5s, higher = more accurate but slower)")
