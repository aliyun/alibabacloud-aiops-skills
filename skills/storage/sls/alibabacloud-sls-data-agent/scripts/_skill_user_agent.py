"""Bind request attribution to this installed Skill and one conversation session."""

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_ENV = "ALIBABACLOUD_SLS_DATA_AGENT_SESSION"


class AttributionError(ValueError):
    pass


def _identity():
    try:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError
        frontmatter = text.split("---", 2)[1]
        names = re.findall(r"^name:\s*([a-z0-9-]+)\s*$", frontmatter, re.MULTILINE)
        if len(names) != 1:
            raise ValueError
        manifest = json.loads((ROOT / "references/manifest.json").read_text(encoding="utf-8"))
        version = manifest.get("version") if isinstance(manifest, dict) else None
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
            raise ValueError
    except (OSError, UnicodeError, ValueError):
        raise AttributionError("Cannot read this Skill's frontmatter name and valid references/manifest.json version.") from None
    return names[0], version


def new_session():
    """Return a local binding for the Agent to reuse throughout this conversation."""
    name, _ = _identity()
    return {"name": name, "root": str(ROOT), "sessionId": secrets.token_hex(16)}


def user_agent():
    # Reread the installed manifest, including after switching back to this Skill.
    name, version = _identity()
    try:
        context = json.loads(os.environ.get(CONTEXT_ENV, ""))
        if (not isinstance(context, dict) or set(context) != {"name", "root", "sessionId"}
                or context["name"] != name or context["root"] != str(ROOT)
                or not isinstance(context["sessionId"], str)
                or not re.fullmatch(r"[0-9a-f]{32}", context["sessionId"])):
            raise ValueError
    except (ValueError, TypeError):
        raise AttributionError("Provide this Skill's conversation binding through " + CONTEXT_ENV + "; create it once with scripts/_skill_user_agent.py init.") from None
    return f"AlibabaCloud-Agent-Skills/{name}/{context['sessionId']} skill-version/{version}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("init", "user-agent"),
                        help="Initialize one local conversation binding, or resolve the current binding's User-Agent")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(new_session(), separators=(",", ":")) if args.operation == "init" else user_agent())
    except AttributionError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
