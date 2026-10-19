"""Resolve this skill's version and generate a fresh session User-Agent."""

import json
import secrets
from pathlib import Path


def main():
    manifest_path = Path(__file__).resolve().parents[1] / "references" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Cannot read skill manifest: {exc}") from exc
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not version or any(c.isspace() for c in version):
        raise SystemExit("Skill manifest version must be a non-empty string without whitespace")
    print(
        "AlibabaCloud-Agent-Skills/alibabacloud-sls-index-config-management/"
        f"{secrets.token_hex(16)} skill-version/{version}"
    )


if __name__ == "__main__":
    main()
