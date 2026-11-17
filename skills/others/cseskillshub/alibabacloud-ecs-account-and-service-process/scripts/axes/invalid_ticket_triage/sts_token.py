"""Read-only identity probe: which account do the current credentials belong to?

The account id labels the triage report so a reader knows whose visibility the instance
check had. Credentials come from the Alibaba Cloud CLI default credential chain only;
this module never accepts, reads, stores or prints an AccessKey pair or a session token,
and every CLI error text passes through masking.
"""

import argparse
import sys

from _cli import CliError, call_aliyun, mask_secrets, new_session_id
from _constants import DEFAULT_TIMEOUT_SECONDS, STS_ACTION, STS_PRODUCT

CONFIGURE_HINT = (
    "No usable credentials were found. Configure the Alibaba Cloud CLI with the "
    "default credential chain (run 'aliyun configure' or attach a profile/instance "
    "role), then re-run. Never paste an AccessKey pair or a session token into a "
    "ticket, a chat message or a command line argument."
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

def get_caller_identity(session_id=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Return {'account_id', 'arn', 'user_id', 'identity_type'} or None if unavailable."""
    try:
        body = call_aliyun(STS_PRODUCT, STS_ACTION, session_id=session_id, timeout=timeout)
    except CliError as exc:
        sys.stderr.write("[WARN] identity check failed: %s\n" % mask_secrets(exc))
        sys.stderr.write("[WARN] %s\n" % CONFIGURE_HINT)
        return None
    return {
        "account_id": body.get("AccountId") or "",
        "arn": body.get("Arn") or "",
        "user_id": body.get("UserId") or "",
        "identity_type": body.get("IdentityType") or "",
    }


def format_identity(identity):
    if not identity:
        return "unavailable (no readable credentials)"
    return "account %s%s" % (
        identity.get("account_id") or "unknown",
        ", identity %s" % identity["arn"] if identity.get("arn") else "",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show which account the read-only credentials belong to.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help="per-call timeout in seconds (default %(default)s)")
    args = parser.parse_args(argv)

    session_id = new_session_id()
    identity = get_caller_identity(session_id=session_id, timeout=args.timeout)
    print("session_id: %s" % session_id)
    print("caller_identity: %s" % format_identity(identity))
    if identity is None:
        print("STATUS: FAIL")
        print("NEXT_ACTION: configure the CLI default credential chain, then re-run the "
              "triage with --verify-instances")
        return 1
    print("STATUS: OK")
    print("NEXT_ACTION: none; this probe is read-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
