#!/usr/bin/env python3
"""
Live stream recorder.

Supports:
- Recording a live stream to MP4/FLV/HLS formats
- On-demand snapshots
- Duration-limited recording
- Recording state management

All results are emitted as JSON with top-level overall_status / severity /
summary fields so that both non-technical users and downstream agents can
consume them directly.
"""

import argparse
import glob
import json
import os
import signal
import subprocess
import sys
import tempfile
from datetime import datetime


# Recording process management (simple implementation: PID file)
RECORD_DIR = os.path.join(os.getcwd(), "outputs", "recordings")
SNAPSHOT_DIR = os.path.join(os.getcwd(), "outputs", "snapshots")

# How long to observe the ffmpeg child before declaring the recording alive.
LIVENESS_PROBE_SECONDS = 1.8

FFMPEG_INSTALL_HINT = (
    "STRONGLY RECOMMENDED: install ffmpeg "
    "(macOS: brew install ffmpeg; Linux: apt install ffmpeg or yum install ffmpeg)"
)


def ffmpeg_available():
    """Return True when the ffmpeg binary can be found and executed."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _emit_ffmpeg_missing(action, url):
    """Emit a friendly JSON error when ffmpeg is missing and exit 1.

    Called before any output path or PID file is touched, so a missing
    ffmpeg never leaves partial files behind.
    """
    result = {
        "action": action,
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "status": "failed",
        "error": (
            "ffmpeg is not installed on this machine; recording and snapshot "
            "are completely unavailable without ffmpeg"
        ),
        "overall_status": "failed",
        "severity": "critical",
        "summary": (
            f"The {action} could not start because ffmpeg is not installed. "
            "Recording and snapshot are completely unavailable without ffmpeg. "
            f"Next: {FFMPEG_INSTALL_HINT} and retry."
        ),
        "fix": FFMPEG_INSTALL_HINT,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(1)


def ensure_dirs():
    """Ensure the output directories exist."""
    os.makedirs(RECORD_DIR, exist_ok=True)
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def get_default_output(format_type="mp4"):
    """Generate a default output file name."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(RECORD_DIR, f"live_{ts}.{format_type}")


def extract_key_error_lines(stderr_text, max_lines=3):
    """Extract the most informative error lines from ffmpeg stderr.

    Prefers lines containing common error markers; falls back to the last
    few lines. Avoids blind mid-word truncation of the raw stderr tail.
    """
    lines = [l.strip() for l in (stderr_text or "").splitlines() if l.strip()]
    markers = (
        "error", "failed", "invalid", "could not", "no such",
        "refused", "denied", "timeout", "timed out", "unreachable",
    )
    key = [l for l in lines if any(m in l.lower() for m in markers)]
    chosen = key[-max_lines:] if key else lines[-max_lines:]
    return chosen


def _remove_pid_file(pid_file):
    """Remove a PID file if it exists (best effort)."""
    try:
        if pid_file and os.path.isfile(pid_file):
            os.remove(pid_file)
    except OSError:
        pass


def _read_recorded_pids():
    """Return {pid: pid_file} for all .pid files under RECORD_DIR."""
    recorded = {}
    for pid_file in glob.glob(os.path.join(RECORD_DIR, "*.pid")):
        try:
            with open(pid_file, "r") as f:
                recorded[int(f.read().strip())] = pid_file
        except (ValueError, OSError):
            continue
    return recorded


def _list_active_recordings():
    """List recordings whose PID file exists and whose process is alive."""
    active = []
    for pid, pid_file in _read_recorded_pids().items():
        try:
            os.kill(pid, 0)  # existence probe only, no signal sent
            active.append({"pid": pid, "pid_file": pid_file})
        except ProcessLookupError:
            continue
        except PermissionError:
            active.append({"pid": pid, "pid_file": pid_file})
    return active


