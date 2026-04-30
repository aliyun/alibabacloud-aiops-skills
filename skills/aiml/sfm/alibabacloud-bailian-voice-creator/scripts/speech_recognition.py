#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Speech Recognition Script
Supports long audio (qwen3-asr-flash-filetrans) and short audio (qwen3-asr-flash) recognition
"""

import os
import json
import time
import dashscope
from dashscope.audio.asr import Transcription
from api_key import get_api_key

# Set API endpoint (Beijing region)
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# Set User-Agent
dashscope.default_headers = {"User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-voice-creator"}


def recognize_long_audio(file_url: str, language_hints: list = None) -> dict:
    """
    Long audio recognition (up to 12 hours).
    
    Uses qwen3-asr-flash-filetrans model, supports:
    - Emotion recognition (surprise/neutral/happy/sad/disgust/angry/fear)
    - Sentence/word-level timestamps
    - Punctuation prediction
    - Singing recognition
    - Noise rejection
    
    Args:
        file_url: Audio file URL (must be publicly accessible)
        language_hints: Language hints, e.g. ['zh', 'en']
    
    Returns:
        Recognition result dictionary
    """
    api_key = get_api_key()
    if api_key:
        dashscope.api_key = api_key
    
    print("Submitting long audio recognition task...")
    print(f"Audio URL: {file_url}")
    
    # Submit async task
    task_response = Transcription.async_call(
        model='qwen3-asr-flash-filetrans',
        file_urls=[file_url],
        language_hints=language_hints or ['zh', 'en'],
        # Optional parameters
        # channel_id=[0],      # Specify audio track index (multi-channel audio)
        # enable_itn=True,     # Enable ITN (number/date formatting), Chinese & English only
        # enable_words=True,   # Enable word-level timestamps
    )
    
    task_id = task_response.output.task_id
    print(f"Task submitted, Task ID: {task_id}")
    print("Waiting for recognition to complete...")
    
    # Wait for task completion
    transcription_response = Transcription.wait(task=task_id)
    
    if transcription_response.status_code == 200:
        results = []
        output = transcription_response.output
        
        # Check if task succeeded
        task_status = output.get('task_status', '') if isinstance(output, dict) else getattr(output, 'task_status', '')
        if task_status == 'FAILED':
            code = output.get('code', '') if isinstance(output, dict) else getattr(output, 'code', '')
            message = output.get('message', '') if isinstance(output, dict) else getattr(output, 'message', '')
            raise Exception(f"Recognition task failed: {code} - {message}")
        
        # Get result list (compatible with dict and DashScopeAPIResponse objects)
        if isinstance(output, dict):
            result_list = output.get('results')
        else:
            try:
                result_list = output['results']
            except (KeyError, TypeError):
                result_list = None
        
        if result_list is None:
            return [output] if output else []
        
        for transcription in result_list:
            if isinstance(transcription, dict):
                if transcription.get('subtask_status') == 'SUCCEEDED':
                    # Get detailed recognition result
                    from urllib import request
                    result_url = transcription.get('transcription_url')
                    if result_url:
                        result = json.loads(request.urlopen(result_url).read().decode('utf8'))
                        results.append(result)
                else:
                    print(f"Subtask failed: {transcription}")
        return results
    else:
        raise Exception(f"Recognition failed: {transcription_response.output}")


def recognize_short_audio(file_url: str) -> str:
    """
    Short audio recognition (up to 5 minutes).
    
    Uses qwen3-asr-flash model, low latency, suitable for real-time scenarios.
    
    Args:
        file_url: Audio file URL (must be publicly accessible, <=10MB)
    
    Returns:
        Recognized text
    """
    import requests
    
    api_key = get_api_key() or os.environ.get("DASHSCOPE_API_KEY", "")
    
    print("Recognizing short audio...")
    print(f"Audio URL: {file_url}")
    
    response = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-voice-creator"
        },
        json={
            "model": "qwen3-asr-flash",
            "input": {
                "file_url": file_url
            }
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        return result.get('output', {}).get('text', '')
    else:
        raise Exception(f"Recognition failed: {response.text}")


def print_recognition_result(result: dict):
    """Print recognition result, including timestamps and emotion info."""
    print("\n" + "=" * 60)
    print("  Speech Recognition Result")
    print("=" * 60)
    
    if 'transcripts' in result:
        for transcript in result['transcripts']:
            # Print text
            text = transcript.get('text', '')
            print(f"\nRecognized text: {text}")
            
            # Print sentence-level details
            if 'sentences' in transcript:
                print("\nSentence details:")
                for i, sentence in enumerate(transcript['sentences'], 1):
                    text = sentence.get('text', '')
                    begin_time = sentence.get('begin_time', 0) / 1000  # Convert to seconds
                    end_time = sentence.get('end_time', 0) / 1000
                    emotion = sentence.get('emotion', '')
                    
                    print(f"  [{begin_time:.2f}s - {end_time:.2f}s] {text}")
                    if emotion:
                        print(f"    Emotion: {emotion}")


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  Speech Recognition - qwen3-asr-flash-filetrans")
    print("=" * 60)
    print()

    # Get audio URL from command line args or interactive input
    if len(sys.argv) > 1:
        audio_url = sys.argv[1]
    else:
        print("Please provide a publicly accessible audio file URL")
        print("Supported formats: aac, amr, flac, m4a, mp3, mp4, ogg, opus, wav, webm, etc.")
        print("Usage: python speech_recognition.py <audio_URL>")
        print()
        audio_url = input("Audio URL: ").strip()

    if not audio_url:
        print("Error: No audio URL provided")
        sys.exit(1)

    try:
        results = recognize_long_audio(
            file_url=audio_url,
            language_hints=['zh', 'en']
        )

        for result in results:
            print_recognition_result(result)

        print("\n" + "=" * 60)
        print("Cost Estimate")
        print("=" * 60)
        print("Model: qwen3-asr-flash-filetrans")
        print("Price: China CNY 0.00022/second")
        print("Note: Actual cost is calculated based on audio duration")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
