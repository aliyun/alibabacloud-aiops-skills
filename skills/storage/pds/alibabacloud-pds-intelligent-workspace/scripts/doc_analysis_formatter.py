#!/usr/bin/env python3
"""
PDS Document Analysis Result Formatter

Downloads and parses signed files, then formats document analysis results.
Supports full-text summary, chapter summaries, keywords, guiding questions, etc.

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


def format_document_analysis(result, output_file=None):
    """
    Format document analysis results.

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

    # 1. Full-text summary
    if "summary" in result_data and result_data["summary"]:
        try:
            summary_data = download_and_parse(result_data["summary"][0])
            output.append("=" * 50)
            output.append("Full-Text Summary")
            output.append("=" * 50)
            output.append("")

            for item in summary_data:
                if "Text" in item:
                    output.append(item["Text"])
                    output.append("")
                if "Image" in item:
                    img = item["Image"]
                    page_num = img.get('PageNumber', 0) + 1
                    output.append(f"Image: {img['ImagePath']} (page {page_num})")
                    output.append("")
        except Exception as e:
            output.append(f"Failed to fetch full-text summary: {e}")
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

    # 3. Chapter summaries
    if "chapter_summaries" in result_data and result_data["chapter_summaries"]:
        try:
            chapters_data = download_and_parse(result_data["chapter_summaries"][0])
            output.append("=" * 50)
            output.append("Chapter Summaries")
            output.append("=" * 50)
            output.append("")

            for chapter in chapters_data:
                title = chapter.get('Title', 'Untitled')
                output.append(f"> {title}")
                output.append("-" * 40)

                for item in chapter.get("Summary", []):
                    text = item.get("Text") or item.get("text")
                    if text:
                        output.append(f"  {text}")
                        output.append("")

                    img = item.get("Image") or item.get("image")
                    if img:
                        output.append(f"  Image: {img.get('ImagePath', 'unknown path')}")
                        output.append("")

            output.append("")
        except Exception as e:
            output.append(f"Failed to fetch chapter summaries: {e}")
            output.append("")

    # 4. Guiding questions
    if "guiding_questions" in result_data and result_data["guiding_questions"]:
        try:
            qa_data = download_and_parse(result_data["guiding_questions"][0])
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

    # 5. Paper-specific fields (optional)
    for field_name, field_label in [
        ("method_description", "Method Description"),
        ("experiment_description", "Experiment Description"),
        ("conclusion_description", "Conclusion Description")
    ]:
        if field_name in result_data and result_data[field_name]:
            try:
                desc_data = download_and_parse(result_data[field_name][0])
                output.append("=" * 50)
                output.append(f"{field_label}")
                output.append("=" * 50)
                output.append("")

                description = desc_data.get("Description", [])
                for item in description:
                    text = item.get("text")
                    if text:
                        output.append(text)
                        output.append("")

                    img = item.get("image")
                    if img:
                        output.append(f"Image: {img.get('ImagePath', 'unknown path')}")
                        output.append("")
            except Exception as e:
                output.append(f"Failed to fetch {field_label}: {e}")
                output.append("")

    # 6. Image list
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
        description='PDS Document Analysis Result Formatter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python doc_analysis_formatter.py result.json
  python doc_analysis_formatter.py result.json -o formatted_output.txt
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
        format_document_analysis(args.input_file, args.output)
        return 0
    except Exception as e:
        print(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
