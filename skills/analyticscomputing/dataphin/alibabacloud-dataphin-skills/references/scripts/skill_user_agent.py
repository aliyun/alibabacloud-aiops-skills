"""Build the suite UA from the installed manifest, without cloud dependencies."""
import argparse
import json
import os
from pathlib import Path
import re

MANIFEST = Path(__file__).resolve().parents[1] / "manifest.json"
SKILL_NAME = "alibabacloud-dataphin-skills"
SEMVER = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def load_version():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("name") != SKILL_NAME:
        raise ValueError("manifest.name must identify " + SKILL_NAME)
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError("manifest.version must be a non-empty semantic version")
    return version


def build_user_agent(session_id=None):
    if session_id is None:
        session_id = os.environ.get("SKILL_SESSION_ID", "")
    if not isinstance(session_id, str) or not re.fullmatch(r"[0-9a-f]{32}", session_id):
        raise ValueError("SKILL_SESSION_ID must be the inherited 32-character lowercase hex session ID")
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id} skill-version/{load_version()}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", help="Session ID inherited from the parent skill")
    parser.add_argument("--version", action="store_true", help="Print the validated manifest version")
    args = parser.parse_args()
    try:
        print(load_version() if args.version else build_user_agent(args.session_id))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Cannot initialize skill User-Agent: {exc}\n")


if __name__ == "__main__":
    main()
