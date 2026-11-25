"""Credential pre-flight through the caller's own identity.

Uses the plugin-mode spelling `aliyun sts get-caller-identity`. Credentials come from
the default chain of the running environment only; this module never reads, writes,
prints or requests an access key, a secret or a password.
"""

import argparse
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

def get_caller_identity(session_id=None, timeout=C.DEFAULT_TIMEOUT):
    """Return the decoded identity payload, raising CliError when unavailable."""
    return _cli.run("GetCallerIdentity", product=C.STS_PRODUCT, params={},
                    session_id=session_id, timeout=timeout, hyphenated=True)


def identity_label(payload):
    """Build a short, non-sensitive traceability tag from the account id."""
    account_id = ""
    if isinstance(payload, dict):
        for key in ("AccountId", "accountId", "AccountUID", "UserId", "PrincipalId"):
            value = payload.get(key)
            if value:
                account_id = str(value)
                break
        if not account_id:
            arn = str(payload.get("Arn") or payload.get("arn") or "")
            digits = [part for part in arn.replace("/", ":").split(":") if part.isdigit()]
            if digits:
                account_id = digits[0]
    if not account_id:
        return "account:unknown"
    if len(account_id) <= 4:
        return "account:{0}".format(account_id)
    return "account:***{0}".format(account_id[-4:])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify the ambient aliyun credentials and print a traceability label.")
    parser.add_argument("--json", action="store_true", help="print the raw identity payload as JSON")
    parser.add_argument("--timeout", type=int, default=C.DEFAULT_TIMEOUT,
                        help="per-call timeout in seconds (default %(default)s)")
    args = parser.parse_args(argv)

    session_id = _cli.new_session_id()
    timeout = min(max(1, args.timeout), C.MAX_TIMEOUT)
    try:
        payload = get_caller_identity(session_id=session_id, timeout=timeout)
    except _cli.CliError as exc:
        _cli.warn(str(exc))
        sys.stderr.write(
            "Credential pre-flight failed. Run `aliyun configure` in this environment and "
            "retry. Never paste an access key, a secret or an instance password into this "
            "skill; it reads credentials from the default chain only.\n")
        print("STATUS: FAIL")
        print("NEXT_ACTION: ask the operator to configure credentials with `aliyun configure`, "
              "then re-run the same command.")
        return 1

    label = identity_label(payload)
    if args.json:
        print(json.dumps({"identity": payload, "label": label, "session_id": session_id},
                         indent=2, sort_keys=True))
    else:
        print("identity OK ({0}) session={1}".format(label, session_id))
    print("STATUS: OK")
    print("NEXT_ACTION: continue with the diagnosis entry script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
