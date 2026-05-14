#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base64 Image Tool
Supports image-to-Base64 and Base64-to-image conversion for DashScope Image API
"""

import os
import sys
import base64
import json


def image_to_base64(image_path):
    """
    Convert a local image to Base64 encoding (data:{mime_type};base64 format).

    Args:
        image_path: Local image path

    Returns:
        Base64 encoded string
    """
    import mimetypes

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"File not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError(f"Unsupported or unrecognized image format: {image_path}")

    try:
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:{mime_type};base64,{encoded_string}"
    except IOError as e:
        raise IOError(f"Error reading file: {image_path}, error: {str(e)}")


def base64_to_image(base64_string, output_path):
    """
    Save a Base64 encoded string as a local image.

    Args:
        base64_string: Base64 encoded string (with or without data:image/png;base64, prefix)
        output_path: Output file path
    """
    # Remove prefix (if present)
    if ',' in base64_string:
        base64_string = base64_string.split(',', 1)[1]

    # Decode and save
    image_data = base64.b64decode(base64_string)

    with open(output_path, 'wb') as f:
        f.write(image_data)

    return output_path


def get_image_info(base64_string):
    """
    Get Base64 image information.

    Args:
        base64_string: Base64 encoded string

    Returns:
        Dictionary containing MIME type, size, and other info
    """
    info = {}

    # Check for prefix
    if ',' in base64_string:
        prefix, data = base64_string.split(',', 1)
        info['has_prefix'] = True
        info['prefix'] = prefix
        # Extract MIME type
        if 'data:' in prefix:
            mime_type = prefix.split(':')[1].split(';')[0]
            info['mime_type'] = mime_type
    else:
        data = base64_string
        info['has_prefix'] = False

    # Calculate size
    info['base64_length'] = len(base64_string)
    info['estimated_size_bytes'] = len(data) * 3 // 4  # Decoded size from Base64

    return info


def main():
    """CLI tool entry point"""
    if len(sys.argv) < 2:
        print("=" * 60)
        print("  Base64 Image Tool - DashScope Image API Helper")
        print("=" * 60)
        print()
        print("Usage:")
        print("  1. Image to Base64:")
        print("     python base64_tool.py encode <image_path>")
        print()
        print("  2. Base64 to Image:")
        print("     python base64_tool.py decode <base64_string> <output_path>")
        print("     Or read Base64 from file:")
        print("     python base64_tool.py decode --file <base64_file> <output_path>")
        print()
        print("  3. View Base64 info:")
        print("     python base64_tool.py info <base64_string>")
        print()
        print("Examples:")
        print('  python base64_tool.py encode "C:/Users/Pictures/test.png"')
        print('  python base64_tool.py decode "data:image/png;base64,iVBOR..." output.png')
        print()
        return

    command = sys.argv[1]

    if command == "encode":
        if len(sys.argv) < 3:
            print("Error: Please specify the image path")
            print("Usage: python base64_tool.py encode <image_path>")
            return

        image_path = sys.argv[2]
        try:
            base64_str = image_to_base64(image_path)
            info = get_image_info(base64_str)

            print("=" * 60)
            print("  Conversion successful")
            print("=" * 60)
            print(f"File: {image_path}")
            print(f"MIME type: {info.get('mime_type', 'unknown')}")
            print(f"Base64 length: {info['base64_length']} chars")
            print(f"Estimated size: {info['estimated_size_bytes'] / 1024:.2f} KB")
            print()
            print("Base64 string (first 100 chars):")
            print(base64_str[:100] + "...")
            print()

            # Save to file
            output_file = image_path + ".base64.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(base64_str)
            print(f"Full Base64 saved to: {output_file}")
            print("=" * 60)

        except Exception as e:
            print(f"Error: {e}")

    elif command == "decode":
        if len(sys.argv) < 4:
            print("Error: Please specify Base64 string and output path")
            print("Usage: python base64_tool.py decode <base64_string> <output_path>")
            return

        if sys.argv[2] == "--file":
            # Read Base64 from file
            base64_file = sys.argv[3]
            output_path = sys.argv[4] if len(sys.argv) > 4 else "output.png"

            with open(base64_file, 'r', encoding='utf-8') as f:
                base64_str = f.read().strip()
        else:
            base64_str = sys.argv[2]
            output_path = sys.argv[3]

        try:
            result_path = base64_to_image(base64_str, output_path)
            print("=" * 60)
            print("  Conversion successful")
            print("=" * 60)
            print(f"Output file: {result_path}")
            print(f"File size: {os.path.getsize(result_path) / 1024:.2f} KB")
            print("=" * 60)

        except Exception as e:
            print(f"Error: {e}")

    elif command == "info":
        if len(sys.argv) < 3:
            print("Error: Please specify Base64 string")
            print("Usage: python base64_tool.py info <base64_string>")
            return

        base64_str = sys.argv[2]
        try:
            info = get_image_info(base64_str)

            print("=" * 60)
            print("  Base64 Image Info")
            print("=" * 60)
            for key, value in info.items():
                print(f"{key}: {value}")
            print("=" * 60)

        except Exception as e:
            print(f"Error: {e}")

    else:
        print(f"Unknown command: {command}")
        print("Available commands: encode, decode, info")


if __name__ == "__main__":
    main()
