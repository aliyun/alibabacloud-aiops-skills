#!/usr/bin/env python3
"""Account identity probe: `aliyun sts get-caller-identity`.

Confirms that a credential chain is present and yields the account UID label that the report
declares as auto-filled. Nothing is read from, written to, or printed about AccessKeys, secrets,
or tokens; the CLI's own credential chain is the only supported path.
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

def get_caller_identity(session_id=None):
    """Return ``{"account_id": ..., "arn": ..., "principal_id": ...}`` or raise ``CliError``."""
    sid = session_id or _cli.new_session_id()
    data = _cli.call_plugin(C.STS_PRODUCT, "GetCallerIdentity", session_id=sid)
    identity = {
        "account_id": _first(data, "AccountId", "accountId", "AccountUid"),
        "arn": _first(data, "Arn", "arn"),
        "principal_id": _first(data, "UserId", "PrincipalId"),
    }
    if not identity["account_id"]:
        raise _cli.CliError("IdentityUnavailable", "the identity call returned no account id")
    return identity


def _first(data, *keys):
    if not isinstance(data, dict):
        return ""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def uid_label(identity):
    """Render the traceability label used in reports."""
    account_id = (identity or {}).get("account_id") or "unknown"
    return "account-uid:%s" % account_id


def main():
    session_id = _cli.new_session_id()
    try:
        identity = get_caller_identity(session_id)
    except _cli.CliError as exc:
        if exc.code in ("CliUnavailable", "BadCLIOutput", "IdentityUnavailable"):
            detail = exc.describe()
        else:
            detail = "%s. An administrator must attach the missing inspection action; see " \
                     "references/ram-policies.md." % exc.describe()
        sys.stdout.write("%s\n" % json.dumps({
            "status": "FAIL",
            "error": exc.code,
            "detail": _cli.mask_credentials(detail),
            "hint": "Configure credentials by running `aliyun configure` yourself; this skill "
                    "never asks for an AccessKey id, secret, or token.",
            "user_agent": _cli.user_agent(session_id),
        }, indent=2, sort_keys=True))
        sys.stdout.write("STATUS: FAIL\nNEXT_ACTION: configure the local CLI credential chain, "
                         "then re-run this command.\n")
        return 1

    sys.stdout.write("%s\n" % json.dumps({
        "status": "OK",
        "identity": identity,
        "label": uid_label(identity),
        "user_agent": _cli.user_agent(session_id),
    }, indent=2, sort_keys=True))
    sys.stdout.write("STATUS: OK\nNEXT_ACTION: pass --region-id to scripts/site_migration.py "
                     "precheck to gather migration evidence.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
