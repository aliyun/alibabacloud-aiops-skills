from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

try:
    from .references.observability import ObservabilitySessionError, skill_session_id
except ImportError:  # pragma: no cover - direct script execution
    from references.observability import ObservabilitySessionError, skill_session_id


def agenthub_script_path() -> Path:
    return (Path(__file__).resolve().parents[1] / "agenthub.py").resolve()


def format_agenthub_command(
    *arguments: str,
    python_executable: str | None = None,
) -> str:
    executable = (
        python_executable
        or os.environ.get("AGENTHUB_PYTHON", "").strip()
        or sys.executable
    )
    command = [executable, str(agenthub_script_path()), *arguments]
    try:
        session_id = skill_session_id()
    except ObservabilitySessionError:
        return shlex.join(command)
    return shlex.join(["env", f"SKILL_SESSION_ID={session_id}", *command])
