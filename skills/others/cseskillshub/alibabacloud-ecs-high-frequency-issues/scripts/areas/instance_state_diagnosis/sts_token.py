#!/usr/bin/env python3
"""
sts_token.py -- credential pre-flight and caller provenance.

Confirms the default credential chain works before any diagnosis runs, and
derives the account id used to label every evidence line ("which account did we
look at"). This matters for delegated cases where the instance may belong to a
different account: a mismatch stops the run instead of reporting on the wrong
tenant.

It never reads, prints, caches, forwards or asks for an AccessKey secret; the
only supported path is `aliyun sts get-caller-identity` (or whatever the ambient credential
chain provides).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, Optional

from _cli import CliError, caller_identity
from _constants import DEFAULT_TIMEOUT

CONFIG_GUIDANCE = (
    "No usable Alibaba Cloud credentials were returned by the default credential "
    "chain. Run `aliyun sts get-caller-identity` in this shell (or attach a RAM role to the "
    "host) and re-run. Do not paste an AccessKey secret into the conversation; "
    "this skill never handles key material directly.")

PERMISSION_GUIDANCE = (
    "The identity behind the default credential chain is not allowed to call "
    "sts:GetCallerIdentity. Grant at least the actions listed in "
    "references/ram-policies.md with a least-privilege custom policy; an "
    "explicit deny shows up as ImplicitDeny, a missing grant as NoPermission.")


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

def get_caller(timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Return {'account_id', 'user_id', 'arn'} or raise CliError."""
    payload = caller_identity(timeout=timeout)
    account_id = payload.get("AccountId") or payload.get("accountId") or ""
    user_id = payload.get("UserId") or payload.get("userId") or ""
    arn = payload.get("Arn") or payload.get("arn") or ""
    if not account_id:
        raise CliError("InvalidResponse", "GetCallerIdentity returned no AccountId")
    return {"account_id": str(account_id), "user_id": str(user_id), "arn": arn}


def provenance_tag(caller: Optional[Dict[str, Any]]) -> str:
    """Short label put on every evidence line for traceability."""
    if not caller:
        return "uid=unknown"
    return "uid=%s" % caller.get("account_id", "unknown")


def diagnose_error(exc: CliError) -> str:
    """Map a credential failure onto the one thing the operator must do next."""
    code = (exc.code or "").lower()
    if code in ("nopermission", "implicitdeny", "accessdenied", "unauthorizedoperation") or "permission" in code:
        return PERMISSION_GUIDANCE
    if code == "clinotavailable":
        return "The aliyun CLI is not installed or not on PATH; install it, then run `aliyun sts get-caller-identity`."
    return CONFIG_GUIDANCE


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Alibaba Cloud credentials via the default credential chain.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Per-call timeout in seconds for the STS request.")
    args = parser.parse_args(argv)

    try:
        caller = get_caller(timeout=args.timeout)
    except CliError as exc:
        sys.stderr.write("[WARN] credential pre-flight failed -- %s\n" % exc)
        sys.stderr.write("%s\n" % diagnose_error(exc))
        print("STATUS: FAIL")
        print("NEXT_ACTION: restore the default credential chain with `aliyun sts get-caller-identity`, "
              "then re-run the diagnosis entry script.")
        return 2

    print("credential pre-flight OK")
    print("  %s" % provenance_tag(caller))
    print("  arn: %s" % (caller.get("arn") or "-"))
    print("STATUS: OK")
    print("NEXT_ACTION: run scripts/areas/instance_state_diagnosis/diagnose_instance_state.py for the customer's instance(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
