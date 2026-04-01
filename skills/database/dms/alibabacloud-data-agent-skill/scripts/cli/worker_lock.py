"""Worker process lock utilities for preventing concurrent workers per session.

Uses a PID file (worker.pid) in the session directory. The parent checks
the lock before spawning; the worker acquires it on start and releases on exit.

Author: Tinker
Created: 2026-03-11
"""

import os
import signal
from pathlib import Path

LOCK_FILENAME = "worker.pid"


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def check_worker_lock(session_dir: Path) -> int | None:
    """Check if a worker is already running for this session.

    Returns the PID of the running worker, or None if no worker is active.
    Stale lock files (dead PID) are automatically cleaned up.
    """
    lock_file = session_dir / LOCK_FILENAME
    if not lock_file.exists():
        return None

    try:
        pid = int(lock_file.read_text().strip())
    except (ValueError, OSError):
        # Corrupt lock file — remove it
        lock_file.unlink(missing_ok=True)
        return None

    if _is_pid_alive(pid):
        return pid

    # Stale lock — process is dead, clean up
    lock_file.unlink(missing_ok=True)
    return None


def acquire_worker_lock(session_dir: Path) -> None:
    """Write the current process PID to the lock file."""
    lock_file = session_dir / LOCK_FILENAME
    lock_file.write_text(str(os.getpid()))


def release_worker_lock(session_dir: Path) -> None:
    """Remove the lock file if it belongs to the current process."""
    lock_file = session_dir / LOCK_FILENAME
    try:
        if lock_file.exists():
            pid = int(lock_file.read_text().strip())
            if pid == os.getpid():
                lock_file.unlink(missing_ok=True)
    except (ValueError, OSError):
        lock_file.unlink(missing_ok=True)


def write_worker_pid(session_dir: Path, pid: int) -> None:
    """Write the spawned worker PID to the lock file (called by parent)."""
    lock_file = session_dir / LOCK_FILENAME
    lock_file.write_text(str(pid))