def cmd_record(args):
    """Start recording a live stream."""
    if not ffmpeg_available():
        _emit_ffmpeg_missing("record", args.url)

    url = args.url
    output = args.output or get_default_output(args.format)
    duration = args.duration
    format_type = args.format

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    # Build the ffmpeg command
    cmd = ["ffmpeg", "-y", "-i", url]

    # Choose parameters based on the output format
    if format_type == "mp4":
        cmd.extend(["-c", "copy", "-movflags", "+frag_keyframe", "-f", "mp4"])
    elif format_type == "flv":
        cmd.extend(["-c", "copy", "-f", "flv"])
    elif format_type == "hls":
        hls_dir = output.replace(".m3u8", "")
        os.makedirs(hls_dir, exist_ok=True)
        cmd.extend([
            "-c", "copy",
            "-f", "hls",
            "-hls_time", "10",
            "-hls_list_size", "0",
            "-hls_segment_filename", os.path.join(hls_dir, "seg_%05d.ts"),
        ])
    elif format_type == "ts":
        cmd.extend(["-c", "copy", "-f", "mpegts"])

    # Optional duration limit
    if duration:
        cmd.extend(["-t", str(duration)])

    cmd.append(output)

    result = {
        "action": "record",
        "url": url,
        "output": output,
        "format": format_type,
        "duration": f"{duration}s" if duration else "unlimited",
        "cmd": " ".join(cmd),
        "timestamp": datetime.now().isoformat(),
    }

    if args.dry_run:
        result["status"] = "dry_run"
        result["overall_status"] = "ok"
        result["severity"] = "info"
        result["summary"] = "Dry run: the ffmpeg command was shown but not executed. Remove --dry-run to start recording."
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    pid_file = output + ".pid"

    # ffmpeg stderr goes to a temp file: a long recording would otherwise
    # fill a pipe buffer and deadlock the child, while the file still lets
    # us extract the root cause when ffmpeg exits immediately.
    stderr_fd, stderr_path = tempfile.mkstemp(prefix="ffmpeg_record_", suffix=".log")

    try:
        # Use Popen so the recording can be interrupted.
        # Recording is intentionally long-running; no timeout applies.
        with os.fdopen(stderr_fd, "w") as stderr_fh:
            proc = subprocess.Popen(  # noqa: timeout
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=stderr_fh,
            )

        # Liveness check: an unreachable stream makes ffmpeg exit almost
        # immediately, so wait briefly and only report "recording" if the
        # process is still alive.
        try:
            exit_code = proc.wait(timeout=LIVENESS_PROBE_SECONDS)
        except subprocess.TimeoutExpired:
            exit_code = None  # still running -> alive

        if exit_code is not None:
            # ffmpeg already exited: the recording never started.
            try:
                with open(stderr_path, "r", errors="replace") as f:
                    stderr_text = f.read()
            except OSError:
                stderr_text = ""
            key_lines = extract_key_error_lines(stderr_text)
            _remove_pid_file(pid_file)
            result["status"] = "failed"
            result["exit_code"] = exit_code
            result["error"] = "; ".join(key_lines) if key_lines else f"ffmpeg exited immediately with code {exit_code}"
            result["overall_status"] = "failed"
            result["severity"] = "critical"
            result["summary"] = (
                "Recording failed because the stream could not be opened. "
                "Next: verify the stream URL is correct and the stream is currently live."
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)

        # The process is alive: the recording really is in progress.
        result["pid"] = proc.pid
        result["status"] = "recording"
        result["message"] = f"Recording... PID={proc.pid}, press Ctrl+C to stop"
        result["overall_status"] = "ok"
        result["severity"] = "info"
        result["summary"] = (
            f"Recording is in progress (PID {proc.pid}). "
            "It stops automatically when --duration elapses, or press Ctrl+C / use the stop command."
        )

        # Save the PID to a file only after the liveness check passed
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))

        # Emit status
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Wait for the recording to finish or for user interruption.
        # Intentionally unbounded; bounded by the user or --duration.
        proc.wait()  # noqa: timeout

        # Clean up the PID file after a normal exit
        _remove_pid_file(pid_file)
        if proc.returncode != 0:
            print(
                f"[warn] ffmpeg exited with code {proc.returncode} before the recording completed",
                file=sys.stderr,
            )
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n[info] Interrupt received, stopping the recording...", file=sys.stderr)
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # SIGTERM was not enough; force-kill the recording process.
            proc.kill()
            proc.wait(timeout=5)
        _remove_pid_file(pid_file)
        print(f"[info] Recording stopped, file: {output}", file=sys.stderr)

    except FileNotFoundError:
        _remove_pid_file(pid_file)
        result["status"] = "failed"
        result["error"] = "ffmpeg is not installed; please install ffmpeg via your package manager"
        result["overall_status"] = "failed"
        result["severity"] = "critical"
        result["summary"] = "Recording failed because ffmpeg is not installed. Next: install ffmpeg and retry."
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    except Exception as e:
        _remove_pid_file(pid_file)
        result["status"] = "error"
        result["error"] = str(e)
        result["overall_status"] = "failed"
        result["severity"] = "high"
        result["summary"] = "Recording failed due to an unexpected error. Next: check the error detail and retry."
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    finally:
        try:
            os.remove(stderr_path)
        except OSError:
            pass


