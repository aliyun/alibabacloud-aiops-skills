#!/usr/bin/env python3
"""Private, session-isolated A2A context persistence."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

from . import secure_store


_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".aliyun_agenthub", "contexts")
_RESERVED_LEGACY_STEMS = frozenset({"config", "credentials", "profile"})


def _validate_component(raw: str, field: str) -> str:
    if raw is None:
        raise ValueError(f"{field} cannot be empty")
    value = str(raw)
    if not value or value in (".", ".."):
        raise ValueError(f"{field} cannot be empty or a traversal component")
    if "\x00" in value or "/" in value or "\\" in value:
        raise ValueError(f"{field} contains unsafe path characters")
    return value


def _context_root() -> Path:
    return secure_store.ensure_private_dir(_CACHE_DIR)


def _session_digest(session_id: str) -> str:
    session = _validate_component(session_id, "session_id")
    return hashlib.sha256(session.encode("utf-8")).hexdigest()


def _session_file(session_id: str) -> str:
    return str(_context_root() / f"{_session_digest(session_id)}.json")


def _lock_file(session_id: str) -> Path:
    return _context_root() / f"{_session_digest(session_id)}.lock"


def _legacy_candidates(session_id: str) -> tuple[Path, ...]:
    session = _validate_component(session_id, "session_id")
    if session.lower() in _RESERVED_LEGACY_STEMS:
        return ()
    root = secure_store.resolve_path(_CACHE_DIR)
    candidates = [root / f"{session}.json"]
    # The released legacy layout stored files directly below
    # ~/.aliyun_agenthub; patched/test roots historically stored them at root.
    if root.name == "contexts":
        candidates.append(root.parent / f"{session}.json")
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return tuple(unique)


def _mapping(data: object) -> dict[str, str]:
    if not isinstance(data, dict):
        return {}
    return {
        str(key): value
        for key, value in data.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def _load_or_migrate_locked(session_id: str, destination: Path) -> dict[str, str]:
    current = secure_store.read_json(destination)
    if current is not None:
        return _mapping(current)

    for legacy_path in _legacy_candidates(session_id):
        try:
            legacy = secure_store.read_json(legacy_path)
        except FileNotFoundError:
            continue
        if legacy is None:
            continue
        migrated = _mapping(legacy)
        secure_store.atomic_write_json(destination, migrated)
        secure_store.secure_unlink(legacy_path, missing_ok=True)
        return migrated
    return {}


def load_context_id(session_id: str, agent_id: str) -> Optional[str]:
    if not session_id or not agent_id:
        return None
    _validate_component(session_id, "session_id")
    agent = _validate_component(agent_id, "agent_id")
    destination = Path(_session_file(session_id))
    with secure_store.file_lock(_lock_file(session_id), exclusive=True) as acquired:
        if not acquired:
            raise secure_store.SecureStoreError("could not acquire context lock")
        return _load_or_migrate_locked(session_id, destination).get(agent)


def save_context_id(session_id: str, agent_id: str, context_id: str) -> None:
    if not session_id or not agent_id or not context_id:
        return
    _validate_component(session_id, "session_id")
    agent = _validate_component(agent_id, "agent_id")
    context = str(context_id)
    if "\x00" in context:
        raise ValueError("context_id contains NUL")
    destination = Path(_session_file(session_id))
    with secure_store.file_lock(_lock_file(session_id), exclusive=True) as acquired:
        if not acquired:
            raise secure_store.SecureStoreError("could not acquire context lock")
        data = _load_or_migrate_locked(session_id, destination)
        data[agent] = context
        secure_store.atomic_write_json(destination, data)
