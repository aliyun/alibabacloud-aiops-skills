#!/usr/bin/env python3
"""
A2A HITL task store.

Persists recoverable task state per local client session:
~/.aliyun_agenthub/a2a_tasks/{session_id}/{agent_id}/{state}/{task_id}.json
"""

import contextlib
import os
from datetime import datetime, timedelta
from typing import Dict, Iterator, List, Optional, Tuple

from . import secure_store


TASK_STORE_ENV = "A2A_TASK_STORE_DIR"
DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), ".aliyun_agenthub", "a2a_tasks")

STATE_PENDING = "pending"
STATE_INPUT_REQUIRED = "input_required"
STATE_RUNNING = "running"
STATE_READY = "ready"
STATE_DELIVERED = "delivered"

ACTIVE_STATES = (STATE_PENDING, STATE_INPUT_REQUIRED, STATE_RUNNING, STATE_READY)
ALL_STATES = ACTIVE_STATES + (STATE_DELIVERED,)
_LEGACY_MESSAGE_FIELDS = ("originalMessagePreview", "submittedMessagePreview")

_FALLBACK_PRIORITY = {
    STATE_READY: 4,
    STATE_RUNNING: 3,
    STATE_INPUT_REQUIRED: 2,
    STATE_PENDING: 1,
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def add_seconds_iso(seconds: int) -> str:
    return (datetime.now().astimezone() + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return parsed
    except ValueError:
        return None


def task_root() -> str:
    return str(secure_store.resolve_path_env(TASK_STORE_ENV, DEFAULT_ROOT))


def validate_path_id(raw: str, field: str = "id") -> str:
    if raw is None:
        raise ValueError(f"{field} 不能为空")
    value = str(raw)
    if not value:
        raise ValueError(f"{field} 不能为空")
    if "/" in value or "\\" in value or "\x00" in value:
        raise ValueError(f"{field} 包含不安全的路径字符")
    if value in (".", ".."):
        raise ValueError(f"{field} 包含路径遍历片段")
    return value


def agent_dir(session_id: str, agent_id: str) -> str:
    sid = validate_path_id(session_id, "session_id")
    aid = validate_path_id(agent_id, "agent_id")
    return str(secure_store.resolve_path(task_root()) / sid / aid)


def ensure_agent_dirs(session_id: str, agent_id: str) -> str:
    root = secure_store.ensure_private_dir(task_root())
    sid = validate_path_id(session_id, "session_id")
    aid = validate_path_id(agent_id, "agent_id")
    session_root = secure_store.ensure_private_dir(root / sid)
    base_path = secure_store.ensure_private_dir(session_root / aid)
    for name in ALL_STATES + ("locks",):
        secure_store.ensure_private_dir(base_path / name)
    return str(base_path)


def record_path(session_id: str, agent_id: str, state: str, task_id: str) -> str:
    if state not in ALL_STATES:
        raise ValueError(f"未知任务状态目录: {state}")
    tid = validate_path_id(task_id, "task_id")
    return os.path.join(ensure_agent_dirs(session_id, agent_id), state, f"{tid}.json")


def lock_path(session_id: str, agent_id: str, name: str) -> str:
    lname = validate_path_id(name, "lock_name")
    return os.path.join(ensure_agent_dirs(session_id, agent_id), "locks", f"{lname}.lock")


def atomic_write_json(path: str, data: dict) -> None:
    secure_store.atomic_write_json(path, data)


def read_json(path: str) -> Optional[dict]:
    return secure_store.read_json(path)


def _remove(path: str) -> None:
    secure_store.secure_unlink(path, missing_ok=True)


@contextlib.contextmanager
def _flock(path: str, exclusive: bool = True, blocking: bool = True) -> Iterator[bool]:
    with secure_store.file_lock(
        path,
        exclusive=exclusive,
        blocking=blocking,
    ) as acquired:
        yield acquired


@contextlib.contextmanager
def scan_lock(session_id: str, agent_id: str) -> Iterator[bool]:
    with _flock(lock_path(session_id, agent_id, "scan"), exclusive=True, blocking=False) as acquired:
        yield acquired


@contextlib.contextmanager
def task_transaction(session_id: str, agent_id: str, task_id: str) -> Iterator["TaskTransaction"]:
    validate_path_id(task_id, "task_id")
    with _flock(lock_path(session_id, agent_id, task_id), exclusive=True, blocking=True) as acquired:
        if not acquired:
            raise RuntimeError("无法获取 task lock")
        tx = TaskTransaction(session_id=session_id, agent_id=agent_id, task_id=task_id)
        yield tx


class TaskTransaction:
    def __init__(self, session_id: str, agent_id: str, task_id: str):
        self.session_id = validate_path_id(session_id, "session_id")
        self.agent_id = validate_path_id(agent_id, "agent_id")
        self.task_id = validate_path_id(task_id, "task_id")
        self.base_dir = ensure_agent_dirs(self.session_id, self.agent_id)

    def path(self, state: str) -> str:
        if state not in ALL_STATES:
            raise ValueError(f"未知任务状态目录: {state}")
        return os.path.join(self.base_dir, state, f"{self.task_id}.json")

    def read_state(self, state: str) -> Optional[dict]:
        path = self.path(state)
        record = read_json(path)
        if record and any(field in record for field in _LEGACY_MESSAGE_FIELDS):
            # One-time in-place schema hygiene for development-era records.
            # Preserve the state/revision verbatim; only remove message text.
            record = dict(record)
            for field in _LEGACY_MESSAGE_FIELDS:
                record.pop(field, None)
            atomic_write_json(path, record)
        return record

    def read_all(self) -> Dict[str, dict]:
        records = {}
        for state in ALL_STATES:
            data = self.read_state(state)
            if data:
                records[state] = data
        return records

    def normalize(self) -> Tuple[Optional[str], Optional[dict]]:
        records = self.read_all()
        delivered = records.get(STATE_DELIVERED)
        if delivered:
            for state in ACTIVE_STATES:
                _remove(self.path(state))
            return STATE_DELIVERED, delivered

        active = {state: records[state] for state in ACTIVE_STATES if state in records}
        if not active:
            return None, None

        def sort_key(item):
            state, record = item
            rev = record.get("stateRevision")
            if isinstance(rev, int):
                return (rev, _FALLBACK_PRIORITY.get(state, 0))
            return (-1, _FALLBACK_PRIORITY.get(state, 0))

        keep_state, keep_record = max(active.items(), key=sort_key)
        for state in active:
            if state != keep_state:
                _remove(self.path(state))
        return keep_state, keep_record

    def next_revision(self) -> int:
        records = self.read_all()
        revisions = [
            r.get("stateRevision")
            for r in records.values()
            if isinstance(r.get("stateRevision"), int)
        ]
        return (max(revisions) if revisions else 0) + 1

    def enter(self, state: str, record: dict) -> dict:
        if state not in ALL_STATES:
            raise ValueError(f"未知任务状态: {state}")
        self.normalize()
        new_record = dict(record)
        # Older development builds persisted shortened user messages.  Never
        # carry those fields into a newly written state record.
        for field in _LEGACY_MESSAGE_FIELDS:
            new_record.pop(field, None)
        new_record["schemaVersion"] = new_record.get("schemaVersion", 1)
        new_record["taskId"] = self.task_id
        new_record["sessionId"] = self.session_id
        new_record["agentId"] = self.agent_id
        new_record["updatedAt"] = now_iso()
        new_record["stateRevision"] = self.next_revision()
        if state == STATE_DELIVERED:
            new_record.pop("activeState", None)
            new_record["archiveState"] = STATE_DELIVERED
            if "deliveredAt" not in new_record:
                new_record["deliveredAt"] = now_iso()
        else:
            new_record.pop("archiveState", None)
            new_record["activeState"] = state
            if "enteredStateAt" not in new_record:
                new_record["enteredStateAt"] = now_iso()
        atomic_write_json(self.path(state), new_record)
        if state == STATE_DELIVERED:
            for old_state in ACTIVE_STATES:
                _remove(self.path(old_state))
        else:
            for old_state in ACTIVE_STATES:
                if old_state != state:
                    _remove(self.path(old_state))
        return new_record

    def remove_active(self) -> None:
        for state in ACTIVE_STATES:
            _remove(self.path(state))

    def remove_all(self) -> None:
        for state in ALL_STATES:
            _remove(self.path(state))


def _task_id_from_filename(filename: str) -> Optional[str]:
    if not filename.endswith(".json"):
        return None
    return filename[:-5]


def _private_child_directories(parent: str, field: str) -> List[str]:
    """List validated real private child directories without following links."""
    base = secure_store.ensure_private_dir(parent)
    try:
        names = os.listdir(base)
    except FileNotFoundError:
        return []
    accepted = []
    for raw_name in names:
        try:
            name = validate_path_id(raw_name, field)
            # secure_store re-lstats, opens O_NOFOLLOW, checks ownership/mode,
            # and verifies object identity. A concurrent swap is revalidated
            # again by list_records before any record becomes trusted.
            secure_store.ensure_private_dir(base / name, repair_mode=True)
        except (OSError, ValueError):
            continue
        accepted.append(name)
    return sorted(set(accepted))


def list_namespaces(session_id: Optional[str] = None) -> List[Tuple[str, str]]:
    """Return validated ``(session_id, agent_id)`` task-store namespaces.

    This is the only supported cross-namespace discovery surface. Callers must
    still use :func:`list_records`, which reopens every current record while
    holding its task lock.
    """
    root = secure_store.ensure_private_dir(task_root())
    if session_id is None:
        session_ids = _private_child_directories(str(root), "session_id")
    else:
        sid = validate_path_id(session_id, "session_id")
        candidate = root / sid
        try:
            candidate.lstat()
            secure_store.ensure_private_dir(candidate, repair_mode=True)
        except FileNotFoundError:
            return []
        session_ids = [sid]

    namespaces: List[Tuple[str, str]] = []
    for sid in session_ids:
        session_root = root / sid
        for aid in _private_child_directories(str(session_root), "agent_id"):
            namespaces.append((sid, aid))
    return namespaces


def list_task_ids(session_id: str, agent_id: str, states: Tuple[str, ...] = ALL_STATES) -> List[str]:
    base = ensure_agent_dirs(session_id, agent_id)
    ids = set()
    for state in states:
        if state not in ALL_STATES:
            continue
        folder = os.path.join(base, state)
        try:
            filenames = os.listdir(folder)
        except FileNotFoundError:
            continue
        for filename in filenames:
            task_id = _task_id_from_filename(filename)
            if task_id:
                ids.add(task_id)
    return sorted(ids)


def list_records(
    session_id: str,
    agent_id: str,
    include_delivered: bool = False,
) -> List[dict]:
    states = ALL_STATES if include_delivered else ACTIVE_STATES
    records = []
    for task_id in list_task_ids(session_id, agent_id, states=states):
        with task_transaction(session_id, agent_id, task_id) as tx:
            _state, record = tx.normalize()
            if not record:
                continue
            if not include_delivered and record.get("archiveState") == STATE_DELIVERED:
                continue
            records.append(record)
    records.sort(key=lambda r: r.get("updatedAt", ""))
    return records


def due_records(session_id: str, agent_id: str, states: Tuple[str, ...]) -> List[dict]:
    now = datetime.now().astimezone()
    records = []
    for task_id in list_task_ids(session_id, agent_id, states=states):
        with task_transaction(session_id, agent_id, task_id) as tx:
            _state, record = tx.normalize()
            if not record:
                continue
            if record.get("activeState") not in states:
                continue
            next_probe = parse_time(record.get("nextProbeAt"))
            if next_probe is None or next_probe <= now:
                records.append(record)
    records.sort(key=lambda r: r.get("nextProbeAt") or "")
    return records
