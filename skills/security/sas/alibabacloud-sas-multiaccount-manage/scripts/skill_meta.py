#!/usr/bin/env python3
"""Skill identity helpers: manifest-derived name/version and session-scoped User-Agent."""

import json
import os
import uuid
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = SKILL_ROOT / "manifest.json"
DEFAULT_SKILL_NAME = "alibabacloud-sas-multiaccount-manage"
DEFAULT_SKILL_VERSION = "0.1.0"
SESSION_ID_ENV = "SKILL_SESSION_ID"
UA_PREFIX = "AlibabaCloud-Agent-Skills"

_session_id = None


def load_manifest():
    """Read manifest.json from the skill root; return an empty dict on failure."""
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get_session_id():
    """Return the current session ID, generating a UUID4 if none is configured.

    Set SKILL_SESSION_ID to share one ID across multiple script invocations in
    the same agent session; otherwise each process gets its own.
    """
    global _session_id
    if _session_id is None:
        _session_id = os.environ.get(SESSION_ID_ENV) or uuid.uuid4().hex
    return _session_id


def build_user_agent_header():
    """Build the User-Agent header: AlibabaCloud-Agent-Skills/{name}/{session-id} skill-version/{version}."""
    manifest = load_manifest()
    name = manifest.get("name") or DEFAULT_SKILL_NAME
    version = manifest.get("version") or DEFAULT_SKILL_VERSION
    return (
        f"User-Agent={UA_PREFIX}/{name}/{get_session_id()}"
        f" skill-version/{version}"
    )
