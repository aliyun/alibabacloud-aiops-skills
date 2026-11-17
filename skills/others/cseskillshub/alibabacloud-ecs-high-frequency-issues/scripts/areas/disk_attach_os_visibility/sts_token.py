#!/usr/bin/env python3
"""Credential pre-flight for this skill: confirm the CLI can call the platform.

Runs the caller-identity API through the account's existing CLI configuration. It never
accepts, reads, stores or echoes an AccessKey pair or a security token: the only
supported path is the default credential chain already configured for the CLI.

Usage:
    python3 scripts/areas/disk_attach_os_visibility/sts_token.py                 # JSON result for the agent to read
    python3 scripts/areas/disk_attach_os_visibility/sts_token.py --quiet         # exit code only
"""

import argparse
import json
import sys
from typing import Any, Dict, Tuple

from _cli import CliError, call, first_value, mask_secrets, new_session_id
from _constants import STS_ACTION_PLUGIN_MODE, STS_PRODUCT, STS_VERSION

configure_hint = (
    "The CLI returned no usable identity. Ask the customer or operator to run "
    "`aliyun sts get-caller-identity` (or attach a RAM role to the machine) and then retry. "
    "Do not ask for, paste, or export an AccessKey pair or a security token anywhere "
    "in this workflow."
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
# stderr is read back by the agent on some transports; mask it too.
_sys.stderr = _MaskedStdout(_sys.stderr)
# --- end hygiene

def fetch_identity(session_id: str, timeout: int, dry_run: bool = False) -> Dict[str, Any]:
    """Return the decoded caller identity payload for this run."""
    return call(STS_PRODUCT, STS_ACTION_PLUGIN_MODE, {}, session_id=session_id,
                timeout=timeout, dry_run=dry_run)


def summarise(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Pick the fields a report may quote, and say whether an identity was proven."""
    account_id = first_value(payload, "AccountId", "Account", default="")
    user_id = first_value(payload, "UserId", "PrincipalId", default="")
    arn = first_value(payload, "Arn", "PrincipalArn", default="")
    identity_ok = bool(account_id or user_id or arn)
    return (
        {
            "account_id_present": bool(account_id),
            "principal_uid": mask_secrets(str(user_id)) if user_id else "",
            "account_label": ("acct-%s" % str(account_id)[-4:]) if account_id else "unknown",
            "principal_arn": mask_secrets(str(arn)) if arn else "",
            "identity_proven": identity_ok,
        },
        identity_ok,
    )


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(description="Verify CLI credentials for this skill.")
    parser.add_argument("--timeout", type=int, default=30, help="Seconds allowed for the identity call.")
    parser.add_argument("--quiet", action="store_true", help="Print nothing; signal the result via the exit code.")
    parser.add_argument("--print-only", action="store_true",
                        help="Show the request that would be sent, without sending it.")
    args = parser.parse_args(argv)

    session_id = new_session_id()
    try:
        payload = fetch_identity(session_id, args.timeout, dry_run=args.print_only)
    except CliError as error:
        if not args.quiet:
            json.dump({
                "ok": False,
                "code": error.code,
                "message": mask_secrets(error.message),
                "permission_failure": error.is_permission_failure,
                "remediation": configure_hint,
                "session_id": session_id,
            }, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        return 2

    if args.print_only:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    summary, identity_ok = summarise(payload)
    summary["ok"] = identity_ok
    summary["session_id"] = session_id
    summary["api"] = "%s/%s %s" % (STS_PRODUCT, STS_VERSION, STS_ACTION_PLUGIN_MODE)
    if not identity_ok:
        summary["remediation"] = configure_hint
    if not args.quiet:
        json.dump(summary, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0 if identity_ok else 2


if __name__ == "__main__":
    sys.exit(main())
