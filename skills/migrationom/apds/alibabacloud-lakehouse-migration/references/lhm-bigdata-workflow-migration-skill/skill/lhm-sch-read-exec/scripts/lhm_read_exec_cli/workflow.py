"""Shared LHM Scheduler workflow helpers.

Provides the API client factory, response JSON parsing, and datasource
candidate extraction used by the stateless single-step operations in
`single_step.py`. Polling and orchestration are Agent-driven; there is no
synchronous workflow loop here.
"""

import json
import os
import uuid
from typing import List

from lhm_read_exec_cli.config import LhmConfig


class WorkflowError(Exception):
    """Raised when workflow encounters an unrecoverable error."""

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
    return f"AlibabaCloud-Agent-Skills/lhm-sch-read-exec/{session_id} skill-version/{version}"


def _create_client(config: LhmConfig):
    """Create LHM CLI client from config.
    
    Uses aliyun CLI instead of SDK for network layer.
    Credentials are resolved through the default credential chain.
    """
    # 网络层模块（与本文件同目录）
    try:
        from lhm_read_exec_cli import aliyun_cli
    except ImportError:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import aliyun_cli

    return aliyun_cli.AliyunCliClient(
        endpoint=config.endpoint,
        region_id=config.region_id,
        skill_name="lhm-sch-read-exec",
    )


def _safe_parse_json(data, context: str):
    """Safely parse JSON string from API response.

    Handles cases where body.data is already a dict/list (SDK auto-parsed),
    an AttrBody object (from aliyun_cli wrapper), or a raw JSON string that needs parsing.

    Args:
        data: Raw data from body.data (str, dict, list, AttrBody, or None).
        context: Description for error message if parsing fails.

    Returns:
        Parsed JSON object (dict or list).

    Raises:
        WorkflowError: If JSON is malformed.
    """
    if data is None:
        return {}
    # Handle AttrBody objects from aliyun_cli wrapper
    if hasattr(data, 'to_dict') and callable(getattr(data, 'to_dict')):
        return data.to_dict()
    if isinstance(data, (dict, list)):
        return data
    # First try direct JSON parse
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: extract JSON array/object from prefixed string
    # (e.g. "检索到多个数据源---[\"a\",\"b\"]" → ["a","b"])
    if isinstance(data, str):
        for i, ch in enumerate(data):
            if ch in ('[', '{'):
                bracket = data[i:]
                try:
                    return json.loads(bracket)
                except (json.JSONDecodeError, TypeError):
                    break
    raise WorkflowError(
        err_code="JSON_PARSE_ERROR",
        err_message=f"Failed to parse {context}. Raw data: {data}",
    )


def select_datasource_from_candidates(candidates: List[dict]) -> List[str]:
    """Extract datasource names from E610R1002 candidate list.

    The Agent presents these to the user and re-invokes the start step with a
    confirmed exact name. This replaces the old interactive prompt loop, which
    is incompatible with stateless single-step execution.

    Args:
        candidates: List of datasource dicts from an E610R1002 response.

    Returns:
        List of candidate datasource names.
    """
    names: List[str] = []
    for candidate in candidates or []:
        name = candidate.get("name", candidate.get("dataSourceName"))
        if name:
            names.append(name)
    return names
