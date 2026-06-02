#!/usr/bin/env python3
"""
PDS Document/Video Analysis Poll Processor

Automatically polls PDS analysis tasks until completion and returns all results.
Supports document analysis (doc/analysis) and video analysis (video/analysis).
"""

import subprocess
import json
import time
import sys
from pathlib import Path
from datetime import datetime


class PDSPollProcessor:
    """PDS analysis task poll processor"""

    def __init__(self, drive_id, file_id, revision_id, x_pds_process="doc/analysis",
                 max_attempts=30, output_dir="/tmp"):
        self.drive_id = drive_id
        self.file_id = file_id
        self.revision_id = revision_id
        self.process_type = x_pds_process
        self.max_attempts = max_attempts
        self.output_dir = Path(output_dir)
        self.result = None

        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def poll_analysis(self):
        """
        Poll analysis task status until completion.

        Returns:
            dict: Analysis result, or None if failed
        """
        print("=" * 60)
        print(f"Starting {self.process_type} analysis task polling")
        print("=" * 60)
        print(f"Drive ID: {self.drive_id}")
        print(f"File ID: {self.file_id}")
        print(f"Revision ID: {self.revision_id}")
        print(f"Process Type: {self.process_type}")
        print(f"Max Attempts: {self.max_attempts}")
        print()

        cmd = [
            "aliyun",
            "pds",
            "process",
            "--resource-type", "file",
            "--drive-id", str(self.drive_id),
            "--file-id", str(self.file_id),
            "--revision-id", str(self.revision_id),
            "--x-pds-process", str(self.process_type),
            "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace"
        ]
        
        attempt = 0
        while attempt < self.max_attempts:
            attempt += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Attempt {attempt}/{self.max_attempts}...")

            proc_result = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if proc_result.returncode != 0:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] Request failed")
                print(f"     Error: {proc_result.stderr.strip()}")
                print()
                print("=" * 60)
                print("Error encountered, stopping poll")
                print("=" * 60)
                return None

            try:
                response = json.loads(proc_result.stdout)

                retry_after = response.get('retry_after') or response.get('retry_time')
                if retry_after is not None:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"  [{timestamp}] Processing, waiting {retry_after}s before retry...")
                    time.sleep(retry_after)
                    continue

                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] Analysis completed!")
                self.result = response
                return response

            except json.JSONDecodeError as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] JSON parse failed: {e}")
                print(f"  Raw output: {proc_result.stdout[:200]}")
                print()
                print("=" * 60)
                print("Error encountered, stopping poll")
                print("=" * 60)
                return None
            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] Error occurred: {e}")
                print()
                print("=" * 60)
                print("Error encountered, stopping poll")
                print("=" * 60)
                return None

        print()
        print("=" * 60)
        print("Max attempts exceeded, analysis may still be in progress")
        print("=" * 60)
        return None
    
    def save_raw_result(self, filename=None):
        """
        Save raw JSON result (contains signed URLs, does not download content).

        Returns:
            str: Saved file path, or None if no result
        """
        if self.result is None:
            print("No result to save")
            return None

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "doc" if self.process_type == "doc/analysis" else "video"
            filename = f"{prefix}_analysis_{timestamp}.json"

        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.result, f, ensure_ascii=False, indent=2)

        print(f"Raw result saved to: {filepath}")
        return str(filepath)
    



def main():
    import argparse

    parser = argparse.ArgumentParser(description='PDS Document/Video Analysis Poll Processor')
    parser.add_argument('--drive-id', required=True, help='Drive ID')
    parser.add_argument('--file-id', required=True, help='File ID')
    parser.add_argument('--revision-id', required=True, help='File revision ID')
    parser.add_argument('--x-pds-process', required=True,
                       choices=['doc/analysis', 'video/analysis'],
                       help='Process type: doc/analysis or video/analysis')
    parser.add_argument('--max-attempts', type=int, default=30, help='Max polling attempts')
    parser.add_argument('--output-dir', default='/tmp', help='Output directory')
    parser.add_argument('-o', '--output', help='Output filename, saved to --output-dir (default: /tmp)')

    args = parser.parse_args()

    processor = PDSPollProcessor(
        drive_id=args.drive_id,
        file_id=args.file_id,
        revision_id=args.revision_id,
        x_pds_process=args.x_pds_process,
        max_attempts=args.max_attempts,
        output_dir=args.output_dir
    )

    result = processor.poll_analysis()

    if result:
        processor.save_raw_result(args.output)
    else:
        print("\nAnalysis task failed or was interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
