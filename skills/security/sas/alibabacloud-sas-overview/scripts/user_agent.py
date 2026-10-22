#!/usr/bin/env python3
"""Build one versioned User-Agent per session from the installed Skill manifest."""
import argparse
import json
from pathlib import Path
import re
import sys
from uuid import UUID, uuid4

MANIFEST = Path(__file__).resolve().parents[1] / "references" / "manifest.json"


def build_user_agent(manifest=MANIFEST, session_id=None):
    data = json.loads(Path(manifest).read_text())
    version = data.get("version") if isinstance(data, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
        raise ValueError("Manifest version must be a non-empty string containing a safe UA token")
    session_id = str(uuid4()) if session_id is None else session_id
    parsed = UUID(session_id)
    if parsed.version != 4 or str(parsed) != session_id:
        raise ValueError("Session ID must be a canonical UUID v4")
    return f"AlibabaCloud-Agent-Skills/alibabacloud-sas-overview/{session_id} skill-version/{version}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", help="Reuse an existing UUID v4 for this session")
    args = parser.parse_args()
    try:
        print(build_user_agent(session_id=args.session_id))
    except (OSError, ValueError, TypeError) as exc:
        print(f"Cannot build User-Agent: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
