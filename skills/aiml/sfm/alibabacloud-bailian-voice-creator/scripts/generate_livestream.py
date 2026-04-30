#!/usr/bin/env python3
"""Generate livestream e-commerce style speech audio"""
import sys
from speech_synthesis import synthesize_with_instruct, list_voices


def main():
    print("=" * 60)
    print("  Livestream Speech Generation - qwen-tts (Instruct Control)")
    print("=" * 60)

    if len(sys.argv) > 1:
        text = sys.argv[1]
        voice = sys.argv[2] if len(sys.argv) > 2 else "Cherry"
        output_path = sys.argv[3] if len(sys.argv) > 3 else "/tmp/livestream_audio.wav"
    else:
        list_voices()
        print()
        print("Please provide the livestream script text")
        print("Usage: python generate_livestream.py <script_text> [voice] [output_file]")
        print()
        text = input("Livestream script: ").strip()
        if not text:
            print("Error: No script text provided")
            sys.exit(1)
        voice = input("Voice (default Cherry): ").strip() or "Cherry"
        output_path = input("Output file (default /tmp/livestream_audio.wav): ").strip() or "/tmp/livestream_audio.wav"

    if not text:
        print("Error: No script text provided")
        sys.exit(1)

    # NOTE: instructions value must be in Chinese - the qwen-tts model processes Chinese instructions
    instructions = "语速快，充满热情和感染力，直播带货风格，音调偏高，有煽动性"

    print(f"\nText: {text}")
    print(f"Voice: {voice}")
    print(f"Instructions: {instructions}")

    try:
        result = synthesize_with_instruct(
            text=text,
            voice=voice,
            instructions=instructions,
            output_file=output_path
        )
        print(f"\nDone! File: {result}")
    except Exception as e:
        print(f"\nSynthesis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
