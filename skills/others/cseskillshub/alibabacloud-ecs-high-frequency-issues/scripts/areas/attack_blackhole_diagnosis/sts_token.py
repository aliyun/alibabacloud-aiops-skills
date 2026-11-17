"""Credential preflight: confirm the default credential chain works and derive
an account/UID provenance tag for the report.

Uses plugin-style invocation (`aliyun sts get-caller-identity`). Never asks for,
reads, stores or echoes an AccessKey id or secret: if the call fails, the caller
is told to run `aliyun sts get-caller-identity` outside this session.
"""

import json

from _cli import CliError, USER_AGENT, mask, run_json


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

class CredentialError(RuntimeError):
    def __init__(self, detail):
        self.detail = mask(detail)
        super(CredentialError, self).__init__(self.detail)


def get_caller_identity(timeout=None):
    """Return ``{"account_id":..., "principal_id":..., "arn":..., "raw":...}``.

    Raises CredentialError when no usable credential exists, so the entry script
    can emit ``STATUS: FAIL`` with setup guidance instead of guessing.
    """
    try:
        payload = run_json("sts", "GetCallerIdentity", params={}, timeout=timeout)
    except CliError as exc:
        if exc.code in ("CliUnavailable",):
            raise CredentialError(
                "The 'aliyun' CLI is not available in this environment. Install it and run "
                "'aliyun sts get-caller-identity' in your own terminal, then retry. No credential values are "
                "collected by this skill."
            )
        raise CredentialError(
            "Credential check failed ({0}). Run 'aliyun sts get-caller-identity' with your own profile, or "
            "attach a RAM identity that allows sts:GetCallerIdentity. Expected failure codes are "
            "NoPermission or ImplicitDeny.".format(exc.code)
        )
    if not payload:
        raise CredentialError("sts:GetCallerIdentity returned no identity; treat as unauthenticated.")
    return {
        "account_id": _pick(payload, "AccountId", "accountId", "Account"),
        "principal_id": _pick(payload, "UserId", "userId", "PrincipalId"),
        "arn": _pick(payload, "Arn", "arn", "UserId"),
        "raw": payload,
    }


def provenance_tag(identity):
    """Short label proving which account a report was produced against."""
    if not identity:
        return "account=unknown"
    account = identity.get("account_id") or "unknown"
    principal = identity.get("principal_id") or "unknown"
    return "account={0}/principal={1}".format(str(account)[-12:], str(principal)[-12:])


def _pick(payload, *keys):
    if not isinstance(payload, dict):
        return None
    lowered = {str(k).lower(): v for k, v in payload.items()}
    for key in keys:
        value = payload.get(key) or lowered.get(key.lower())
        if value:
            return value
    return None


def as_json(identity):
    return json.dumps(
        {
            "account_id": (identity or {}).get("account_id"),
            "principal_id": (identity or {}).get("principal_id"),
            "arn": (identity or {}).get("arn"),
            "user_agent": USER_AGENT,
        },
        indent=2,
    )


if __name__ == "__main__":  # pragma: no cover - manual smoke check
    try:
        print(json.dumps(get_caller_identity(), indent=2, default=str))
    except CredentialError as err:
        print("CREDENTIAL_UNAVAILABLE: {0}".format(err))
