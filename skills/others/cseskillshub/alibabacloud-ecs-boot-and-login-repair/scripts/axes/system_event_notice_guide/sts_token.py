#!/usr/bin/env python3
"""Credential reachability check and account traceability tag.

Uses the CLI plug-in form `aliyun sts get-caller-identity`. This skill never
reads, prints, stores or passes any credential value: it only asks the CLI
whether the already-configured identity can be resolved, and keeps a masked
account tag for the report.
"""

from typing import Dict, Optional, Tuple

from _cli import CliError, redact, run_aliyun
from _constants import (
    CLI_TIMEOUT_SECONDS,
    STS_ACTION_PLUGIN_MODE,
    STS_PRODUCT,
)

_KEEP_FIELDS = ("AccountId", "UserId", "Arn")


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

def get_caller_identity(
    session_id: str,
    timeout: int = CLI_TIMEOUT_SECONDS,
    profile: Optional[str] = None,
) -> Dict[str, str]:
    """Return the whitelisted identity fields of the current caller."""
    response = run_aliyun(
        STS_PRODUCT,
        STS_ACTION_PLUGIN_MODE,
        {},
        session_id=session_id,
        timeout=timeout,
        profile=profile,
    )
    identity = {}
    for field in _KEEP_FIELDS:
        value = response.get(field)
        if isinstance(value, (str, int)):
            identity[field] = str(value)
    return identity


def mask_account(value: Optional[str]) -> str:
    """Keep only the tail of an account id so the report stays traceable."""
    text = (value or "").strip()
    if not text:
        return "unknown"
    if len(text) <= 4:
        return "****"
    return "****" + text[-4:]


def mask_arn(value: Optional[str]) -> str:
    text = (value or "").strip()
    if not text:
        return "unknown"
    parts = text.split(":")
    if len(parts) > 4:
        parts[4] = "****" + (parts[4][-4:] if len(parts[4]) > 4 else "")
    return ":".join(parts)


def resolve_caller(
    session_id: str,
    timeout: int = CLI_TIMEOUT_SECONDS,
    profile: Optional[str] = None,
) -> Tuple[Dict[str, str], Optional[CliError]]:
    """Never fatal: a failure is reported and the run continues."""
    try:
        identity = get_caller_identity(session_id, timeout=timeout, profile=profile)
    except CliError as exc:
        return {}, CliError(exc.code, redact(exc.message), exc.retryable)
    caller = {
        "account_masked": mask_account(identity.get("AccountId")),
        "principal_masked": mask_arn(identity.get("Arn")),
        "user_id_masked": mask_account(identity.get("UserId")),
    }
    return caller, None
