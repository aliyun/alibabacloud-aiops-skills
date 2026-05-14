#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Image Editing Example - Base64 Encoding Method
Demonstrates how to use Base64 encoded local images for editing
"""

import os
import base64
from dashscope import MultiModalConversation
import dashscope

from api_key import get_api_key

# Set API endpoint (Beijing region)
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


def image_to_base64(image_path):
    """Convert a local image to Base64 encoding."""
    import mimetypes

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError(f"Unsupported or unrecognized image format: {image_path}")

    try:
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:{mime_type};base64,{encoded_string}"
    except IOError as e:
        raise IOError(f"Error reading file: {image_path}, error: {str(e)}")


def edit_with_base64(image_paths, instruction, output_count=2):
    """
    Edit images using Base64 encoded images.

    Args:
        image_paths: List of local image paths (1-3)
        instruction: Editing instruction
        output_count: Number of output images

    Returns:
        List of generated image URLs
    """
    # Convert all images to Base64
    base64_images = []
    for path in image_paths:
        if not os.path.exists(path):
            print(f"Warning: File not found {path}")
            continue
        base64_images.append(image_to_base64(path))
        print(f"Loaded: {path} -> Base64 ({len(base64_images[-1])} chars)")

    if not base64_images:
        raise ValueError("No valid image files")

    # Build message
    content = [{"image": img} for img in base64_images]
    content.append({"text": instruction})

    messages = [{"role": "user", "content": content}]

    # Call API
    api_key = get_api_key()

    # Set custom headers
    dashscope.default_headers = {"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"}

    print(f"\nEditing image (model: qwen-image-2.0-pro)...")
    print(f"Instruction: {instruction}")

    response = MultiModalConversation.call(
        api_key=api_key,
        model="qwen-image-2.0-pro",
        messages=messages,
        stream=False,
        n=output_count,
        watermark=False,
        prompt_extend=True,
        negative_prompt="",
        size="1024*1536",
        timeout=120
    )

    if response.status_code == 200:
        image_urls = []
        for content in response.output.choices[0].message.content:
            if 'image' in content:
                image_urls.append(content['image'])
        return image_urls
    else:
        print(f"HTTP status code: {response.status_code}")
        print(f"Error code: {response.code}")
        print(f"Error message: {response.message}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python image_edit_base64.py <instruction> <local_image1> [local_image2] [local_image3]")
        print("Example: python image_edit_base64.py 'Convert to oil painting style' ./photo.png")
        print("         python image_edit_base64.py 'Merge these images' img1.jpg img2.jpg img3.jpg")
        sys.exit(1)

    instruction = sys.argv[1]
    image_paths = sys.argv[2:]

    print(f"Instruction: {instruction}")
    print(f"Images: {', '.join(image_paths)}")
    image_urls = edit_with_base64(image_paths, instruction, output_count=2)

    if image_urls:
        print(f"\nEditing successful! {len(image_urls)} image(s):")
        for i, url in enumerate(image_urls, 1):
            print(f"  Image {i}: {url}")
    else:
        print("\nEditing failed")
