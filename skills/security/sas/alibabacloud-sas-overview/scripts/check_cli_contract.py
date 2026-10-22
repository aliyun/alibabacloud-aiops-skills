#!/usr/bin/env python3
"""Check documented API command names/flags against CLI help; never query cloud data."""
import argparse
import json
from pathlib import Path
import re
import subprocess

try:
    from .user_agent import build_user_agent
except ImportError:
    from user_agent import build_user_agent

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {"sas": "2018-12-03", "waf-openapi": "2021-10-01", "bssopenapi": "2017-12-14"}


def documented_commands(text):
    negative, shell = False, False
    for line in text.replace("\\\n", " ").splitlines():
        if line.startswith("#") and not shell:
            negative = "INCORRECT" in line
        if line.startswith("```"):
            shell = not shell and line.strip() in ("```bash", "```shell", "```sh")
            continue
        if not shell or negative or line.lstrip().startswith("#"):
            continue
        match = re.search(r"\baliyun\s+(sas|waf-openapi|bssopenapi)\s+([\w-]+)\b", line)
        if match:
            yield match.group(1), match.group(2), set(re.findall(r"--[A-Za-z][A-Za-z0-9-]*", line))


def validate_help(product, action, flags, help_text):
    errors = []
    if f"aliyun {product} {action} [parameters]" not in help_text:
        errors.append("missing command usage; a version banner alone is not valid help")
    if f"API Version: {VERSIONS[product]}" not in help_text:
        errors.append("wrong or missing API version")
    # --user-agent is accepted by the CLI dispatcher but omitted from generated help.
    supported = set(re.findall(r"--[A-Za-z][A-Za-z0-9-]*", help_text)) | {"--user-agent"}
    if flags - supported:
        errors.append("unknown flags: " + ", ".join(sorted(flags - supported)))
    required = set(re.findall(r"^\s+(--[\w-]+)\s+\w+ \(required\)", help_text, re.M))
    if "--help" not in flags and required - flags:
        errors.append("missing required flags: " + ", ".join(sorted(required - flags)))
    if "--user-agent" not in flags:
        errors.append("missing session User-Agent")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--help-dir", type=Path, help="Use previously captured help for offline checks")
    args = parser.parse_args()
    try:
        user_agent = build_user_agent()
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"checked_commands": 0, "failures": {"user-agent": [str(exc)]}}))
        return 1
    used = {}
    for path in [ROOT / "SKILL.md", *sorted((ROOT / "references").glob("*.md"))]:
        for product, action, flags in documented_commands(path.read_text()):
            used.setdefault((product, action), []).append(flags)
    # The pagination helper builds this call dynamically; include its argument contract.
    used.setdefault(("sas", "describe-cloud-center-instances"), []).append(
        {"--region", "--machine-types", "--current-page", "--page-size", "--user-agent"})
    failures = {}
    for (product, action), invocations in sorted(used.items()):
        try:
            if args.help_dir:
                help_text = (args.help_dir / f"{product}-{action}.txt").read_text()
            else:
                result = subprocess.run(["aliyun", product, action, "--help", "--user-agent", user_agent],
                                        capture_output=True, text=True, timeout=30)
                if result.returncode:
                    raise ValueError(f"help exited {result.returncode}")
                help_text = result.stdout
            errors = sorted({error for flags in invocations
                             for error in validate_help(product, action, flags, help_text)})
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            errors = [str(exc)]
        if errors:
            failures[f"{product} {action}"] = errors
    print(json.dumps({"checked_commands": len(used), "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
