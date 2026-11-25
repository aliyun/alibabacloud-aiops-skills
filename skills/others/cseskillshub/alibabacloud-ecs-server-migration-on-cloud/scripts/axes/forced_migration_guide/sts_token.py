"""Credential / caller-identity probe for the read-only migration guide skill.

Runs the plugin-mode, lower-case-hyphenated STS command and derives an account
label for traceability. Uses only the default credential chain. It never asks
for, reads, prints, or stores an access key or secret; on failure it points the
user to `aliyun configure`.
"""

import subprocess
import sys
import time

from _constants import CLI_BACKOFF_BASE_SECONDS, CLI_MAX_RETRIES, STS_PRODUCT
from _cli import CliError, mask_credentials, user_agent, _run


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

def get_caller_identity():
    """Return the decoded caller identity dict, or raise CliError.

    Command shape (plugin mode, product + lower-case-hyphenated action):
        aliyun sts get-caller-identity --user-agent <ua>
    """
    cmd = [
        "aliyun",
        STS_PRODUCT,
        "GetCallerIdentity",
        "--user-agent",
        user_agent(),
    ]

    last_error = None
    for attempt in range(CLI_MAX_RETRIES):
        try:
            proc = _run(cmd)
        except FileNotFoundError:
            raise CliError("CliNotFound",
                           "the 'aliyun' CLI was not found on PATH; install and configure it "
                           "via the default credential chain (aliyun configure)")
        except OSError as exc:
            raise CliError("CliInvokeError", mask_credentials(str(exc)))
        except subprocess.TimeoutExpired:
            last_error = "RequestTimeout: get-caller-identity timed out"
            sys.stderr.write("[WARN] {} (attempt {}/{})\n".format(
                last_error, attempt + 1, CLI_MAX_RETRIES))
            time.sleep(CLI_BACKOFF_BASE_SECONDS * (2 ** attempt))
            continue

        if proc.returncode == 0:
            import json
            try:
                return json.loads((proc.stdout or "").strip() or "{}")
            except ValueError:
                raise CliError("ParseError", "caller identity response was not valid JSON")

        err_text = mask_credentials((proc.stderr or proc.stdout or "").strip())
        if attempt < CLI_MAX_RETRIES - 1:
            last_error = err_text
            time.sleep(CLI_BACKOFF_BASE_SECONDS * (2 ** attempt))
            continue
        raise CliError("CredentialCheckFailed", err_text or "aliyun sts get-caller-identity failed")

    raise CliError("CredentialCheckFailed", last_error or "retries exhausted")


def account_label(identity):
    """Short, non-secret account tag for the report header."""
    account_id = (identity or {}).get("AccountId") or (identity or {}).get("UserId") or "unknown"
    return str(account_id)


def configure_hint():
    return (
        "No usable credential was found. Configure the default credential chain by running "
        "`aliyun configure` (or export standard ALIBABA_CLOUD environment variables). "
        "This skill only uses read-only actions and never handles access keys or secrets directly."
    )
