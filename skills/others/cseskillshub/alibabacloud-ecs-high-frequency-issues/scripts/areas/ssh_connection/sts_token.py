"""Credential preflight for the ECS SSH connection diagnosis skill.

Runs ``aliyun sts get-caller-identity`` through the shared CLI layer to prove the
default credential chain works and to derive the traceability tag
(``uid:<AccountId>``) printed in every report. The instance-ownership check that
follows in the entry script depends on this: an instance that belongs to another
account is invisible to these calls, and saying so early saves a whole session of
dead-end investigation.

Usage::

    python scripts/areas/ssh_connection/sts_token.py            # human readable
    python scripts/areas/ssh_connection/sts_token.py --json     # machine readable
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import CliError, AliyunCli, dig, minimal_policy_snippet  # noqa: E402
from _constants import STS_IDENTITY_COMMAND, STS_PRODUCT  # noqa: E402

REQUIRED_HINT = (
    "sts GetCallerIdentity needs no ECS permission; a failure here means the "
    "credentials themselves are unusable, not that a policy is missing."
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

def fetch_identity(cli: Optional[AliyunCli] = None) -> Dict[str, Any]:
    """Return account id, user id and ARN for the active credentials."""
    cli = cli or AliyunCli()
    payload = cli.call(STS_PRODUCT, STS_IDENTITY_COMMAND, {})
    account_id = dig(payload, ("AccountId", "accountId", "AccountID"))
    return {
        "account_id": str(account_id or ""),
        "user_id": str(dig(payload, ("UserId", "userId")) or ""),
        "arn": str(dig(payload, ("Arn", "arn")) or ""),
        "session_id": cli.session_id,
        "user_agent": cli.user_agent,
    }


def uid_tag(identity: Dict[str, Any]) -> str:
    """Traceability tag: the calling account, never a credential value."""
    return "uid:%s" % (identity.get("account_id") or "unknown")


def failure_guidance(error: CliError) -> str:
    lines = [
        "STATUS: FAIL",
        "NEXT_ACTION: fix the local CLI profile, then re-run this preflight",
        "",
        "Call to %s %s failed with code %s." % (
            STS_PRODUCT, STS_IDENTITY_COMMAND, error.code),
        REQUIRED_HINT,
        "",
        "Do this by hand (this skill never reads, prints or transmits an "
        "AccessKey pair; it only uses the default credential chain):",
        "  1. Run 'aliyun sts get-caller-identity --profile <name>' and point it at a valid "
        "RAM identity, or export ALIBABA_CLOUD_PROFILE.",
        "  2. If the identity exists but is denied, it needs at minimum:",
        minimal_policy_snippet(["sts:GetCallerIdentity"]),
        "  3. A denial is reported by the service as NoPermission or ImplicitDeny "
        "- attach the missing action, do not broaden to a full product policy.",
    ]
    return "\n".join(lines)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON instead of text")
    args = parser.parse_args(argv)

    cli = AliyunCli()
    try:
        identity = fetch_identity(cli)
    except CliError as error:
        if args.as_json:
            json.dump({"ok": False, "code": error.code,
                       "message": error.message}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(failure_guidance(error) + "\n")
        return 2

    if not identity["account_id"]:
        sys.stderr.write("[WARN] GetCallerIdentity answered without an "
                         "AccountId field; ownership checks will be limited.\n")

    if args.as_json:
        json.dump({"ok": True, "uid_tag": uid_tag(identity), **identity},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(
            "Credentials OK\n"
            "  account   : %s\n"
            "  caller    : %s\n"
            "  arn       : %s\n"
            "  trace tag : %s\n"
            "  session   : %s\n"
            "  user-agent: %s\n" % (
                identity["account_id"] or "(not returned)",
                identity["user_id"] or "(not returned)",
                identity["arn"] or "(not returned)",
                uid_tag(identity),
                identity["session_id"],
                identity["user_agent"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
