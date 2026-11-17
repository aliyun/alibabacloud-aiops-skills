"""Resolve the current account through the default credential chain.

Used only to attribute the hand-off material pack to the right account. Only a
truncated provenance tag is surfaced; account id and ARN are not printed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from _cli import CliError, run_cli
from _constants import STS_PRODUCT, STS_TIMEOUT_SECONDS

_STS_ACTION = "GetCallerIdentity"
_ACCOUNT_KEYS = ("AccountId", "AccountUID", "OwnerId", "UserId")

CONFIGURE_GUIDANCE = (
    "No usable credentials were resolved from the default credential chain. Run "
    "`aliyun configure` to refresh them. This skill never asks for, reads or stores "
    "key material."
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

def get_caller_identity(timeout: Optional[int] = None) -> Dict[str, Any]:
    """Return {"status": "ok", "provenance_tag", ...} or a failed record plus guidance."""
    try:
        body = run_cli(STS_PRODUCT, _STS_ACTION, {}, quiet=True,
                       timeout=timeout or STS_TIMEOUT_SECONDS)
    except CliError as error:
        record = error.to_record(_STS_ACTION)
        record.update({"status": "failed", "guidance": CONFIGURE_GUIDANCE})
        return record

    account = _first(body, _ACCOUNT_KEYS)
    return {
        "status": "ok",
        "provenance_tag": _provenance_tag(account),
        "identity_type": str(body.get("IdentityType") or "unknown"),
    }


def _first(body: Dict[str, Any], keys: tuple) -> str:
    for key in keys:
        value = body.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _provenance_tag(account: str) -> str:
    if not account:
        return "acct:unresolved"
    return f"acct-tail-{account[-4:]}"


__all__ = ["get_caller_identity", "CONFIGURE_GUIDANCE"]
