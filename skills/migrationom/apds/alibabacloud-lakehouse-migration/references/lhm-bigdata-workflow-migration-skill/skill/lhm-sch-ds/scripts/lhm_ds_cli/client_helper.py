"""Shared LHM Scheduler datasource helpers.

Provides the API client factory and response JSON parsing used by the
stateless single-step operations in `operations.py`. There is no orchestration
loop here — sequencing and user interaction are Agent-driven.
"""

import json
import os
import uuid
from typing import Any

from lhm_ds_cli.config import LhmConfig


class OperationError(Exception):
    """Raised when an operation encounters an unrecoverable error."""

    def __init__(self, err_code: str, err_message: str, request_id: str = ""):
        self.err_code = err_code
        self.err_message = err_message
        self.request_id = request_id
        super().__init__(f"[{err_code}] {err_message} (RequestId: {request_id})")


_FALLBACK_SESSION_ID = ""


def build_user_agent() -> str:
    """Build the observability UA: AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{version}.

    The session-id is taken from the LHM_SESSION_ID environment variable
    (generated once at session start by the dispatcher and reused across the
    whole session); when unset, a per-process fallback ID is generated once
    and cached so the UA is always present and stable within one process.
    """
    global _FALLBACK_SESSION_ID
    session_id = os.environ.get("LHM_SESSION_ID", "").strip()
    if not session_id:
        if not _FALLBACK_SESSION_ID:
            _FALLBACK_SESSION_ID = uuid.uuid4().hex
        session_id = _FALLBACK_SESSION_ID
    version = os.environ.get("LHM_SKILL_VERSION", "").strip() or "1.0.0"
    return f"AlibabaCloud-Agent-Skills/lhm-sch-ds/{session_id} skill-version/{version}"


def create_client(config: LhmConfig):
    """Create LHM Inner API client from config.
    
    Uses aliyun CLI instead of SDK for network layer.
    Credentials are resolved through the default credential chain.
    """
    # 网络层模块（与本文件同目录）
    try:
        from lhm_ds_cli import aliyun_cli
    except ImportError:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import aliyun_cli

    return aliyun_cli.AliyunCliClient(
        endpoint=config.endpoint,
        region_id=config.region_id,
        skill_name="lhm-sch-ds",
    )


def safe_parse_json(data: Any, context: str) -> Any:
    """Safely parse JSON string from API response.

    Handles cases where body.data is already a dict/list (SDK auto-parsed)
    or a raw JSON string that needs parsing.

    Args:
        data: Raw data from body.data (str, dict, list, or None).
        context: Description for error message if parsing fails.

    Returns:
        Parsed JSON object (dict or list), or the original scalar value.

    Raises:
        OperationError: If JSON is malformed.
    """
    if data is None:
        return {}
    if isinstance(data, (dict, list)):
        return data
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError) as parse_error:
        raise OperationError(
            err_code="JSON_PARSE_ERROR",
            err_message=f"Failed to parse {context}: {parse_error}. Raw data: {data}",
        ) from parse_error


def request_id_of(body) -> str:
    """Extract request_id from a response body, defaulting to empty."""
    return getattr(body, "request_id", "") or ""
