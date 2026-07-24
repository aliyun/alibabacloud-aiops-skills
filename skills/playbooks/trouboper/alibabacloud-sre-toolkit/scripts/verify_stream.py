#!/usr/bin/env python3
"""Development verification script for STAROps SSE streaming.

TEST-ONLY / NOT FOR PRODUCTION USE: This script is not part of the runtime
workflow and must never be invoked in production environments.
It launches starops_manager.py as a subprocess to verify streaming behavior.
Arguments are passed as a list (no shell interpolation).

Usage:
    python3 verify_stream.py "<thread-id>" "<question>" --config "<path>" --uid "<uid>"

Principle:
    1. Launch starops_manager.py chat ... --stream via subprocess.Popen
    2. Thread reads stderr (streaming events), main thread waits for stdout (final answer)
    3. Each event is printed with timestamp to verify real-time delivery
"""
import os
import subprocess
import sys
import threading
import time


def main():
    skill_root = os.path.dirname(os.path.abspath(__file__))
    starops_script = os.path.join(skill_root, "starops_manager.py")

    # Validate: ensure no shell metacharacters in arguments (defense in depth)
    for arg in sys.argv[1:]:
        if any(c in arg for c in ";|&$`\\"):
            print(f"ERROR: Invalid character in argument: {arg!r}", file=sys.stderr)
            sys.exit(1)

    # Arguments passed from command line: thread_id question --config ... --uid ...
    cmd = [sys.executable, starops_script, "chat"] + sys.argv[1:] + ["--stream"]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=skill_root,
    )

    # Thread: real-time reading of stderr events
    events_received = []
    first_event_time = None
    last_event_time = None

    def read_stderr():
        nonlocal first_event_time, last_event_time
        for line in iter(proc.stderr.readline, b""):
            ts = time.strftime("%H:%M:%S")
            now = time.monotonic()
            if first_event_time is None:
                first_event_time = now
            last_event_time = now
            text = line.decode("utf-8", errors="replace").rstrip()
            print(f"  [{ts}] {text}", flush=True)
            events_received.append(text)

    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stderr_thread.start()

    # Wait for process to finish
    proc.wait()
    stderr_thread.join(timeout=5)

    # Read stdout final answer
    answer = proc.stdout.read().decode("utf-8", errors="replace").strip()

    # Verification results
    print(f"\n{'='*60}", flush=True)
    print(f"Verification Results", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"Streaming events received: {len(events_received)}", flush=True)
    print(f"First-to-last event span: {last_event_time - first_event_time:.2f}s" if first_event_time and last_event_time else "No events", flush=True)
    print(f"Final answer length: {len(answer)} chars", flush=True)
    print(f"Exit code: {proc.returncode}", flush=True)

    if events_received:
        print(f"\nFirst event: {events_received[0][:80]}", flush=True)
        print(f"Last event: {events_received[-1][:80]}", flush=True)

    print(f"\n--- Final Answer (first 500 chars) ---", flush=True)
    print(answer[:500], flush=True)


if __name__ == "__main__":
    main()
