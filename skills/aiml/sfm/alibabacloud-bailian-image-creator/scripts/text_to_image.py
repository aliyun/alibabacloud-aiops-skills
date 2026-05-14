#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qwen Text-to-Image Example Script
Models: qwen-image-2.0-pro, qwen-image-2.0

Important Notes:
1. DASHSCOPE_API_KEY is first read from ~/.aliyun/config.json current profile's dashscope.api_key
2. Fallback: read from environment variable DASHSCOPE_API_KEY
3. DASHSCOPE_API_KEY (sk-xxx) and DashScope Coding Plan API Key (sk-sp-xxx) are two different keys
"""

import os
import sys
import urllib.request
import dashscope
from dashscope import MultiModalConversation

from api_key import get_api_key

# Set API endpoint (Beijing region)
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
# Singapore region: https://dashscope-intl.aliyuncs.com/api/v1


def generate_image(prompt, size='1024*1024', model='qwen-image-2.0-pro',
                   save_dir=None):
    """
    Generate an image from text description.

    Args:
        prompt: Text description
        size: Image size, supports '1024*1024', '720*1280', '1280*720', etc.
        model: Model name, 'qwen-image-2.0-pro' or 'qwen-image-2.0'
        save_dir: Save directory; if specified, auto-downloads images; None returns URLs only

    Returns:
        List of generated image URLs (if save_dir is specified, also downloads locally)
    """
    # Cost estimation and confirmation
    print("\n" + "=" * 60)
    print("Cost Estimate")
    print("=" * 60)
    cost_per_image = 0.5 if model == 'qwen-image-2.0-pro' else 0.21
    n = 1  # Default: generate 1 image
    estimated_cost = cost_per_image * n
    print(f"Model: {model}")
    print(f"Unit price: {cost_per_image}/image")
    print(f"Count: {n} image(s)")
    print(f"Estimated cost: {estimated_cost:.2f}")
    print("=" * 60)

    # Skip confirmation in non-interactive environments
    if sys.stdin.isatty():
        confirm = input("\nProceed with generation? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Generation cancelled")
            return None

    messages = [
        {
            "role": "user",
            "content": [
                {"text": prompt}
            ]
        }
    ]

    # Get API Key (supports Alibaba Cloud CLI config and environment variable)
    api_key = get_api_key()
    dashscope.api_key = api_key

    # Set custom headers
    dashscope.default_headers = {"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"}

    print("\nGenerating image...")
    response = MultiModalConversation.call(
        api_key=api_key,
        model=model,
        messages=messages,
        result_format='message',
        stream=False,
        watermark=False,
        prompt_extend=True,
        negative_prompt="low quality, blurry, deformed hands, extra fingers, distorted face, uncanny valley, text, watermark, logo, signature, worst quality",
        size=size,
        timeout=120
    )

    if response.status_code == 200:
        image_urls = []
        for content in response.output.choices[0].message.content:
            if 'image' in content:
                image_urls.append(content['image'])
        if save_dir and image_urls:
            os.makedirs(save_dir, exist_ok=True)
            for i, url in enumerate(image_urls, 1):
                filepath = os.path.join(save_dir, f"generated_{i}.png")
                with urllib.request.urlopen(url, timeout=60) as resp, open(filepath, 'wb') as f:
                    f.write(resp.read())
                print(f"  Saved: {filepath}")
        return image_urls
    else:
        print(f"HTTP status code: {response.status_code}")
        print(f"Error code: {response.code}")
        print(f"Error message: {response.message}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python text_to_image.py <prompt> [size] [model]")
        print("Example: python text_to_image.py 'An orange cat sitting on a windowsill, sunlight, 8K' 1024*1024 qwen-image-2.0-pro")
        print()
        print("Parameters:")
        print("  prompt    Required, image description text")
        print("  size      Optional, default 1024*1024 (supports 720*1280, 1280*720, etc.)")
        print("  model     Optional, default qwen-image-2.0-pro (or qwen-image-2.0)")
        sys.exit(1)

    prompt = sys.argv[1]
    size = sys.argv[2] if len(sys.argv) >= 3 else '1024*1024'
    model = sys.argv[3] if len(sys.argv) >= 4 else 'qwen-image-2.0-pro'

    image_urls = generate_image(prompt, size=size, model=model, save_dir=os.getcwd())

    if image_urls:
        print(f"\nGeneration successful! {len(image_urls)} image(s):")
        for i, url in enumerate(image_urls, 1):
            print(f"  Image {i}: {url}")
    elif image_urls is None:
        print("\nCancelled")
    else:
        print("\nGeneration failed")
