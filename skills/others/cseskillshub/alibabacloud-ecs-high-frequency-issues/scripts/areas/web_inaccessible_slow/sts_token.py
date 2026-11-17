"""Credential preflight: who is calling, and which account do the assets have to belong to.

Uses the ambient credential chain that the CLI is already configured with. This module
never accepts, reads, prints or stores an access key, a secret or a password; when the
preflight fails the only guidance it emits is to configure the CLI out-of-band.

Run directly for a stand-alone check::

    python3 scripts/areas/web_inaccessible_slow/sts_token.py
"""

import argparse
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
# stderr is read back by the agent on some transports; mask it too.
_sys.stderr = _MaskedStdout(_sys.stderr)
# --- end hygiene

class CredentialError(Exception):
    """Raised when the caller identity cannot be resolved."""


def get_caller_identity(session_id=None, timeout=None):
    """Return the caller identity dict (AccountId, Arn, UserId).

    Raises :class:`CredentialError` with operator-actionable guidance on failure.
    """
    try:
        payload = _cli.call("sts", "GetCallerIdentity", session_id=session_id,
                            timeout=timeout or C.STS_TIMEOUT, retries=1)
    except _cli.CliError as exc:
        if exc.is_denial:
            raise CredentialError(
                "The credential in use is not permitted to call sts:GetCallerIdentity. "
                "Grant that single action (see references/ram-policies.md) and continue; "
                "account-ownership conclusions are unavailable until then.")
        raise CredentialError(
            "No usable credential was found (%s). Configure the CLI out of this "
            "conversation - for example with `aliyun sts get-caller-identity` using a RAM user or a "
            "temporary credential. Never paste an access key, a secret or a password into "
            "the support conversation." % exc.code)
    if not payload or not payload.get("AccountId"):
        raise CredentialError("sts:GetCallerIdentity returned no AccountId.")
    return payload


def uid_label(identity):
    """Short traceability tag put at the top of every report."""
    account = str(identity.get("AccountId", "unknown"))
    masked_account = account[:4] + "***" if len(account) > 4 else account
    arn = str(identity.get("Arn", ""))
    principal = arn.split("/")[-1] if arn else str(identity.get("UserId", "unknown"))
    return "caller=uid:%s principal:%s" % (masked_account, principal or "unknown")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check the active cloud identity.")
    parser.add_argument("--region-id", default=C.DEFAULT_REGION,
                        help="Region context for the label only; identity is global.")
    args = parser.parse_args(argv)

    session_id = _cli.new_session_id()
    try:
        identity = get_caller_identity(session_id=session_id)
    except CredentialError as exc:
        sys.stdout.write("STATUS: %s\n" % C.STATUS_FAIL)
        sys.stdout.write("NEXT_ACTION: Ask the operator to configure credentials for the "
                         "CLI outside this conversation, then re-run the preflight.\n")
        sys.stdout.write("DETAIL: %s\n" % _cli.mask_secrets(exc))
        return 1

    sys.stdout.write("%s\n" % uid_label(identity))
    sys.stdout.write("account_id: %s\n" % identity.get("AccountId"))
    sys.stdout.write("arn: %s\n" % _cli.mask_secrets(identity.get("Arn", "")))
    sys.stdout.write("session_id: %s\n" % session_id)
    sys.stdout.write("STATUS: %s\n" % C.STATUS_OK)
    sys.stdout.write("NEXT_ACTION: Continue with the layered check; L1 asset ownership is "
                     "judged against this AccountId.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
