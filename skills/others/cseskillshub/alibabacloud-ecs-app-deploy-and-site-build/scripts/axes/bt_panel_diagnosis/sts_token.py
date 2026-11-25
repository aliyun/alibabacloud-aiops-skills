"""Credential self-check: which account does the active profile belong to?

This scenario has a confirmed cross-account failure mode: threads stall when
the queried instance turns out to live in another account (case T-4B98459C:
front and back end in two different accounts). The account uid is therefore
resolved once and stamped onto every report, and the report states plainly
that read-only queries only ever see the resources of the current credentials
in the named region. Only the default credential chain is used: this module
never accepts, reads or prints a credential value, and a failure points at
`aliyun sts get-caller-identity`.
"""

import json
import os
import sys

from _constants import API_STS_GET_CALLER_IDENTITY, PRODUCT_STS
from _cli import call_soft, mask_secrets, session_id, user_agent


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

def profile_scope():
    """Which named profile the default chain resolves to. A profile name only -
    this module never touches a credential value."""
    return (os.environ.get("ALIBABA_CLOUD_PROFILE")
            or os.environ.get("ALICLOUD_PROFILE")
            or "default")


def resolve_identity():
    """Return (account_info, error). account_info is None when unauthenticated.

    Nothing is cached on disk: an identity check costs one small read-only
    call, and machine state that can go stale is worse than that call.
    """
    payload, error = call_soft(API_STS_GET_CALLER_IDENTITY, product=PRODUCT_STS)
    if error is not None:
        return None, error

    account_id = str(payload.get("AccountId") or payload.get("accountId") or "")
    arn = str(payload.get("Arn") or payload.get("arn") or "")
    identity_type = str(payload.get("IdentityType") or payload.get("identityType") or "")
    principal = arn.rsplit("/", 1)[-1] if arn else ""

    record = {
        "identity": profile_scope(),
        "account_suffix": account_id[-4:] if account_id else "unknown",
        "identity_type": identity_type,
        "principal": principal,
        "user_agent": user_agent(),
    }
    return dict(record), None


def uid_tag(record):
    """Short provenance label attached to reports; the full account id and any
    credential material are not printed."""
    if not record:
        return "account=unverified"
    return "account=****{0} ({1})".format(record.get("account_suffix", "unknown"),
                                          record.get("identity_type") or "unknown")


def main(argv=None):
    record, error = resolve_identity()
    if error is not None:
        sys.stderr.write("[WARN] {0}\n".format(mask_secrets(str(error))))
        sys.stderr.write(
            "No usable credentials were found. Run `aliyun sts get-caller-identity` and complete "
            "the setup in the CLI's own prompts; this skill never collects a "
            "credential value on your behalf.\n"
        )
        print("STATUS: FAIL")
        print("NEXT_ACTION: configure the aliyun CLI default credential chain, then "
              "re-run check-env.")
        return 1

    print(json.dumps({
        "identity": uid_tag(record),
        "identity_type": record.get("identity_type", ""),
        "principal": record.get("principal", ""),
        "user_agent": record.get("user_agent", ""),
        "session_id": session_id(),
    }, indent=2, sort_keys=True))
    print("STATUS: OK")
    print("NEXT_ACTION: run triage with --region-id set to the region the customer "
          "names and either --instance-id or an IP the customer gave.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
