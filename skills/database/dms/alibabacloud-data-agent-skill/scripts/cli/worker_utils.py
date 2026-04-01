"""Common utilities for async worker management in Data Agent CLI."""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from cli.worker_lock import write_worker_pid, check_worker_lock
from data_agent import (
    DataAgentConfig,
    DataAgentClient,
    SessionManager,
    MessageHandler,
)


def is_worker_process() -> bool:
    """Check if this is a worker process."""
    return os.environ.get("DATA_AGENT_ASYNC_WORKER") == "1"


def get_worker_session_details() -> tuple[str, str]:
    """Get session and agent IDs from environment variables in worker process."""
    session_id = os.environ["DATA_AGENT_SESSION_ID"]
    agent_id = os.environ.get("DATA_AGENT_AGENT_ID", "")
    return session_id, agent_id


def initialize_components() -> tuple:
    """Initialize common Data Agent components."""
    config = DataAgentConfig.from_env()
    client = DataAgentClient(config)
    session_manager = SessionManager(client)
    message_handler = MessageHandler(client)
    return config, client, session_manager, message_handler


def setup_async_worker(
    args: object,
    session,
    additional_env_vars: Optional[Dict[str, str]] = None
) -> None:
    """Setup and run async worker process.

    Args:
        args: Command line arguments
        session: Session object containing session_id and agent_id
        additional_env_vars: Additional environment variables to set
    """
    session_id = session.session_id
    session_dir = Path(f"sessions/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)

    # Check for existing worker
    existing_pid = check_worker_lock(session_dir)
    if existing_pid:
        print(f"⚠️  A worker process (PID {existing_pid}) is already running for session {session_id}.", file=sys.stderr)
        print(f"   Check progress: cat sessions/{session_id}/progress.log", file=sys.stderr)
        print(f"   Current status: {(session_dir / 'status.txt').read_text().strip() if (session_dir / 'status.txt').exists() else 'unknown'}", file=sys.stderr)
        sys.exit(1)

    # Save input.json
    input_data = vars(args).copy()
    input_data.pop("func", None)
    with open(session_dir / "input.json", "w", encoding="utf-8") as f:
        json.dump(input_data, f, ensure_ascii=False, indent=2)

    # Write status.txt
    with open(session_dir / "status.txt", "w", encoding="utf-8") as f:
        f.write("running")

    # Construct worker command
    cmd = [sys.executable] + [arg for arg in sys.argv if arg != "--async-run"]
    env = os.environ.copy()
    env["DATA_AGENT_ASYNC_WORKER"] = "1"
    env["DATA_AGENT_SESSION_ID"] = session_id
    env["DATA_AGENT_AGENT_ID"] = session.agent_id

    # Set additional environment variables if provided
    if additional_env_vars:
        env.update(additional_env_vars)

    # Make sure PYTHONIOENCODING is set so unicode is flushed properly
    env["PYTHONIOENCODING"] = "utf-8"
    # Force unbuffered output so logs appear immediately
    env["PYTHONUNBUFFERED"] = "1"

    # Start the subprocess in background and immediately write the PID
    # Worker will redirect its own stdout to progress.log
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,  # Worker handles its own logging
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env
    )

    # Write PID immediately after starting the process
    write_worker_pid(session_dir, proc.pid)

    # For true async behavior, we return immediately without waiting
    # The actual logging will be handled by the worker process itself
    print(f"\n✅ Async task started. Session ID: {session_id}")
    print(f"Check progress at: sessions/{session_id}/progress.log")

    sys.exit(0)


def handle_worker_completion(session_dir: Path, need_confirm: bool = False, error: Optional[Exception] = None) -> None:
    """Handle worker process completion by updating status files.

    Args:
        session_dir: Session directory path
        need_confirm: Whether user confirmation is needed
        error: Exception object if there was an error, None otherwise
    """
    if error:
        # Error occurred
        with open(session_dir / "status.txt", "w", encoding="utf-8") as f:
            f.write("failed")
        with open(session_dir / "result.json", "w", encoding="utf-8") as f:
            json.dump({"status": "failed", "error": str(error)}, f)
    elif need_confirm:
        # Need user confirmation
        with open(session_dir / "status.txt", "w", encoding="utf-8") as f:
            f.write("waiting_input")
        with open(session_dir / "result.json", "w", encoding="utf-8") as f:
            json.dump({"status": "waiting_input"}, f)
    else:
        # Success
        with open(session_dir / "status.txt", "w", encoding="utf-8") as f:
            f.write("completed")
        with open(session_dir / "result.json", "w", encoding="utf-8") as f:
            json.dump({"status": "completed"}, f)