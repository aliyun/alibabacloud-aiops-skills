"""Shared SDK client construction and transport settings."""

import json
import os
from pathlib import Path
import re

from .common import OpsError, positive_number


DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 60
DEFAULT_CHAT_READ_TIMEOUT = 300
_SESSION_ID = re.compile(r"[0-9a-f]{32}")
_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "references" / "manifest.json"


def _manifest_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate manifest key.")
    return result


def _invalid_json_constant(value):
    raise ValueError(f"Invalid JSON constant: {value}")


def user_agent():
    """Require the skill-scoped trace session and version for observability."""
    session = os.environ.get("SKILL_SESSION_ID", "").strip()
    if not _SESSION_ID.fullmatch(session):
        raise OpsError("ValidationError",
                       "Missing session tracking ID: set SKILL_SESSION_ID before running to a freshly"
                       " generated 32-character lowercase hexadecimal string for this skill's current"
                       " session (generated once per session, never shared with other skills).")
    try:
        manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"),
                              object_pairs_hook=_manifest_object, parse_constant=_invalid_json_constant)
    except (OSError, ValueError) as error:
        raise OpsError("ValidationError", "Cannot read valid JSON from references/manifest.json.") from error
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise OpsError("ValidationError", "references/manifest.json must have a non-empty string version.")
    if os.environ.get("SKILL_VERSION", "") != version:
        raise OpsError("ValidationError",
                       "SKILL_VERSION must match the top-level version in this skill's references/manifest.json.")
    return f"AlibabaCloud-Agent-Skills/alibabacloud-flink-ai-ops/{session} skill-version/{version}"


def create_client(region):
    """Create the Ververica SDK client using the default credential chain."""
    agent = user_agent()

    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_tea_openapi.models import Config
    from alibabacloud_ververica20220718.client import Client
    from darabonba.runtime import RetryOptions

    if not hasattr(Client, "trigger_patrol_with_options"):
        raise OpsError("DependencyError", "Install SDK 1.14.0 from assets/requirements.txt.")

    return Client(Config(
        credential=CredentialClient(),
        endpoint=f"ververica.{region}.aliyuncs.com",
        user_agent=agent,
        retry_options=RetryOptions(retryable=False),
    ))


def runtime_options(connect_timeout, read_timeout, timeout=None, *, for_chat=False):
    """Convert timeouts to milliseconds and cap them by the remaining budget."""
    from darabonba.runtime import RuntimeOptions

    if read_timeout is None:
        read_timeout = DEFAULT_CHAT_READ_TIMEOUT if for_chat else DEFAULT_READ_TIMEOUT
    if timeout is not None:
        positive_number(timeout, "timeout")
    remaining = timeout if timeout is not None else float("inf")
    return RuntimeOptions(
        connect_timeout=max(1, int(min(connect_timeout, remaining) * 1000)),
        read_timeout=max(1, int(min(read_timeout, remaining) * 1000)),
        autoretry=False,
        max_attempts=1,
    )
