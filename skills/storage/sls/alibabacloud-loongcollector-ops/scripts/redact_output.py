#!/usr/bin/env python3
"""redact_output.py — redact secrets before showing command history / logs.

Masks AccessKey IDs/secrets, STS tokens, private keys, bearer tokens and common
credential CLI flags in arbitrary text, so audit output can be shown without
leaking secrets. Never reveals the original value; masks in place preserving a
short hint (first/last chars) only for high-entropy blobs longer than 12 chars.

Protocol: stdout = redacted text (default) or JSON when --json;
          stderr = diagnostics; exit 0 ok (redactions may be 0), 2 usage error.

Usage:
  python3 scripts/redact_output.py --input cmd.log
  echo "aliyun ... --access-key-secret ABCD1234..." | python3 scripts/redact_output.py
  python3 scripts/redact_output.py --input cmd.log --json
"""
import argparse
import json
import os
import re
import sys

# (name, compiled pattern, replacement using group 1 as the kept prefix)
PATTERNS = [
    ("akid_ltai", re.compile(r"\b(LTAI)[A-Za-z0-9]{6,}\b"), r"\1****"),
    ("ak_flag", re.compile(r"(--access-key-(?:id|secret)\s+)(\S+)", re.I), r"\1****"),
    ("sts_flag", re.compile(r"(--sts-token\s+)(\S+)", re.I), r"\1****"),
    ("secret_flag", re.compile(r"(--(?:secret|password|token)\s+)(\S+)", re.I), r"\1****"),
    ("bearer", re.compile(r"(Bearer\s+)([A-Za-z0-9._\-]+)", re.I), r"\1****"),
    ("assignment", re.compile(
        r"((?:access[_-]?key[_-]?secret|secret[_-]?access[_-]?key|"
        r"accesskeysecret|password|passwd|token|sts[_-]?token)"
        r"['\"]?\s*[:=]\s*['\"]?)([^\s'\",}]+)", re.I), r"\1****"),
]
PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.S)


def redact(text):
    count = 0
    if PRIVATE_KEY.search(text):
        text, n = PRIVATE_KEY.subn("-----BEGIN PRIVATE KEY----- ****REDACTED**** -----END PRIVATE KEY-----", text)
        count += n
    for _name, pat, repl in PATTERNS:
        text, n = pat.subn(repl, text)
        count += n
    return text, count


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--input", help="file to redact; omit to read stdin")
    ap.add_argument("--json", action="store_true", help="emit JSON envelope")
    args = ap.parse_args()

    if args.input:
        if not os.path.isfile(args.input):
            sys.stderr.write("[redact_output] file not found: %s\n" % args.input)
            return 2
        with open(args.input, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    else:
        raw = sys.stdin.read()

    redacted, count = redact(raw)

    if args.json:
        out = {
            "tool": "redact_output",
            "session_id": os.environ.get("SKILL_SESSION_ID", ""),
            "status": "ok",
            "redactions": count,
            "text": redacted,
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(redacted)
        if not redacted.endswith("\n"):
            sys.stdout.write("\n")
        sys.stderr.write("[redact_output] %d redaction(s) applied\n" % count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