def cmd_snapshot(args):
    """Capture a snapshot frame."""
    if not ffmpeg_available():
        _emit_ffmpeg_missing("snapshot", args.url)

    url = args.url
    output = args.output or os.path.join(
        SNAPSHOT_DIR,
        f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    )

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", url,
        "-frames:v", "1",
        "-q:v", "2",
        output,
    ]

    result = {
        "action": "snapshot",
        "url": url,
        "output": output,
        "timestamp": datetime.now().isoformat(),
    }

    if args.dry_run:
        result["status"] = "dry_run"
        result["cmd"] = " ".join(cmd)
        result["overall_status"] = "ok"
        result["severity"] = "info"
        result["summary"] = "Dry run: the ffmpeg command was shown but not executed. Remove --dry-run to capture."
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    exit_code = 0

    # Capture the snapshot
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0 and os.path.isfile(output):
            result["status"] = "captured"
            result["file_size"] = os.path.getsize(output)
            result["overall_status"] = "ok"
            result["severity"] = "info"
            result["summary"] = f"Snapshot captured successfully and saved to {output}."
        else:
            key_lines = extract_key_error_lines(proc.stderr)
            result["status"] = "failed"
            result["error"] = "; ".join(key_lines) if key_lines else "Unknown error"
            result["overall_status"] = "failed"
            result["severity"] = "high"
            result["summary"] = (
                "Snapshot failed. Next: verify the stream URL is correct and the stream is currently live."
            )
            exit_code = 1
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["error"] = "Snapshot timed out; check whether the live stream is reachable"
        result["overall_status"] = "failed"
        result["severity"] = "high"
        result["summary"] = "Snapshot timed out. Next: check whether the live stream is reachable and retry."
        exit_code = 1
    except FileNotFoundError:
        result["status"] = "error"
        result["error"] = "ffmpeg is not installed; please install ffmpeg via your package manager"
        result["overall_status"] = "failed"
        result["severity"] = "critical"
        result["summary"] = "Snapshot failed because ffmpeg is not installed. Next: install ffmpeg and retry."
        exit_code = 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    if exit_code:
        sys.exit(exit_code)


