"""Credential check and account provenance tag.

Uses the default credential chain only (environment, `aliyun configure`
profile, or an instance RAM role). This module never reads, prints, or asks
for an AccessKey pair or a security token.
"""

import sys

import _cli
from _constants import READ_TIMEOUT_SECONDS, STS_PRODUCT

# Plugin mode: the CLI token is lowercase-hyphenated.
STS_CLI_ACTION = "GetCallerIdentity"


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

def get_caller_identity(session_id="", stream=None):
    """Return the caller identity payload, or None when credentials are unusable."""
    return _cli.describe(
        STS_PRODUCT,
        "GetCallerIdentity",
        params={},
        session_id=session_id,
        timeout=READ_TIMEOUT_SECONDS,
        stream=stream or sys.stderr,
        cli_action=STS_CLI_ACTION,
    )


def account_id(identity):
    if not isinstance(identity, dict):
        return ""
    return str(identity.get("AccountId") or identity.get("AccountUID") or "")


def uid_tag(identity):
    """Short provenance tag placed in every report header."""
    account = account_id(identity)
    if not account:
        return "uid=unknown"
    return "uid={}".format(account)


def main(argv=None):
    stream = sys.stderr
    session_id = _cli.new_session_id()
    identity = get_caller_identity(session_id=session_id, stream=stream)
    if identity is None:
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: run `aliyun configure` with a valid profile of the account "
              "that owns the migration source, then re-run. Do not paste an AccessKey "
              "pair or a security token into the conversation.")
        return 2
    print("caller: {}".format(uid_tag(identity)))
    print("arn   : {}".format(_cli.mask_secrets(identity.get("Arn", ""))))
    print("STATUS: OK")
    print("NEXT_ACTION: continue with `assess_migration.py assess`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
