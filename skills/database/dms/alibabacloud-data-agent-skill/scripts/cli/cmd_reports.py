"""Reports subcommand to list and download generated files.

Author: Tinker
Created: 2026-03-11
"""

import argparse
import sys
from pathlib import Path
import time

from data_agent import (
    DataAgentConfig,
    DataAgentClient,
    FileManager,
)


def cmd_reports(args: argparse.Namespace) -> None:
    """Handle reports subcommand."""
    session_id = args.session_id
    session_dir = Path(f"sessions/{session_id}")
    report_dir = session_dir / "reports"

    print(f"Fetching generated files for session {session_id}...")

    # Initialize components
    config = DataAgentConfig.from_env()
    client = DataAgentClient(config)
    file_manager = FileManager(client)

    total_reports = 0
    categories = ("WebReport", "TextReport", "DefaultArtifact")

    found_files = []

    for category in categories:
        try:
            files = file_manager.list_files(session_id, file_category=category)
            if files:
                found_files.extend([(category, rf) for rf in files])
        except Exception as e:
            print(f"  Warning: could not list {category}: {e}", file=sys.stderr)
            continue

    if not found_files:
        print("No report files found for this session.")
        print("Note: Reports are usually generated in ANALYSIS or INSIGHT modes.")
        return

    report_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading files to {report_dir.resolve()}...\n")

    for category, rf in found_files:
        if not rf.download_url:
            print(f"  [{category}] {rf.filename or rf.file_id}: No download URL available")
            continue

        save_path = report_dir / (rf.filename or f"{rf.file_id}.bin")
        try:
            print(f"  Downloading [{category}] {rf.filename or rf.file_id}...")
            file_manager.download_from_url(rf.download_url, str(save_path))
            print(f"  ✅ Saved to {save_path.resolve()}")
            total_reports += 1
        except Exception as e:
            print(f"  ❌ Failed to download {rf.filename or rf.file_id} ({category}): {e}", file=sys.stderr)

    if total_reports > 0:
        print(f"\nSuccessfully downloaded {total_reports} files.")