def cmd_stop(args):
    """Stop a recording.

    Safety rule: a numeric id is only honored when it matches the PID
    recorded in a .pid file under outputs/recordings/; arbitrary PIDs are
    never signaled. Use --all to stop every active recording.
    """
    timestamp = datetime.now().isoformat()

    if args.all:
        active = _list_active_recordings()
        stopped = []
        for rec in active:
            try:
                os.kill(rec["pid"], signal.SIGTERM)
                stopped.append(rec["pid"])
                _remove_pid_file(rec["pid_file"])
            except ProcessLookupError:
                _remove_pid_file(rec["pid_file"])
        result = {
            "action": "stop",
            "status": "stopped" if stopped else "not_found",
            "stopped_pids": stopped,
            "timestamp": timestamp,
            "overall_status": "ok" if stopped else "warning",
            "severity": "info",
            "summary": (
                f"Stopped {len(stopped)} recording(s)."
                if stopped else
                "No active recordings were found; nothing was stopped."
            ),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if not stopped:
            sys.exit(1)
        return

    recording_id = args.recording_id
    if not recording_id:
        result = {
            "action": "stop",
            "status": "error",
            "error": "Provide --recording-id <PID_OR_PIDFILE> or --all",
            "timestamp": timestamp,
            "overall_status": "failed",
            "severity": "low",
            "summary": "No target given. Next: pass --recording-id, or use --all to stop every active recording.",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    recorded = _read_recorded_pids()

    is_recorded_pid = recording_id.isdigit() and int(recording_id) in recorded

    if os.path.isfile(recording_id) or is_recorded_pid:
        # Explicit PID file path, or a PID recorded by this tool
        pid_file = recording_id if os.path.isfile(recording_id) else recorded[int(recording_id)]
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
        except (ValueError, OSError):
            pid = None

        if pid is None:
            result = {
                "action": "stop",
                "recording_id": recording_id,
                "status": "not_found",
                "timestamp": timestamp,
                "overall_status": "failed",
                "severity": "low",
                "summary": "The PID file could not be read. Next: use --all or check active recordings.",
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)

        try:
            os.kill(pid, signal.SIGTERM)
            _remove_pid_file(pid_file)
            result = {
                "action": "stop",
                "pid": pid,
                "status": "stopped",
                "timestamp": timestamp,
                "overall_status": "ok",
                "severity": "info",
                "summary": f"Recording stopped (PID {pid}).",
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except ProcessLookupError:
            _remove_pid_file(pid_file)
            result = {
                "action": "stop",
                "pid": pid,
                "status": "process_not_found",
                "timestamp": timestamp,
                "overall_status": "warning",
                "severity": "low",
                "summary": "The recorded process is no longer running; the stale PID file was cleaned up.",
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Numeric id that does NOT match any recorded .pid file: refuse to
    # signal an arbitrary PID.
    if recording_id.lstrip("-").isdigit():
        active = _list_active_recordings()
        result = {
            "action": "stop",
            "recording_id": recording_id,
            "status": "not_found",
            "error": (
                "This PID is not registered as a recording started by this tool; "
                "signaling arbitrary PIDs is not allowed."
            ),
            "active_recordings": active,
            "timestamp": timestamp,
            "overall_status": "failed",
            "severity": "low",
            "summary": (
                "No matching recording was found, so nothing was stopped. "
                "Next: use stop --all, or check the active_recordings list for valid ids."
            ),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    result = {
        "action": "stop",
        "recording_id": recording_id,
        "status": "not_found",
        "timestamp": timestamp,
        "overall_status": "failed",
        "severity": "low",
        "summary": "No matching recording was found. Next: use stop --all or check active recordings.",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Live stream recording / snapshot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # record
    p_record = subparsers.add_parser("record", help="Record a live stream")
    p_record.add_argument("--url", required=True, help="Live stream URL")
    p_record.add_argument("--output", default=None, help="Output file path (auto-generated by default)")
    p_record.add_argument("--duration", type=int, default=None, help="Recording duration in seconds (unlimited by default)")
    p_record.add_argument("--format", default="mp4", choices=["mp4", "flv", "hls", "ts"],
                          help="Recording format (default mp4)")
    p_record.add_argument("--dry-run", action="store_true", help="Show the command without executing")
    p_record.set_defaults(func=cmd_record)

    # snapshot
    p_snap = subparsers.add_parser("snapshot", help="Capture a snapshot frame")
    p_snap.add_argument("--url", required=True, help="Live stream URL")
    p_snap.add_argument("--output", default=None, help="Output image path (auto-generated by default)")
    p_snap.add_argument("--dry-run", action="store_true", help="Show the command without executing")
    p_snap.set_defaults(func=cmd_snapshot)

    # stop
    p_stop = subparsers.add_parser("stop", help="Stop a recording")
    p_stop.add_argument(
        "--recording-id", default=None,
        help="Recording PID file path, or a PID previously recorded by this tool",
    )
    p_stop.add_argument("--all", action="store_true", help="Stop every active recording")
    p_stop.set_defaults(func=cmd_stop)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
