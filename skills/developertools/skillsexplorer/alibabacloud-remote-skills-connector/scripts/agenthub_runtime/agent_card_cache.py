from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

try:  # agenthub.py exposes scripts/ as the import root.
    from a2a_proxy.references import secure_store
except ModuleNotFoundError:  # Tests may import scripts.agenthub_runtime directly.
    from scripts.a2a_proxy.references import secure_store


AGENT_CARD_CACHE_ENV = "AGENTHUB_AGENT_CARD_CACHE_DIR"
DEFAULT_AGENT_CARD_CACHE_ROOT = Path.home() / ".aliyun_agenthub" / "agent_cards"
AGENT_CARD_CACHE_SCHEMA_VERSION = 2
AGENT_CARD_CACHE_SOURCE = "validated_agent_card"
_CACHE_KEYS = {
    "schemaVersion",
    "source",
    "sessionId",
    "agentId",
    "endpoint",
    "rpcPath",
    "supportsStreaming",
    "updatedAt",
}


@dataclass(frozen=True)
class AgentCardRecord:
    session_id: str
    agent_id: str
    endpoint: str
    stdout: str
    supports_streaming: bool
    updated_at: str = ""


def agent_card_cache_root(env: Mapping[str, str] | None = None) -> Path:
    return secure_store.resolve_path_env(
        AGENT_CARD_CACHE_ENV,
        DEFAULT_AGENT_CARD_CACHE_ROOT,
        env=env,
    )


def _cache_path(session_id: str, agent_id: str, *, root: Path | None = None) -> Path:
    digest = hashlib.sha256(f"{session_id}\0{agent_id}".encode("utf-8")).hexdigest()
    cache_root = secure_store.resolve_path(root) if root is not None else agent_card_cache_root()
    return cache_root / f"{digest}.json"


def _cache_lock(path: Path) -> Path:
    return path.with_suffix(".lock")


def read_agent_card_record(
    session_id: str,
    agent_id: str,
    endpoint: str,
    *,
    root: Path | None = None,
) -> AgentCardRecord | None:
    path = _cache_path(session_id, agent_id, root=root)
    secure_store.ensure_private_dir(path.parent)
    with secure_store.file_lock(_cache_lock(path), exclusive=False) as acquired:
        if not acquired:
            raise secure_store.SecureStoreError("could not acquire Agent Card cache lock")
        data = secure_store.read_json(path)
    if data is None:
        return None
    if not isinstance(data, dict):
        return None
    # Version 1 caches may contain a boolean inferred from human description
    # text.  Treat every legacy/unknown provenance record as a cache miss so
    # the caller fetches and validates a structured Agent Card again.
    if set(data) != _CACHE_KEYS:
        return None
    if data.get("schemaVersion") != AGENT_CARD_CACHE_SCHEMA_VERSION:
        return None
    if data.get("source") != AGENT_CARD_CACHE_SOURCE:
        return None
    if data.get("sessionId") != session_id:
        return None
    if data.get("agentId") != agent_id:
        return None
    if data.get("endpoint") != endpoint:
        return None
    if data.get("rpcPath") != "/rpc":
        return None
    supports_streaming = data.get("supportsStreaming")
    if type(supports_streaming) is not bool:
        return None
    return AgentCardRecord(
        session_id=session_id,
        agent_id=agent_id,
        endpoint=endpoint,
        stdout="",
        supports_streaming=supports_streaming,
        updated_at=str(data.get("updatedAt") or ""),
    )


def write_agent_card_record(
    session_id: str,
    agent_id: str,
    endpoint: str,
    stdout: str,
    supports_streaming: bool,
    *,
    root: Path | None = None,
) -> AgentCardRecord:
    if type(supports_streaming) is not bool:
        raise ValueError("supports_streaming must be a JSON boolean")
    record = AgentCardRecord(
        session_id=session_id,
        agent_id=agent_id,
        endpoint=endpoint,
        stdout=stdout,
        supports_streaming=supports_streaming,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    path = _cache_path(session_id, agent_id, root=root)
    secure_store.ensure_private_dir(path.parent)
    payload = {
        "schemaVersion": AGENT_CARD_CACHE_SCHEMA_VERSION,
        "source": AGENT_CARD_CACHE_SOURCE,
        "sessionId": record.session_id,
        "agentId": record.agent_id,
        "endpoint": record.endpoint,
        "rpcPath": "/rpc",
        "supportsStreaming": record.supports_streaming,
        "updatedAt": record.updated_at,
    }
    with secure_store.file_lock(_cache_lock(path), exclusive=True) as acquired:
        if not acquired:
            raise secure_store.SecureStoreError("could not acquire Agent Card cache lock")
        secure_store.atomic_write_json(path, payload)
    return record
