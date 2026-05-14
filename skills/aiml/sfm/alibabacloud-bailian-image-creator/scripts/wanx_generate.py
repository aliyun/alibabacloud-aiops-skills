#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Wanx Image Generation Example Script
Models: wan2.7-image-pro, wan2.7-image

Supported scenarios:
- Text-to-image: Generate images from pure text descriptions
- Image editing: Edit based on reference images + text instructions
- Image series: enable_sequential=True to generate a set of coherent images
"""

import dashscope
from dashscope.aigc.image_generation import ImageGeneration
from dashscope.api_entities.dashscope_response import Message

from api_key import get_api_key

# Set API endpoint (Beijing region)
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


def wanx_generate(prompt, reference_images=None, model='wan2.7-image',
                  size="2K", output_count=1, enable_sequential=False):
    """
    Generate images using the Wanx model.

    Args:
        prompt: Text description
        reference_images: List of reference image URLs (optional, for editing/multi-image reference)
        model: Model name, 'wan2.7-image-pro' or 'wan2.7-image'
        size: Image size, '1K', '2K' (default), '4K' (pro text-to-image only)
        output_count: Number of output images (normal mode 1-4, series mode 1-12)
        enable_sequential: Whether to enable image series generation mode

    Returns:
        List of generated image URLs
    """
    api_key = get_api_key()

    # Set custom headers
    dashscope.default_headers = {"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"}

    # Build message content
    content = [{"text": prompt}]
    if reference_images:
        for img_url in reference_images:
            content.append({"image": img_url})

    message = Message(
        role="user",
        content=content
    )

    print("----sync call, please wait a moment----")
    rsp = ImageGeneration.call(
        model=model,
        api_key=api_key,
        messages=[message],
        watermark=False,
        n=output_count,
        enable_sequential=enable_sequential,
        size=size,
        timeout=120
    )

    if rsp.status_code == 200:
        image_urls = []
        for choice in rsp.output.choices:
            for content_item in choice["message"]["content"]:
                if content_item.get("type") == "image":
                    image_urls.append(content_item["image"])
        return image_urls
    else:
        print(f"HTTP status code: {rsp.status_code}")
        print(f"Error code: {rsp.code}")
        print(f"Error message: {rsp.message}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python wanx_generate.py <prompt> [ref_image_URL1] [ref_image_URL2] ...")
        print()
        print("Text-to-image example:")
        print("  python wanx_generate.py 'A panda drinking tea in a bamboo forest, ink painting style'")
        print()
        print("Image editing example (with reference images):")
        print("  python wanx_generate.py 'Paint the graffiti from image 2 on the car in image 1' url1 url2")
        sys.exit(1)

    prompt = sys.argv[1]
    reference_images = sys.argv[2:] if len(sys.argv) > 2 else None

    print(f"Prompt: {prompt}")
    if reference_images:
        print(f"Reference images: {len(reference_images)}")
    print("Generating image...")

    image_urls = wanx_generate(prompt, reference_images)

    if image_urls:
        print(f"\nGeneration successful! {len(image_urls)} image(s):")
        for i, url in enumerate(image_urls, 1):
            print(f"  Image {i}: {url}")
    else:
        print("Generation failed")
