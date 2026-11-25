#!/usr/bin/env python3
"""Caller identity through the customer's own credential chain.

Read-only helper: it answers "which account and identity am I looking at" so a finding can
carry a traceable tag, and it fails loudly with configure guidance instead of asking for any
credential material.

    python3 scripts/sts_token.py
    python3 scripts/sts_token.py --format json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import CliError, call, new_session_id, warn
from _constants import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    STS_API_VERSION,
    STS_CALLER_IDENTITY,
    STS_PRODUCT,
)


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

def _short(value, keep=4):
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= keep * 2:
        return "***"
    return "{0}***{1}".format(text[:keep], text[-keep:])


def fetch_caller(session_id=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Return ``{account_id, caller_id, identity_arn, trace_tag, session_id}``.

    Raises :class:`CliError` when the identity read cannot be made.
    """
    sid = session_id or new_session_id()
    body = call(STS_PRODUCT, STS_CALLER_IDENTITY, {}, session_id=sid, timeout=timeout)
    account_id = body.get("AccountId") or body.get("AccountUid") or ""
    caller_id = body.get("UserId") or body.get("PrincipalId") or ""
    identity_arn = body.get("Arn") or ""
    tag = "acct:{0}".format(_short(account_id)) if account_id else "acct:unresolved"
    if caller_id:
        tag = "{0}/principal:{1}".format(tag, _short(caller_id))
    return {
        "account_id": str(account_id),
        "caller_id": str(caller_id),
        "identity_arn": str(identity_arn),
        "trace_tag": tag,
        "session_id": sid,
    }


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only caller identity check for the disk encryption guide skill.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help="per-call timeout in seconds (default {0}, max {1})".format(
                            DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS))
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    timeout = max(1, min(int(args.timeout), MAX_TIMEOUT_SECONDS))
    try:
        identity = fetch_caller(timeout=timeout)
    except CliError as exc:
        warn("{0} -> configure a CLI profile with your own credentials, then retry; "
             "this skill never asks for an access key pair.".format(exc))
        print("STATUS: FAIL")
        print("NEXT_ACTION: Ask the customer to run `aliyun configure` for the profile that "
              "owns the target resources, then re-run the identity check.")
        return 1
    if args.format == "json":
        print(json.dumps({"identity": identity, "apiVersion": STS_API_VERSION},
                         indent=2, sort_keys=True))
    else:
        print("Account    : {0}".format(identity["trace_tag"]))
        print("Identity   : {0}".format(identity["identity_arn"] or "not returned"))
        print("Session    : {0}".format(identity["session_id"]))
        print("API version: {0}".format(STS_API_VERSION))
        print("STATUS: OK")
        print("NEXT_ACTION: Re-run this read in the region that owns the disks before "
              "quoting any encryption answer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
