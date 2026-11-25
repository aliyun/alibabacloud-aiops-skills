"""Caller identity pre-flight.

Run before any other evidence gathering so the report can state which account
the readings came from, and so a missing or mis-scoped authorization is found at
the first step instead of half way through a diagnosis.

Credentials are never handled here: the CLI resolves the caller from its own
default chain, and the only guidance this module gives on failure is to
verify that chain with ``aliyun sts get-caller-identity``. It never asks for, reads or
stores key material.

Usage::

    python3 scripts/axes/web_service_runtime_config/sts_token.py check
    python3 scripts/axes/web_service_runtime_config/sts_token.py check --plan-only
"""

import argparse
import sys

from _cli import CliError, new_session_id, run_cli
from _constants import PRODUCT_STS, STS_PLUGIN_COMMAND


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

def get_caller_identity(session_id=None, plan_only=False, timeout=None):
    """Return the STS identity payload for the current CLI caller."""
    kwargs = {"plan_only": plan_only}
    if timeout:
        kwargs["timeout"] = timeout
    return run_cli(PRODUCT_STS, STS_PLUGIN_COMMAND, {}, session_id=session_id, **kwargs)


def account_label(identity):
    """A short provenance tag for the report header."""
    if not identity:
        return "uid:unknown"
    account_id = identity.get("AccountId") or identity.get("account_id") or ""
    if not account_id:
        return "uid:unknown"
    return "uid:%s" % (account_id,)


def preflight(session_id=None, plan_only=False, timeout=None):
    """Return ``(identity, error)``; one of the two is always ``None``."""
    try:
        return get_caller_identity(session_id=session_id, plan_only=plan_only,
                                   timeout=timeout), None
    except CliError as error:
        return None, error


def _main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify that the CLI credential chain resolves an identity."
    )
    parser.add_argument("mode", nargs="?", default="check", choices=("check",),
                        help="what to do; only 'check' exists")
    parser.add_argument("--plan-only", action="store_true",
                        help="print the planned call instead of issuing it")
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the CLI wall-clock timeout in seconds")
    args = parser.parse_args(argv)

    session_id = new_session_id()
    identity, error = preflight(session_id=session_id, plan_only=args.plan_only,
                                timeout=args.timeout)
    if error is not None:
        sys.stderr.write(
            "[WARN] identity pre-flight failed: %s\n"
            "       sign the CLI in again with `aliyun sts get-caller-identity`; this skill "
            "never asks for or stores credentials of its own.\n" % (error,)
        )
        print("STATUS: DEGRADED")
        print("NEXT_ACTION: restore the CLI default credential chain, then re-run this check.")
        return 1

    print("identity ok: %s" % (account_label(identity),))
    print("session-id: %s" % (session_id,))
    print("STATUS: OK")
    print("NEXT_ACTION: continue with the report command.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
