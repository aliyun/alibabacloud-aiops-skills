#!/usr/bin/env python3
"""Credential pre-check and account trace label.

Runs the plugin-mode identity call (`aliyun sts get-caller-identity`) so that
every report can state which account the read-only evidence came from. Only the
default credential chain of the aliyun CLI is used; this module never handles,
reads, stores or prints an AccessKey pair, and it never asks the customer for
one.

Usage:
    python scripts/sts_token.py [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import CliError, call_caller_identity, new_session_id  # noqa: E402
from _constants import STS_API_VERSION  # noqa: E402


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
# --- end hygiene

def resolve_identity(session_id):
    """Return the caller identity payload, or raise CliError with CLI guidance."""
    payload = call_caller_identity(session_id)
    if not isinstance(payload, dict):
        raise CliError("UnexpectedIdentityShape", "identity call did not return an object")
    return payload


def account_label(identity):
    """Short trace label: account id when present, otherwise a stable fallback."""
    account_id = identity.get("AccountId") or identity.get("accountId") or ""
    identity_type = identity.get("IdentityType") or identity.get("identityType") or ""
    if not account_id:
        return "account:unknown"
    return f"account:{account_id}" + (f" ({identity_type})" if identity_type else "")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check credentials via the default chain")
    parser.add_argument("--json", action="store_true", help="print the raw identity payload")
    args = parser.parse_args(argv)

    session_id = new_session_id()
    try:
        identity = resolve_identity(session_id)
    except CliError as exc:
        if exc.is_permission_denied():
            print(
                "STATUS: FAIL\n"
                "NEXT_ACTION: The identity call was refused (NoPermission / ImplicitDeny). "
                "Attach the read-only actions listed in references/ram-policies.md to the "
                "RAM principal, then re-run.",
                file=sys.stderr,
            )
        else:
            print(
                "STATUS: FAIL\n"
                "NEXT_ACTION: No usable credential was found. Run `aliyun configure` so the "
                "default credential chain resolves; do not paste keys into this session.",
                file=sys.stderr,
            )
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(identity, indent=2, ensure_ascii=False))
    else:
        print(f"STS identity check: OK (product sts, version {STS_API_VERSION})")
        print(f"  {account_label(identity)}")
        for key in ("Arn", "UserId", "PrincipalId", "RoleId"):
            if identity.get(key):
                print(f"  {key}: {identity[key]}")
        print("STATUS: OK")
        print("NEXT_ACTION: Run scripts/image_cross_account_check.py with --region-id.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
