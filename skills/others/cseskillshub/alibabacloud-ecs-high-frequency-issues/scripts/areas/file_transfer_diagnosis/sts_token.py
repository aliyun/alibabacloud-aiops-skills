#!/usr/bin/env python3
"""Credential and identity preflight for this skill.

Resolves the caller identity from the ambient CLI credential chain so evidence
reports can carry the account the queries ran against. Run directly:

    python scripts/areas/file_transfer_diagnosis/sts_token.py

Exit code is 0 when the identity resolves, 1 when it degrades. This module
never accepts, reads, prints or stores a long-term key or secret: the CLI
profile is the only supported credential source.
"""

import sys

import _cli
import _constants as C

ACCOUNT_IDENTITY_FIELDS = ("AccountId", "UserId", "Arn", "IdentityType")


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

def resolve_identity(session_id=None):
    """Return a dict with the caller identity, or raise ``_cli.CliError``."""
    payload = _cli.call_plugin("sts", "GetCallerIdentity",
                              session_id=session_id)
    identity = {}
    for field in ACCOUNT_IDENTITY_FIELDS:
        value = payload.get(field)
        if value:
            identity[field] = str(value)
    if not identity:
        raise _cli.CliError("EmptyIdentity",
                            "the identity call returned no account fields")
    identity["UidTag"] = "uid-{0}".format(identity.get("AccountId", "unknown"))
    return identity


def format_identity(identity):
    lines = ["Caller identity"]
    for field in ACCOUNT_IDENTITY_FIELDS:
        if field in identity:
            lines.append("  {0}: {1}".format(field, identity[field]))
    if "UidTag" in identity:
        lines.append("  Traceability tag: {0}".format(identity["UidTag"]))
    return "\n".join(lines)


def main():
    session_id = _cli.new_session_id()
    print("session id: {0}".format(session_id))
    print("user-agent: {0}".format(_cli.user_agent(session_id)))

    if not _cli.cli_available():
        print("The Alibaba Cloud CLI executable was not found on PATH.")
        print("Install and configure the CLI, then re-run this script.")
        print(C.STATUS_FAIL)
        print("NEXT_ACTION: Install the Alibaba Cloud CLI and run "
              "`aliyun sts get-caller-identity` with a profile; do not pass credentials to "
              "this skill.")
        return 1

    try:
        identity = resolve_identity(session_id=session_id)
    except _cli.CliError as error:
        print(format_error(error))
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: Configure a CLI profile with `aliyun sts get-caller-identity`, "
              "or attach an instance RAM role, then re-run. Reports can still "
              "be produced with an explicit --account-note, but the account "
              "the evidence came from will be unverified.")
        return 1

    print(format_identity(identity))
    print(C.STATUS_OK)
    print("NEXT_ACTION: Run `python scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py "
          "collect --region-id <region> --instance-id <id>` to gather "
          "evidence.")
    return 0


def format_error(error):
    lines = ["Identity preflight failed: {0}".format(error)]
    if _cli.is_permission_error(str(error)):
        lines.append(
            "The credential in use lacks the sts:GetCallerIdentity permission "
            "or is denied by policy (NoPermission / ImplicitDeny).")
        lines.append("Attach the minimal policy in "
                     "references/ram-policies.md to the calling identity.")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
