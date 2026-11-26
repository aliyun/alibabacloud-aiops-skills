"""Build versioned User-Agent attribution from the manifest without identity or credentials in session IDs."""

import os
from pathlib import Path
import re
import stat
import uuid

from context_graph_contract import SkillError, parse_json


SKILL_NAME = "alibabacloud-dataworks-context-graph"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "references" / "manifest.json"
MAX_MANIFEST_BYTES = 16 * 1024
_PROCESS_SESSION_ID = uuid.uuid4().hex
_VERSION = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def manifest_version():
    """Read the actual manifest for each new transport through bounded regular-file access; errors expose no content."""
    descriptor = None
    try:
        # Check the fixed package path first; nonblocking and nofollow flags add protection where available.
        initial = MANIFEST_PATH.lstat()
        if not stat.S_ISREG(initial.st_mode) or not 0 < initial.st_size <= MAX_MANIFEST_BYTES:
            raise ValueError
        descriptor = os.open(MANIFEST_PATH, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
                             | getattr(os, "O_NOFOLLOW", 0))
        actual = os.fstat(descriptor)
        if not stat.S_ISREG(actual.st_mode) or not 0 < actual.st_size <= MAX_MANIFEST_BYTES:
            raise ValueError
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            content = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(content) > MAX_MANIFEST_BYTES:
            raise ValueError
        manifest = parse_json(content.decode("utf-8"))
        if not isinstance(manifest, dict) or manifest.get("name") != SKILL_NAME:
            raise ValueError
        version = manifest.get("version")
        if not isinstance(version, str) or len(version) > 64 or not _VERSION.fullmatch(version):
            raise ValueError
        return version
    except (OSError, ValueError, UnicodeError, RecursionError, SkillError):
        raise SkillError("SkillManifestInvalid", "Skill manifest is missing or invalid.") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def validate_session_id(value):
    """Require a host-generated 32-character lowercase hexadecimal session ID without echoing invalid values."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise SkillError("InvalidSessionId", "Skill session ID must be 32 lowercase hexadecimal characters.")
    return value


def user_agent(session_id=None):
    """Reuse the process-random identifier by default and always derive the version from the bundled manifest."""
    session = _PROCESS_SESSION_ID if session_id is None else validate_session_id(session_id)
    version = manifest_version()
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session} skill-version/{version}"
