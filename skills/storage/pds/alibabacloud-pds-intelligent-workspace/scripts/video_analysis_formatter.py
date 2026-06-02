#!/usr/bin/env python3
"""
PDS Audio/Video Analysis Result Formatter

Downloads and parses signed files, then formats audio/video analysis results.
Supports video summary, transcript, chapter summaries, PPT details, etc.

Note: To submit and poll analysis tasks, use pds_poll_processor.py instead.
"""

import requests
import json
import argparse
from pathlib import Path


def download_and_parse(signed_url):
    """Download and parse a signed URL"""
    response = requests.get(signed_url, timeout=30)
    response.raise_for_status()
    return response.json()


def ms_to_timestamp(ms):
    """Convert milliseconds to timestamp format"""
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_video_analysis(result, output_file=None):
    """
    Format audio/video analysis results.

    Args:
        result: Complete API response (dict or JSON file path)
        output_file: Output file path; prints to console if None
    """
    if isinstance(result, str):
        with open(result, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
    else:
        result_data = result

    output = []

    # 1. Video summary
    if "summary" in result_data and result_data["summary"]:
        try:
            summary_data = download_and_parse(result_data["summary"][0])
            output.append("=" * 50)
            output.append("Video Summary")
            output.append("=" * 50)
            output.append("")

            for item in summary_data:
                if "Text" in item:
                    output.append(item["Text"])
                    output.append("")
        except Exception as e:
            output.append(f"Failed to fetch video summary: {e}")
            output.append("")

    # 2. Keywords
    if "keywords" in result_data and result_data["keywords"]:
        try:
            keywords_data = download_and_parse(result_data["keywords"][0])
            output.append("=" * 50)
            output.append("Keywords")
            output.append("=" * 50)
            keywords_str = " | ".join([f"#{kw}" for kw in keywords_data])
            output.append(keywords_str)
            output.append("")
        except Exception as e:
            output.append(f"Failed to fetch keywords: {e}")
            output.append("")

    # 3. Transcript
    if "transcript" in result_data and result_data["transcript"]:
        try:
            transcript_data = download_and_parse(result_data["transcript"][0])
            output.append("=" * 50)
            output.append("Transcript")
            output.append("=" * 50)
            output.append("")

            for item in transcript_data:
                start_time = ms_to_timestamp(item["TimeRange"][0])
                end_time = ms_to_timestamp(item["TimeRange"][1])
                speaker_id = item.get("SpeakerId", "unknown")
                speaker_short = speaker_id.split("-")[-1][:8] if "-" in speaker_id else speaker_id[:8]

                output.append(f"[{start_time} - {end_time}] Speaker {speaker_short}:")
                output.append(item.get("Content", ""))
                output.append("")
        except Exception as e:
            output.append(f"Failed to fetch transcript: {e}")
            output.append("")

    # 4. Transcript summary
    if "transcript_summaries" in result_data and result_data["transcript_summaries"]:
        try:
            transcript_summary_data = download_and_parse(result_data["transcript_summaries"][0])
            output.append("=" * 50)
            output.append("Transcript Summary")
            output.append("=" * 50)
            output.append("")

            for item in transcript_summary_data:
                text = item.get("Text", "")
                if text:
                    output.append(text)
                    output.append("")
        except Exception as e:
            output.append(f"Failed to fetch transcript summary: {e}")
            output.append("")

    # 5. Chapter summaries (with time ranges)
    if "chapter_summaries" in result_data and result_data["chapter_summaries"]:
        try:
            chapters_data = download_and_parse(result_data["chapter_summaries"][0])
            output.append("=" * 50)
            output.append("Chapter Summaries")
            output.append("=" * 50)
            output.append("")

            for chapter in chapters_data:
                title = chapter.get('Title', 'Untitled')
                time_range = chapter.get('TimeRange', [0, 0])
                start_time = ms_to_timestamp(time_range[0])
                end_time = ms_to_timestamp(time_range[1])

                output.append(f"> {title} [{start_time} - {end_time}]")
                output.append("-" * 40)

                for item in chapter.get("Summary", []):
                    text = item.get("Text")
                    if text:
                        output.append(f"  {text}")
                        output.append("")

                    img = item.get("Image")
                    if img:
                        output.append(f"  Image: {img.get('ImagePath', 'unknown path')}")
                        output.append("")

                output.append("")
        except Exception as e:
            output.append(f"Failed to fetch chapter summaries: {e}")
            output.append("")

    # 6. Transcript chapter summaries
    if "transcript_chapter_summaries" in result_data and result_data["transcript_chapter_summaries"]:
        try:
            transcript_chapters_data = download_and_parse(result_data["transcript_chapter_summaries"][0])
            output.append("=" * 50)
            output.append("Transcript Chapter Summaries")
            output.append("=" * 50)
            output.append("")

            for chapter in transcript_chapters_data:
                title = chapter.get('Title', 'Untitled')
                time_range = chapter.get('TimeRange', [0, 0])
                start_time = ms_to_timestamp(time_range[0])
                end_time = ms_to_timestamp(time_range[1])

                output.append(f"> {title} [{start_time} - {end_time}]")
                output.append("-" * 40)

                for item in chapter.get("Summary", []):
                    text = item.get("Text")
                    if text:
                        output.append(f"  {text}")
                        output.append("")

                output.append("")
        except Exception as e:
            output.append(f"Failed to fetch transcript chapter summaries: {e}")
            output.append("")

    # 7. PPT details
    if "ppt_details" in result_data and result_data["ppt_details"]:
        try:
            ppt_data = download_and_parse(result_data["ppt_details"][0])
            output.append("=" * 50)
            output.append("PPT Extraction")
            output.append("=" * 50)
            output.append("")

            for i, ppt in enumerate(ppt_data, 1):
                page_num = ppt.get("PPTShotIndex", i - 1) + 1
                start_time = ms_to_timestamp(ppt.get("StartTime", 0))
                image_path = ppt.get("ImagePath", "unknown path")

                output.append(f"Page {page_num} (appears at: {start_time})")
                output.append(f"Image path: {image_path}")
                output.append("")
        except Exception as e:
            output.append(f"Failed to fetch PPT details: {e}")
            output.append("")

    # 8. Guiding questions
    if "questions" in result_data and result_data["questions"]:
        try:
            qa_data = download_and_parse(result_data["questions"][0])
            output.append("=" * 50)
            output.append("Guiding Questions")
            output.append("=" * 50)
            output.append("")

            for i, qa in enumerate(qa_data, 1):
                output.append(f"Q{i}: {qa.get('Question', 'N/A')}")
                output.append(f"A{i}: {qa.get('Answer', 'N/A')}")
                output.append("")
        except Exception as e:
            output.append(f"Failed to fetch guiding questions: {e}")
            output.append("")

    # 9. Image list
    if "images" in result_data and result_data["images"]:
        output.append("=" * 50)
        output.append("Image List")
        output.append("=" * 50)
        output.append("")

        for img_path, img_info in result_data["images"].items():
            output.append(f"  {img_path}")
            if "url" in img_info:
                output.append(f"   URL: {img_info['url']}")
            if "thumbnail" in img_info:
                output.append(f"   Thumbnail: {img_info['thumbnail']}")
            output.append("")

    formatted_output = "\n".join(output)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted_output)
        print(f"Formatted result saved to: {output_file}")
    else:
        print(formatted_output)

    return formatted_output


def main():
    parser = argparse.ArgumentParser(
        description='PDS Audio/Video Analysis Result Formatter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python video_analysis_formatter.py result.json
  python video_analysis_formatter.py result.json -o formatted_output.txt
        """
    )

    parser.add_argument(
        'input_file',
        help='JSON result file path from the analysis API'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output file path (prints to console by default)'
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"File not found: {args.input_file}")
        return 1

    try:
        format_video_analysis(args.input_file, args.output)
        return 0
    except Exception as e:
        print(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
