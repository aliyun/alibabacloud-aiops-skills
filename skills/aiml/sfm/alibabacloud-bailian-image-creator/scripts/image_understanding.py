#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Image and Video Understanding Example Script
Models: qwen3.5-plus, qwen-vl-max, qwen-vl-plus
"""

from openai import OpenAI

from api_key import get_api_key

# Set API endpoint (Beijing region)
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# Singapore region: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
# Virginia region: https://dashscope-us.aliyuncs.com/compatible-mode/v1


def analyze_image(image_url, question, model="qwen3.5-plus"):
    """
    Analyze image content and answer questions.

    Args:
        image_url: Image URL or local path (file://)
        question: Question text
        model: Model name, e.g., 'qwen3.5-plus', 'qwen-vl-max'

    Returns:
        Model response content
    """
    client = OpenAI(
        api_key=get_api_key(),
        base_url=BASE_URL,
        default_headers={"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"},
        timeout=60.0
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        },
                    },
                    {"type": "text", "text": question},
                ],
            },
        ],
    )

    return completion.choices[0].message.content


def analyze_multiple_images(image_urls, question, model="qwen3.5-plus"):
    """
    Analyze multiple images and answer questions.

    Args:
        image_urls: List of image URLs
        question: Question text
        model: Model name

    Returns:
        Model response content
    """
    client = OpenAI(
        api_key=get_api_key(),
        base_url=BASE_URL,
        default_headers={"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-image-creator"},
        timeout=60.0
    )

    content = []
    for img_url in image_urls:
        content.append({
            "type": "image_url",
            "image_url": {"url": img_url}
        })
    content.append({"type": "text", "text": question})

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": content,
            },
        ],
    )

    return completion.choices[0].message.content


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        image_url = sys.argv[1]
        question = sys.argv[2]
    elif len(sys.argv) == 2:
        image_url = sys.argv[1]
        question = "Please describe the content of this image in detail"
    else:
        print("Usage: python image_understanding.py <image_URL> [question]")
        print("Example: python image_understanding.py https://example.com/photo.jpg 'What is depicted in this image?'")
        sys.exit(1)

    print(f"Image: {image_url}")
    print(f"Question: {question}")
    print("Analyzing image...")
    response = analyze_image(image_url, question, model="qwen3.5-plus")
    print(f"\nAnalysis result:\n{response}")
