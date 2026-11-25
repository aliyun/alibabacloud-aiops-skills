#!/usr/bin/env python3
"""Identity pre-check for the ECS website build guide skill.

Runs the plugin-mode command ``aliyun sts get-caller-identity`` through the
shared CLI layer and reports the caller's account id, which is used only as a
traceability label on the read-only inventory so a report can be tied back to
the account it was produced under.

This script performs no change of any kind and never touches credential values:
the CLI resolves credentials from its own default chain. On failure it prints
the returned error code (``NoPermission``, ``ImplicitDeny``, or a
credential-chain problem) and tells the operator to configure the CLI in their
own environment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from . import _cli, _constants as C
except ImportError:  # pragma: no cover - direct execution
    import _cli
    import _constants as C


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

def verify(profile=None, timeout=None):
    """Return ``{"account_id", "arn", "identity_type"}`` for the caller.

    Raises :class:`_cli.CliError` when the identity call cannot be completed.
    """
    argv = list(C.STS_CALLER_IDENTITY_CMD)
    if profile:
        argv += ["--profile", profile]
    body = _cli.decode_json(_cli.run_cli(argv, timeout=timeout), "GetCallerIdentity")
    return {
        "account_id": body.get("AccountId") or body.get("accountId") or "",
        "arn": body.get("Arn") or body.get("arn") or "",
        "identity_type": body.get("IdentityType") or "",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify the CLI identity used for the read-only queries."
    )
    parser.add_argument("--profile", help="Optional named CLI credential profile.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=C.DEFAULT_TIMEOUT,
        help="Per-call timeout in seconds (default: {}).".format(C.DEFAULT_TIMEOUT),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    try:
        identity = verify(profile=args.profile, timeout=args.timeout)
    except _cli.CliError as exc:
        payload = {
            "STATUS": C.STATUS_FAIL,
            "NEXT_ACTION": (
                "Configure the Alibaba Cloud CLI default credential chain by "
                "running 'aliyun configure' in your own environment, then re-run "
                "this pre-check. Do not paste credential values into the "
                "conversation. If the code is NoPermission or ImplicitDeny, "
                "apply the read-only policy documented in "
                "references/ram-policies.md."
            ),
            "error": str(exc),
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("{} {}".format(C.WARN_PREFIX, payload["error"]), file=sys.stderr)
            print("STATUS: {}".format(payload["STATUS"]))
            print("NEXT_ACTION: {}".format(payload["NEXT_ACTION"]))
        return 1

    payload = {
        "STATUS": C.STATUS_OK,
        "account_id": identity["account_id"],
        "arn": identity["arn"],
        "user_agent": _cli.build_user_agent(),
        "session_id": _cli.SESSION_ID,
        "NEXT_ACTION": (
            "Run scripts/website_build_guide.py --region-id <region> for the "
            "read-only deployment inventory."
        ),
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("Account ID label: {}".format(identity["account_id"] or "(not returned)"))
        print("Caller ARN      : {}".format(identity["arn"] or "(not returned)"))
        print("Session id      : {}".format(_cli.SESSION_ID))
        print("User-Agent      : {}".format(payload["user_agent"]))
        print("STATUS: {}".format(C.STATUS_OK))
        print("NEXT_ACTION: {}".format(payload["NEXT_ACTION"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
