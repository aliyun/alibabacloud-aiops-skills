"""Resolve the calling identity through the default credential chain.

Uses the plugin-style command ``aliyun sts get-caller-identity``. Credentials
come from the CLI's own default chain (profile, env, instance role, STS cache);
this module never asks for, reads, stores or prints an AccessKey pair.
"""

import json

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

def _parse(stdout):
    if not stdout.strip():
        return {}
    try:
        payload = json.loads(stdout)
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def get_caller_identity():
    """Return ``{"AccountId", "Arn", "IdentityType", "UserId"}`` or raise.

    Raises :class:`_cli.CliError` when no usable credential exists so the caller
    can degrade instead of guessing an account.
    """
    argv = list(C.STS_IDENTITY_COMMAND) + ["--user-agent", _cli.user_agent()]
    returncode, stdout, stderr = _cli.run(argv, timeout=C.CLI_TIMEOUT_SECONDS)
    if returncode != 0:
        code, message = _cli.parse_error(stdout, stderr)
        raise _cli.CliError(code, message)
    identity = _parse(stdout)
    if not identity:
        raise _cli.CliError("MalformedResponse", "caller identity response unusable")
    return identity


def identity_label():
    """Short provenance tag for reports: identity type plus masked account."""
    try:
        identity = get_caller_identity()
    except _cli.CliError as exc:
        return None, "identity unavailable ({0})".format(exc.code)
    account = str(identity.get("AccountId") or "")
    tag = ""
    if account:
        tag = "acct:{0}***{1}".format(account[:4], account[-2:]) if len(account) > 6 else "acct:***"
    arn = str(identity.get("Arn") or "")
    identity_type = str(identity.get("IdentityType") or "")
    detail = " ".join(v for v in (tag, identity_type, arn) if v)
    return detail.strip() or "account unknown", None


def configure_hint():
    return (
        "No usable Alibaba Cloud credential was found. Run `aliyun configure` and "
        "supply a profile from the default credential chain (RAM user, role or STS "
        "session). Never paste an AccessKey pair into this conversation or a file."
    )


if __name__ == "__main__":  # pragma: no cover - manual probe only
    try:
        print(json.dumps(get_caller_identity(), indent=2, sort_keys=True))
    except _cli.CliError as error:
        print("STATUS: FAIL")
        print("NEXT_ACTION: {0}".format(configure_hint()))
        raise SystemExit(str(error))
