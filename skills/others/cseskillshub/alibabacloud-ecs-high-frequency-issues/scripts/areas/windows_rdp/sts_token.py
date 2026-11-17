"""Caller identity check for the Windows RDP diagnosis skill.

Uses the plugin-style command ``aliyun sts get-caller-identity`` to prove that
the default credential chain of the local CLI works and to derive the short
account label that makes a run traceable. Credential material itself is never
touched: there is no key, token or profile parameter anywhere in this code path,
and a failure points at ``aliyun sts get-caller-identity`` rather than asking for keys.
"""

from typing import Any, Dict, List, Optional, Tuple

from _cli import CliError, mask_credentials, run_cli
from _constants import (
    ACTION_GET_CALLER_IDENTITY,
    CODE_IMPLICIT_DENY,
    CODE_INVALID_CREDENTIAL,
    CODE_MISSING_PARAMETER,
    CODE_NO_PERMISSION,
    PRODUCT_STS,
    STS_API_VERSION,
)

_IDENTITY_FIELD_CANDIDATES = {
    "account": ("AccountId", "accountId", "AccountUid", "Uid"),
    "arn": ("Arn", "arn", "UserId", "PrincipalId"),
    "identity_type": ("IdentityType", "identityType", "PrincipalType"),
}


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

def fetch_caller_identity(
    session_id: str, warnings: Optional[List[str]] = None
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Return ``(identity, error_code)`` for the current CLI principal."""
    try:
        payload = run_cli(
            PRODUCT_STS,
            ACTION_GET_CALLER_IDENTITY,
            params=None,
            session_id=session_id,
            retries=1,
            warnings=warnings,
        )
    except CliError as exc:
        return {}, exc.code
    except Exception as exc:  # pragma: no cover - defensive transport guard
        if warnings is not None:
            warnings.append(
                "unexpected identity lookup failure: {0}".format(mask_credentials(exc))
            )
        return {}, CODE_INVALID_CREDENTIAL

    identity: Dict[str, Any] = {"api_version": STS_API_VERSION, "raw_returned": bool(payload)}
    for target, candidates in _IDENTITY_FIELD_CANDIDATES.items():
        identity[target] = _first_present(payload, candidates)
    identity["account"] = identity.get("account") or _parse_account_from_arn(identity.get("arn"))
    if not identity.get("raw_returned"):
        return identity, CODE_MISSING_PARAMETER
    return identity, None


def _first_present(payload: Optional[Dict[str, Any]], keys: Tuple[str, ...]) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _parse_account_from_arn(arn: Optional[str]) -> Optional[str]:
    """Best-effort account extraction from an ``acs:ram::<account>:...`` style ARN."""
    if not arn:
        return None
    for part in str(arn).split(":"):
        if part.isdigit() and len(part) >= 12:
            return part
    return None


def uid_traceability_label(identity: Dict[str, Any]) -> str:
    """Render the account as a short label safe to paste into a ticket."""
    account = (identity or {}).get("account")
    if not account:
        return "account:unavailable"
    digits = "".join(c for c in str(account) if c.isdigit())
    if len(digits) <= 4:
        return "account:uid-{0}".format(digits or "unknown")
    return "account:uid-****{0}".format(digits[-4:])


def identity_guidance_lines(error_code: Optional[str]) -> List[str]:
    """Manual remediation hints for a failed identity lookup."""
    if error_code == CODE_INVALID_CREDENTIAL:
        return [
            "Refresh the local credential chain with `aliyun sts get-caller-identity`; this skill "
            "never asks for, reads or passes key material.",
            "Confirm the RAM principal still belongs to the account that owns the "
            "Windows instance.",
        ]
    if error_code in (CODE_NO_PERMISSION, CODE_IMPLICIT_DENY):
        return [
            "Grant the read actions listed in references/ram-policies.md; the identity "
            "check needs the STS caller-identity action.",
        ]
    return [
        "Re-run the identity check on its own through this package\'s identity preflight for the same area, then retry the question.",
    ]


def main() -> None:  # pragma: no cover - thin CLI wrapper
    """Run the identity check on its own and print the traceability label."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="Verify the current aliyun CLI identity via the STS caller-identity action"
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()

    from _cli import new_session_id

    warnings: List[str] = []
    sid = new_session_id()
    identity, error_code = fetch_caller_identity(sid, warnings=warnings)
    label = uid_traceability_label(identity)

    if args.json:
        print(json.dumps({
            "session_id": sid,
            "account_label": label,
            "arn": identity.get("arn"),
            "identity_type": identity.get("identity_type"),
            "error_code": error_code,
            "warnings": warnings,
        }, indent=2))
    else:
        print("=" * 60)
        print("Caller identity (aliyun CLI default credential chain)")
        print("=" * 60)
        print("  Account label : {0}".format(label))
        print("  Arn           : {0}".format(identity.get("arn") or "not returned"))
        print("  Identity type : {0}".format(identity.get("identity_type") or "not returned"))
        for w in warnings:
            print("  [WARN] {0}".format(w))

    if error_code:
        for line in identity_guidance_lines(error_code):
            print("  - {0}".format(line))
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: repair the credential chain or grant the identity action, then retry")
        sys.exit(1)
    print("\nSTATUS: OK")
    print("NEXT_ACTION: run scripts/areas/windows_rdp/rdp_diagnose.py for the target instance")


if __name__ == "__main__":  # pragma: no cover
    main()
