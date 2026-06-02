#!/usr/bin/env python3
"""
PDS Archive Download Async Task Poller

Automatically polls PDS archive download task status until completion and returns the download URL.
"""

import subprocess
import json
import time
import sys
from datetime import datetime


class PDSArchivePoller:
    """PDS archive download task poller"""

    def __init__(self, async_task_id, max_attempts=60, poll_interval=5):
        self.async_task_id = async_task_id
        self.max_attempts = max_attempts
        self.poll_interval = poll_interval
        self.download_url = None

    def poll(self):
        """
        Poll archive download task status.

        Returns:
            str: Download URL, or None if failed
        """
        print("=" * 60)
        print("Starting archive download task polling")
        print("=" * 60)
        print(f"Async Task ID: {self.async_task_id}")
        print(f"Max Attempts: {self.max_attempts}")
        print(f"Poll Interval: {self.poll_interval}s")
        print()

        cmd = [
            "aliyun", "pds", "get-async-task",
            "--async-task-id", str(self.async_task_id),
            "--user-agent", "AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace"
        ]

        attempt = 0
        while attempt < self.max_attempts:
            attempt += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Attempt {attempt}/{self.max_attempts}...")

            try:
                proc_result = subprocess.run(
                    cmd,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except subprocess.TimeoutExpired:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] Request timed out, retrying...")
                time.sleep(self.poll_interval)
                continue

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
            except json.JSONDecodeError as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] JSON parse failed: {e}")
                print(f"  Raw output: {proc_result.stdout[:200]}")
                print()
                print("=" * 60)
                print("Error encountered, stopping poll")
                print("=" * 60)
                return None

            state = response.get("state", "")

            if state == "Succeed":
                self.download_url = response.get("url", "")
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] Archive task completed!")
                print(f"  Download URL: {self.download_url}")
                print()
                print("=" * 60)
                print("Archive download task completed successfully")
                print("=" * 60)
                return self.download_url

            elif state == "Failed":
                message = response.get("message", "unknown error")
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] Task failed: {message}")
                print()
                print("=" * 60)
                print("Archive download task failed")
                print("=" * 60)
                return None

            else:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"  [{timestamp}] Task state: {state}, waiting {self.poll_interval}s before retry...")
                time.sleep(self.poll_interval)

        print()
        print("=" * 60)
        print("Max attempts exceeded, task may still be in progress")
        print(f"   Retry later with the same async_task_id: {self.async_task_id}")
        print("=" * 60)
        return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description='PDS Archive Download Async Task Poller')
    parser.add_argument('--async-task-id', required=True, help='Async task ID')
    parser.add_argument('--max-attempts', type=int, default=60, help='Max polling attempts (default: 60)')
    parser.add_argument('--poll-interval', type=int, default=5, help='Poll interval in seconds (default: 5)')

    args = parser.parse_args()

    poller = PDSArchivePoller(
        async_task_id=args.async_task_id,
        max_attempts=args.max_attempts,
        poll_interval=args.poll_interval
    )

    url = poller.poll()

    if not url:
        sys.exit(1)


if __name__ == "__main__":
    main()
