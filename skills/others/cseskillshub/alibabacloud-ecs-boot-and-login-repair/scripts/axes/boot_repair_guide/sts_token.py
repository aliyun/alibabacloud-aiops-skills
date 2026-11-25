"""Credential chain probe and report provenance tag.

Run directly to check that the default credential chain works before any triage:

    python3 scripts/sts_token.py

Emits a short JSON object describing the calling identity. Only a truncated account
identifier is surfaced, and only so a report can state which account produced its
numbers; no secret, token, or key material is read, accepted, printed, or stored.
"""

import json
import sys

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

def caller_identity(session_id=None):
    """Return a provenance record for the active identity, or raise ``CliError``."""
    payload = _cli.call("GetCallerIdentity", session_id=session_id, timeout=20)
    account_id = str(payload.get("AccountId") or payload.get("account_id") or "")
    arn = str(payload.get("Arn") or "")
    identity = {
        "identity_type": payload.get("IdentityType") or payload.get("identity_type") or "unknown",
        # Last four characters only. The full value never leaves the transport layer.
        "account_tail": account_id[-4:] if account_id else "n/a",
        "principal": _tail_of_arn(arn),
        "raw_fields_seen": sorted(k for k in payload if k in ("AccountId", "Arn", "IdentityType",
                                                              "UserId", "RequestId")),
    }
    return identity


def _tail_of_arn(arn):
    if not arn:
        return "n/a"
    parts = arn.split(":")
    if len(parts) >= 6 and parts[5]:
        resource = parts[5]
        if len(resource) > 24:
            resource = "..." + resource[-12:]
        return resource
    return "n/a"


def main(argv=None):
    session_id = _cli.new_session_id()
    try:
        identity = caller_identity(session_id=session_id)
    except _cli.CliError as exc:
        print(json.dumps({"ok": False, "session_id": session_id,
                          "code": exc.code,
                          "message": _cli.mask_credentials(exc.message),
                          "guidance": ("Configure the default credential chain with 'aliyun "
                                       "configure'. This skill never asks for an access key "
                                       "pair, a token, or a guest password.")},
                         indent=2))
        print("STATUS: FAIL")
        print("NEXT_ACTION: Customer or operator configures CLI credentials, then re-runs the "
              "same command.")
        return 2
    identity["ok"] = True
    identity["session_id"] = session_id
    identity["user_agent"] = _cli.user_agent(session_id)
    identity["skill"] = C.SKILL_NAME
    print(json.dumps(identity, indent=2, ensure_ascii=False))
    print("STATUS: OK")
    print("NEXT_ACTION: Continue with 'boot_repair_guide.py profile' for the affected instance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
