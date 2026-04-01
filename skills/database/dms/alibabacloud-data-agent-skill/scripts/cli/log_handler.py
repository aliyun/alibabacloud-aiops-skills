"""Structured logging handler for Data Agent.

Provides logging to plain text format only (progress.jsonl disabled).
"""

import json
from pathlib import Path
from datetime import datetime
from typing import TextIO, Optional, Dict, Any


class StructuredLogHandler:
    """Handles logging to plain text format only (JSONL logging disabled)."""

    def __init__(self, session_dir: Path, log_prefix: str = "progress"):
        """Initialize the log handler (JSONL logging disabled).

        Args:
            session_dir: Directory for the session where logs will be stored.
            log_prefix: Prefix for log files (e.g., "progress" for progress.log, or "process" for process.log)
        """
        self.session_dir = session_dir
        self.log_prefix = log_prefix
        self.progress_log_path = session_dir / f"{log_prefix}.log"
        # JSONL logging disabled - progress.jsonl creation is skipped
        # self.progress_jsonl_path = session_dir / f"{log_prefix}.jsonl"

        # Open only the plain text log file
        self.progress_log_file: Optional[TextIO] = None
        # JSONL logging disabled
        # self.progress_jsonl_file: Optional[TextIO] = None

    def __enter__(self):
        """Enter context manager, opening log file."""
        # Ensure directory exists
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Open only the plain text log file
        self.progress_log_file = open(self.progress_log_path, "w", encoding="utf-8")
        # JSONL logging disabled

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager, closing log file."""
        if self.progress_log_file:
            self.progress_log_file.close()
        # JSONL logging disabled

    def write_log(self, text: str):
        """Write text to the plain log file (e.g., progress.log or process.log).

        Args:
            text: Text to write to the plain text log.
        """
        if self.progress_log_file:
            self.progress_log_file.write(text)
            self.progress_log_file.flush()  # Ensure immediate write

    def write_jsonl(self, data: Dict[str, Any]):
        """Write structured data to the JSONL file (disabled).

        Args:
            data: Dictionary containing structured log data.
        """
        # JSONL logging is disabled - do nothing
        pass

    def write_both(self, text: str, data: Optional[Dict[str, Any]] = None):
        """Write to plain text log only (JSONL logging disabled).

        Args:
            text: Text to write to the plain text log.
            data: Structured data (ignored since JSONL logging is disabled).
        """
        self.write_log(text)

        # JSONL logging disabled - data parameter is ignored

    def close(self):
        """Close the plain text log file handle (JSONL logging disabled)."""
        if self.progress_log_file:
            self.progress_log_file.close()
            self.progress_log_file = None
        # JSONL logging disabled