from __future__ import annotations

import hashlib
import hmac
import json
import re

try:
    from scripts.a2a_proxy.references import task_store
except ImportError:  # pragma: no cover - direct package execution
    from a2a_proxy.references import task_store


_ACTION_REF_RE = re.compile(r"^[0-9a-f]{64}$")


def _field(record: object, *names: str):
    for name in names:
        if isinstance(record, dict) and name in record:
            return record[name]
        if hasattr(record, name):
            return getattr(record, name)
    return None


def _identity(record: object) -> tuple[str, str, str, str, int]:
    session_id = _field(record, "sessionId", "session_id")
    agent_id = _field(record, "agentId", "agent_id")
    endpoint = _field(record, "endpoint")
    task_id = _field(record, "taskId", "task_id")
    hitl_round = _field(record, "hitlRound", "hitl_round")
    if not all(isinstance(value, str) and value for value in (session_id, agent_id, endpoint, task_id)):
        raise ValueError("follow action record is incomplete")
    if type(hitl_round) is not int or hitl_round <= 0:
        raise ValueError("follow action round is invalid")
    task_store.validate_path_id(session_id, "session_id")
    task_store.validate_path_id(agent_id, "agent_id")
    task_store.validate_path_id(task_id, "task_id")
    return session_id, agent_id, endpoint, task_id, hitl_round


def _selector(identity: tuple[str, str, str, str, int]) -> str:
    encoded = json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"agenthub-follow-v1\0" + encoded).hexdigest()


def _current_pending(identity: tuple[str, str, str, str, int]) -> dict | None:
    session_id, agent_id, _endpoint, task_id, _round = identity
    for record in task_store.list_records(session_id, agent_id):
        if record.get("taskId") != task_id:
            continue
        if record.get("activeState") != task_store.STATE_PENDING:
            return None
        try:
            return record if _identity(record) == identity else None
        except ValueError:
            return None
    return None


def issue_follow_action(record: object) -> str:
    if _field(record, "activeState", "active_state") != task_store.STATE_PENDING:
        raise ValueError("follow action requires a pending task round")
    identity = _identity(record)
    if _current_pending(identity) is None:
        raise ValueError("follow action does not match the current pending task round")
    return _selector(identity)


def resolve_follow_action(action_ref: str) -> dict:
    if not isinstance(action_ref, str) or not _ACTION_REF_RE.fullmatch(action_ref):
        raise ValueError("invalid follow action reference")
    for session_id, agent_id in task_store.list_namespaces():
        try:
            records = task_store.list_records(session_id, agent_id)
        except (OSError, RuntimeError, ValueError):
            continue
        for record in records:
            if record.get("activeState") != task_store.STATE_PENDING:
                continue
            try:
                expected = _selector(_identity(record))
            except ValueError:
                continue
            if hmac.compare_digest(expected, action_ref):
                return record
    raise ValueError("follow action is stale or unknown")
