#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qwen Image Editing Example Script
Models: qwen-image-2.0-pro, qwen-image-edit-max, qwen-image-edit-plus

Supports three image input methods:
1. HTTP/HTTPS URL: "https://example.com/image.png"
2. Local file path: "file://C:/Users/Pictures/image.png"
3. Base64 encoding: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
"""

import os
import base64
from dashscope import MultiModalConversation
import dashscope

from api_key import get_api_key

# Set API endpoint (Beijing region)
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


def image_to_base64(image_path):
    """
    Convert a local image to Base64 encoding.

    Args:
        image_path: Local image path

    Returns:
        Base64 encoded string (data:{mime_type};base64 format)
    """
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


def edit_images(reference_images, instruction, model="qwen-image-2.0-pro",
                output_count=2, size="1024*1536"):
    """
    Edit images based on reference images.

    Args:
        reference_images: List of reference images (1-3), supports three formats:
            - HTTP/HTTPS URL: "https://example.com/image.png"
            - Local file path: "file://C:/Users/Pictures/image.png"
            - Base64 encoding: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
        instruction: Editing instruction text
        model: Editing model, supports 'qwen-image-2.0-pro', 'qwen-image-edit-max',
               'qwen-image-edit-plus', 'qwen-image-edit'
        output_count: Number of output images (1-6, qwen-image-edit fixed at 1)
        size: Output image size

    Returns:
        List of generated image URLs
    """
    if len(reference_images) < 1 or len(reference_images) > 3:
        raise ValueError("Reference image count must be between 1 and 3")

    # Process image reference formats
    processed_images = []
    for img in reference_images:
        if img.startswith('file://'):
            # Local file path, convert to Base64
            local_path = img[7:]  # Remove file:// prefix
            if not os.path.exists(local_path):
                raise ValueError(f"Local file not found: {local_path}")
            processed_images.append(image_to_base64(local_path))
        elif img.startswith('data:image'):
            # Already Base64 format, use directly
            processed_images.append(img)
        else:
            # HTTP/HTTPS URL, use directly
            processed_images.append(img)

    # Build message content
    content = []
    for img_ref in processed_images:
        content.append({"image": img_ref})
    content.append({"text": instruction})

    messages = [
        {
            "role": "user",
            "content": content
        }
    ]

    api_key = get_api_key()

    # Set custom headers
    dashscope.default_headers = {"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"}

    response = MultiModalConversation.call(
        api_key=api_key,
        model=model,
        messages=messages,
        stream=False,
        n=output_count,
        watermark=False,
        prompt_extend=True,
        negative_prompt="",
        size=size,
        timeout=120
    )

    if response.status_code == 200:
        image_urls = []
        for content_item in response.output.choices[0].message.content:
            if 'image' in content_item:
                image_urls.append(content_item['image'])
    else:
        image_urls = None

    if image_urls:
        print(f"Success! Generated {len(image_urls)} image(s)")
        for i, url in enumerate(image_urls, 1):
            print(f"  Image {i}: {url}")

        # Cost info
        print("\n" + "=" * 60)
        print("Cost Estimate")
        print("=" * 60)
        cost_per_image = 0.5 if model in ('qwen-image-2.0-pro', 'qwen-image-edit-max') else 0.21
        total_cost = cost_per_image * len(image_urls)
        print(f"Model: {model}")
        print(f"Unit price: {cost_per_image}/image")
        print(f"Count: {len(image_urls)} image(s)")
        print(f"Estimated cost: {total_cost:.2f}")
        print(f"\nView detailed bills:")
        print("   https://usercenter2.aliyun.com/finance/expense-center/overview")
        print("=" * 60)
        return image_urls
    else:
        if response.status_code != 200:
            print(f"HTTP status code: {response.status_code}")
            print(f"Error code: {response.code}")
            print(f"Error message: {response.message}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python image_edit.py <instruction> <image_URL1> [image_URL2] [image_URL3]")
        print("Example: python image_edit.py 'Change the background to white' https://example.com/photo.png")
        print("         python image_edit.py 'Person from image 1 wearing clothes from image 2' url1 url2")
        print()
        print("Supported image formats:")
        print("  - HTTP/HTTPS URL: https://example.com/image.png")
        print("  - Local file path: file:///path/to/image.png")
        print("  - Base64 encoding: data:image/png;base64,...")
        sys.exit(1)

    instruction = sys.argv[1]
    reference_images = sys.argv[2:]

    print(f"Instruction: {instruction}")
    print(f"Reference images: {len(reference_images)}")
    image_urls = edit_images(reference_images, instruction)

    if image_urls:
        print(f"\nEditing successful! {len(image_urls)} image(s):")
        for i, url in enumerate(image_urls, 1):
            print(f"  Image {i}: {url}")
    else:
        print("\nEditing failed")
