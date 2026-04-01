"""Simple dual logging for Data Agent sessions.

This module provides functionality to create both progress.log and progress.jsonl files.
"""
import subprocess
from pathlib import Path
from datetime import datetime
import json
from typing import Optional


def run_with_dual_logging(cmd, session_dir: Path, env=None):
    """Run a subprocess and create both progress.log and progress.jsonl files."""
    session_dir.mkdir(parents=True, exist_ok=True)

    # Run the subprocess with output redirected to a temporary file
    temp_output_path = session_dir / "temp_output.txt"

    with open(temp_output_path, 'w', encoding='utf-8') as temp_file:
        proc = subprocess.Popen(
            cmd,
            stdout=temp_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env
        )
        proc.wait()

    # After subprocess completes, process the output to create both log files
    process_output_to_dual_logs(temp_output_path, session_dir)

    # Clean up temporary file
    temp_output_path.unlink(missing_ok=True)

    return proc


def process_output_to_dual_logs(temp_output_path: Path, session_dir: Path):
    """Process the temporary output file and create log format only (progress.jsonl disabled)."""
    progress_log_path = session_dir / "progress.log"
    # progress_jsonl_path = session_dir / "progress.jsonl"  # Disabled per user request

    with open(temp_output_path, 'r', encoding='utf-8') as temp_file:
        content = temp_file.read()

    # Write to progress.log as-is
    with open(progress_log_path, 'w', encoding='utf-8') as log_file:
        log_file.write(content)

    # JSONL logging disabled - progress.jsonl creation is skipped
    # Process content for progress.jsonl (skipped)