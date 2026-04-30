#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Speech Synthesis Script
Supports standard synthesis and instruct-controlled synthesis
"""

import os
import requests
import dashscope
from api_key import get_api_key

# Set User-Agent
dashscope.default_headers = {"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-voice-creator"}


def download_audio(url: str, output_path: str) -> str:
    """
    Download audio file and handle format automatically.

    Args:
        url: Audio URL
        output_path: Output path (can be .wav or .mp3)

    Returns:
        Actual saved file path
    """
    response = requests.get(url, headers={"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-voice-creator"}, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Download failed: {response.status_code}")

    audio_data = response.content
    
    # Detect actual audio format
    if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
        actual_format = 'wav'
    elif audio_data[:3] == b'\xff\xfb' or audio_data[:3] == b'\xff\xf3':
        actual_format = 'mp3'
    elif audio_data[:4] == b'OggS':
        actual_format = 'ogg'
    else:
        actual_format = 'wav'  # default
    
    # Ensure extension matches actual format
    output_path = os.path.expanduser(output_path)
    base, ext = os.path.splitext(output_path)
    if ext.lower() != f'.{actual_format}':
        output_path = f'{base}.{actual_format}'
        print(f"Warning: Detected audio format is {actual_format.upper()}, adjusted file extension")
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(audio_data)
    
    return output_path


def synthesize_speech(
    text: str,
    voice: str = "Cherry",
    output_file: str = None,
    show_cost: bool = True
) -> str:
    """
    Standard speech synthesis.
    
    Uses qwen-tts model.
    
    Args:
        text: Text to synthesize
        voice: Voice name, e.g. Cherry, Serena, Ethan, etc.
        output_file: Output file path (optional; if provided, audio will be downloaded)
        show_cost: Whether to show cost estimate
    
    Returns:
        Audio URL or local file path
    """
    api_key = get_api_key()
    if api_key:
        dashscope.api_key = api_key
    
    if show_cost:
        print("\n" + "=" * 60)
        print("Cost Estimate")
        print("=" * 60)
        char_count = len(text)
        # qwen-tts charges by tokens
        estimated_tokens = char_count  # rough estimate
        input_cost = (estimated_tokens / 1000) * 0.0016
        output_cost = (estimated_tokens / 1000) * 0.01
        total_cost = input_cost + output_cost
        print(f"Model: qwen-tts")
        print(f"Characters: {char_count} chars (approx. {estimated_tokens} tokens)")
        print(f"Input cost: China CNY {input_cost:.4f} (CNY 0.0016/1K tokens)")
        print(f"Output cost: China CNY {output_cost:.4f} (CNY 0.01/1K tokens)")
        print(f"Estimated total: China CNY {total_cost:.4f}")
        print("=" * 60)
    
    print(f"\nSynthesizing speech...")
    print(f"Text: {text[:50]}..." if len(text) > 50 else f"Text: {text}")
    print(f"Voice: {voice}")
    
    response = dashscope.MultiModalConversation.call(
        model="qwen-tts",
        text=text,
        voice=voice
    )
    
    if response.status_code == 200:
        audio_url = response.output.get('audio', {}).get('url', '')
        
        if not audio_url:
            raise Exception("Synthesis succeeded but no audio URL returned")
        
        print(f"Synthesis successful!")
        print(f"Audio URL: {audio_url[:80]}...")
        print("(URL valid for 24 hours, please download promptly)")
        
        if output_file:
            actual_path = download_audio(audio_url, output_file)
            print(f"Audio saved: {actual_path}")
            return actual_path
        
        return audio_url
    else:
        raise Exception(f"Synthesis failed: {response.code} - {response.message}")


def synthesize_with_instruct(
    text: str,
    voice: str = "Cherry",
    instructions: str = None,
    output_file: str = None,
    show_cost: bool = True
) -> str:
    """
    Instruct-controlled speech synthesis.
    
    Control voice expressiveness via natural language (speed, emotion, pitch, etc.)
    
    Args:
        text: Text to synthesize
        voice: Voice name
        instructions: Instruction description, e.g. "语速较快，充满热情和感染力"
                      (NOTE: instructions value must be in Chinese - the qwen-tts model processes Chinese instructions)
        output_file: Output file path (optional)
        show_cost: Whether to show cost estimate
    
    Returns:
        Audio URL or local file path
    """
    api_key = get_api_key()
    if api_key:
        dashscope.api_key = api_key
    
    if show_cost:
        print("\n" + "=" * 60)
        print("Cost Estimate")
        print("=" * 60)
        char_count = len(text)
        estimated_tokens = char_count
        input_cost = (estimated_tokens / 1000) * 0.0016
        output_cost = (estimated_tokens / 1000) * 0.01
        total_cost = input_cost + output_cost
        print(f"Model: qwen-tts (with instruct control)")
        print(f"Characters: {char_count} chars")
        print(f"Instructions: {instructions}")
        print(f"Estimated total: China CNY {total_cost:.4f}")
        print("=" * 60)
    
    print(f"\nSynthesizing speech with instruct control...")
    print(f"Text: {text[:50]}..." if len(text) > 50 else f"Text: {text}")
    print(f"Voice: {voice}")
    
    response = dashscope.MultiModalConversation.call(
        model="qwen-tts",
        text=text,
        voice=voice,
        instructions=instructions
    )
    
    if response.status_code == 200:
        audio_url = response.output.get('audio', {}).get('url', '')
        
        if not audio_url:
            raise Exception("Synthesis succeeded but no audio URL returned")
        
        print(f"Synthesis successful!")
        print(f"Audio URL: {audio_url[:80]}...")
        
        if output_file:
            actual_path = download_audio(audio_url, output_file)
            print(f"Audio saved: {actual_path}")
            return actual_path
        
        return audio_url
    else:
        raise Exception(f"Synthesis failed: {response.code} - {response.message}")


# Voices supported by qwen-tts via MultiModalConversation.call
VOICE_LIST = {
    "Cherry": {"name": "Qianyue", "desc": "Sunny, positive, naturally approachable young woman", "gender": "Female"},
    "Serena": {"name": "Suyao", "desc": "Gentle and soft-spoken young woman", "gender": "Female"},
    "Ethan": {"name": "Chenxu", "desc": "Sunny, warm, and energetic", "gender": "Male"},
    "Chelsie": {"name": "Qianxue", "desc": "Anime-style virtual companion", "gender": "Female"},
}


def list_voices():
    """List available voices."""
    print("\nAvailable voices:")
    print("-" * 60)
    print(f"{'Parameter':<12} {'Name':<15} {'Gender':<8} {'Description'}")
    print("-" * 60)
    for voice_id, info in VOICE_LIST.items():
        print(f"{voice_id:<12} {info['name']:<15} {info['gender']:<8} {info['desc']}")


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  Speech Synthesis - qwen-tts")
    print("=" * 60)

    # List available voices
    list_voices()
    print()

    # Get parameters from command line args or interactive input
    if len(sys.argv) > 1:
        text = sys.argv[1]
        voice = sys.argv[2] if len(sys.argv) > 2 else "Cherry"
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        print("Please provide the text to synthesize")
        print("Usage: python speech_synthesis.py <text> [voice] [output_file]")
        print()
        text = input("Text: ").strip()
        if not text:
            print("Error: No text provided")
            sys.exit(1)
        voice = input("Voice (default Cherry): ").strip() or "Cherry"
        output_file = input("Output file path (leave empty to return URL only): ").strip() or None

    if not text:
        print("Error: No text provided")
        sys.exit(1)

    # Ask whether to use instruct control
    use_instruct = input("Use instruct-controlled style? (y/N): ").strip().lower() == 'y' if len(sys.argv) <= 1 else False
    instructions = None
    if use_instruct:
        instructions = input("Instruction description (e.g. in Chinese: '语速快，充满热情'): ").strip()

    try:
        if instructions:
            result = synthesize_with_instruct(
                text=text, voice=voice,
                instructions=instructions, output_file=output_file
            )
        else:
            result = synthesize_speech(
                text=text, voice=voice, output_file=output_file
            )
        print(f"\nDone! Result: {result}")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
