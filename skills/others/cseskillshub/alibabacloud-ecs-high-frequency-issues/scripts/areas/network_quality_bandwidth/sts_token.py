#!/usr/bin/env python3
"""Identity preflight for the diagnosis scripts.

Uses the credential profile already configured for the CLI. Nothing in this module reads,
accepts, or prints an AccessKey pair; on failure the guidance is always to repair the local CLI
profile rather than to paste credentials into the conversation.
"""

import hashlib
import json
import sys

import _cli
from _constants import STS_PRODUCT, STS_TIMEOUT_SECONDS

STS_ACTION = "GetCallerIdentity"


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

def provenance_tag(account_id):
    """Short stable tag so a report can be tied to one account without echoing the raw id."""
    if not account_id:
        return "uid-unknown"
    digest = hashlib.sha256(str(account_id).encode("utf-8")).hexdigest()
    return "uid-" + digest[:8]


def get_caller_identity():
    """Return account identity fields, raising CliError when the profile does not work."""
    payload = _cli.call(STS_PRODUCT, STS_ACTION, {}, timeout=STS_TIMEOUT_SECONDS, attempts=1)
    if not isinstance(payload, dict):
        raise _cli.CliError("BadResponse", "identity check returned an unexpected body")
    account_id = payload.get("AccountId") or payload.get("accountId")
    return {
        "account_id": account_id,
        "principal_id": payload.get("PrincipalId") or payload.get("UserId"),
        "arn": _cli.redact_text(payload.get("Arn") or ""),
        "provenance_tag": provenance_tag(account_id),
    }


def main(argv=None):
    _cli.announce()
    try:
        identity = get_caller_identity()
    except _cli.CliError as exc:
        sys.stderr.write("[WARN] identity check failed: {0}\n".format(exc))
        sys.stderr.write(
            "[guidance] Configure the local CLI profile with the default credential chain "
            "(aliyun sts get-caller-identity). Never paste an AccessKey pair or a password into the ticket.\n"
        )
        print("STATUS: FAIL")
        print("NEXT_ACTION: Repair CLI credentials or grant the actions listed in "
              "references/ram-policies.md, then rerun preflight.")
        return 1
    json.dump(identity, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    print("STATUS: OK")
    print("NEXT_ACTION: run collect with the region and the instance id or public IP.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
