#!/usr/bin/env python3
"""
sts_token.py -- credential pre-flight and account provenance label
==================================================================
SECURITY: This skill is strictly READ-ONLY. This script only calls the
read action sts:GetCallerIdentity through the shared CLI layer. Credentials
come exclusively from the aliyun CLI default credential chain; this script
never reads, prompts for, prints, or stores key material. Only the public
account id (a label, not a secret) is cached, in a dotfile with 0600 mode,
so reports can state which account the evidence was collected under.

Usage:
    python3 scripts/areas/console_resource_lookup/sts_token.py [--json] [--refresh] [--profile NAME]

Exit codes: 0 = identity resolved (OK or DEGRADED cache read), 1 = FAIL
(no usable credential; the printed NEXT_ACTION guides `aliyun sts get-caller-identity`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import _cli
from _cli import CliError

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          ".sts_cache.json")


# --- customer-facing hygiene (P0-2): never print a raw UID / InvokeId / session id
import re as _re
import sys as _sys


def _mask_pii(text):
    if not isinstance(text, str):
        return text
    text = _re.sub(r"(?<!\d)(1\d{15})(?!\d)", lambda m: "****" + m.group(1)[-4:], text)
    text = _re.sub(r"\bt-([a-z0-9]{6,})\b", lambda m: "t-****" + m.group(1)[-4:], text)
    text = _re.sub(r"\b([0-9a-f]{32})\b", lambda m: "****" + m.group(1)[-4:], text)
    return text


class _MaskedStdout(object):
    def __init__(self, stream):
        self._stream = stream

    def write(self, data):
        return self._stream.write(_mask_pii(data))

    def __getattr__(self, name):
        return getattr(self._stream, name)


_sys.stdout = _MaskedStdout(_sys.stdout)
# stderr is read back by the agent on some transports; mask it too.
_sys.stderr = _MaskedStdout(_sys.stderr)
# --- end hygiene

def _load_cache() -> dict:
    try:
        with open(CACHE_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and data.get("account_id"):
            return data
    except (OSError, ValueError):
        pass
    return {}


def _store_cache(data: dict) -> None:
    """Cache the PUBLIC account id only, with owner-only file mode."""
    try:
        tmp = CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.chmod(tmp, 0o600)
        os.replace(tmp, CACHE_FILE)
    except OSError as exc:
        print(f"[WARN] could not write the identity cache: {exc}",
              file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the active credential via sts:GetCallerIdentity "
                    "and print the account provenance label.")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON instead of text")
    parser.add_argument("--refresh", action="store_true",
                        help="ignore the cache and re-query")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI profile name")
    args = parser.parse_args()

    _cli.check_cli_available()

    if not args.refresh:
        cached = _load_cache()
        if cached:
            _out(args.json, cached, "DEGRADED",
                 "cached identity; run again with --refresh to re-query")
            return 0

    status, body, err = "OK", {}, ""
    try:
        body = _cli.call("sts", "GetCallerIdentity", {}, profile=args.profile)
    except (CliError, ValueError) as exc:
        status, err = "FAIL", str(exc)

    if status == "OK":
        data = {
            "account_id": str(body.get("AccountId", "") or ""),
            "caller": str(body.get("Arn", "") or ""),
            "identity_type": str(body.get("IdentityType", "") or ""),
        }
        _store_cache(data)
        _out(args.json, data, status,
             "credentials verified; every lookup report carries this "
             "account provenance")
        return 0

    print(f"[WARN] GetCallerIdentity failed: {err}", file=sys.stderr)
    _out(args.json, {}, status,
         "the default credential chain is not usable: ask the user to run "
         "`aliyun sts get-caller-identity` (never collect key material in chat), then "
         "retry this pre-flight")
    return 1


def _out(as_json: bool, data: dict, status: str, next_action: str) -> None:
    if as_json:
        print(json.dumps({"status": status, "identity": data,
                          "next_action": next_action}, ensure_ascii=False,
                         indent=2))
    else:
        print(f"Account ID    : {data.get('account_id') or 'unresolved'}")
        print(f"Caller ARN    : {data.get('caller') or 'unresolved'}")
        print(f"STATUS: {status}")
        print(f"NEXT_ACTION: {next_action}")


if __name__ == "__main__":
    sys.exit(main())
