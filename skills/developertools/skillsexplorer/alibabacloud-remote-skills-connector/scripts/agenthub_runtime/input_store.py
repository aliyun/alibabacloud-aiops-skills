"""One-shot, path-confined input handles for public CLI payloads."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

try:  # agenthub.py exposes scripts/ as the import root.
    from a2a_proxy.references import secure_store
except ModuleNotFoundError:  # Tests may import scripts.agenthub_runtime directly.
    from scripts.a2a_proxy.references import secure_store


INPUT_STORE_ENV = "AGENTHUB_INPUT_STORE_DIR"
DEFAULT_INPUT_STORE_ROOT = Path.home() / ".aliyun_agenthub" / "inputs"
DEFAULT_INPUT_TTL_SECONDS = 600
MAX_INPUT_BYTES = 1024 * 1024
MAX_INPUT_METADATA_BYTES = 4096
INPUT_LOCK_SHARDS = 64
INPUT_METADATA_SCHEMA_VERSION = 1
CLEANUP_SCAN_LIMIT = 32
ALLOWED_INPUT_KINDS = frozenset({"message", "keyword"})
_INPUT_ID_RE = re.compile(r"^(message|keyword)-([0-9a-f]{32})$")
_FUTURE_MTIME_TOLERANCE_SECONDS = 300
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(r"\bLTAI[A-Za-z0-9]{12,}\b"),
    re.compile(
        r"(?i)\b(?:access[_ -]?key[_ -]?secret|security[_ -]?token|"
        r"refresh[_ -]?token|oauth[_ -]?token)\b\s*[:=]\s*[^\s,;]{8,}"
    ),
)


def _kind(raw: str) -> str:
    value = str(raw or "")
    if value not in ALLOWED_INPUT_KINDS:
        raise ValueError(f"unsupported input kind: {value!r}")
    return value


def input_store_root(
    *,
    root: os.PathLike[str] | str | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    if root is not None:
        return secure_store.resolve_path(root)
    return secure_store.resolve_path_env(
        INPUT_STORE_ENV,
        DEFAULT_INPUT_STORE_ROOT,
        env=env,
    )


def _validated_input_id(input_id: str, expected_kind: str) -> str:
    if not isinstance(input_id, str) or "\x00" in input_id:
        raise ValueError("inputId must be a managed non-path identifier")
    matched = _INPUT_ID_RE.fullmatch(input_id)
    if not matched:
        raise ValueError("inputId has an invalid format")
    if matched.group(1) != expected_kind:
        raise ValueError("inputId kind does not match the requested input kind")
    return input_id


def _input_path(root: Path, input_id: str) -> Path:
    return root / f"{input_id}.input"


def _metadata_path(root: Path, input_id: str) -> Path:
    return root / f"{input_id}.metadata.json"


def _lock_path(root: Path, input_id: str) -> Path:
    locks = secure_store.ensure_private_dir(root / "locks")
    digest = hashlib.sha256(input_id.encode("ascii")).digest()
    shard = int.from_bytes(digest[:4], "big") % INPUT_LOCK_SHARDS
    return locks / f"shard-{shard:02d}.lock"


def _metadata_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"managed input metadata field {field} is invalid")
    return float(value)


def _read_metadata(path: Path, input_id: str, kind: str) -> tuple[dict, os.stat_result]:
    payload, info = secure_store.read_private_bytes(
        path,
        max_bytes=MAX_INPUT_METADATA_BYTES,
        repair_mode=False,
    )
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("managed input metadata is invalid") from exc
    expected_fields = {
        "schemaVersion",
        "inputId",
        "kind",
        "allocatedAt",
        "expiresAt",
    }
    if not isinstance(data, dict) or set(data) != expected_fields:
        raise ValueError("managed input metadata has an invalid schema")
    if data.get("schemaVersion") != INPUT_METADATA_SCHEMA_VERSION:
        raise ValueError("managed input metadata version is unsupported")
    if data.get("inputId") != input_id or data.get("kind") != kind:
        raise ValueError("managed input metadata identity does not match")
    allocated_at = _metadata_number(data.get("allocatedAt"), "allocatedAt")
    expires_at = _metadata_number(data.get("expiresAt"), "expiresAt")
    if expires_at <= allocated_at:
        raise ValueError("managed input metadata deadline is invalid")
    return data, info


def _unlink_metadata(path: Path, info: os.stat_result) -> None:
    secure_store.secure_unlink(
        path,
        missing_ok=True,
        expected_identity=(info.st_dev, info.st_ino),
        repair_mode=False,
    )


def _cleanup_expired_inputs(root: Path, *, exclude_input_id: str | None = None) -> None:
    """Bounded opportunistic cleanup for expired, unconsumed managed inputs."""
    now = time.time()
    try:
        names = os.listdir(root)
    except FileNotFoundError:
        return
    suffix = ".metadata.json"
    examined = 0
    for name in names:
        if examined >= CLEANUP_SCAN_LIMIT or not name.endswith(suffix):
            continue
        input_id = name[: -len(suffix)]
        matched = _INPUT_ID_RE.fullmatch(input_id)
        if not matched or input_id == exclude_input_id:
            continue
        examined += 1
        kind = matched.group(1)
        try:
            with secure_store.file_lock(
                _lock_path(root, input_id),
                exclusive=True,
                blocking=False,
            ) as acquired:
                if not acquired:
                    continue
                metadata_path = _metadata_path(root, input_id)
                metadata, metadata_info = _read_metadata(metadata_path, input_id, kind)
                if _metadata_number(metadata["expiresAt"], "expiresAt") > now:
                    continue
                input_path = _input_path(root, input_id)
                try:
                    secure_store.secure_unlink(input_path, missing_ok=True, repair_mode=False)
                finally:
                    _unlink_metadata(metadata_path, metadata_info)
        except (OSError, RuntimeError, ValueError):
            # Unsafe/corrupt paths stay fail-closed and are never followed.
            continue


def allocate_input(
    kind: str,
    *,
    root: os.PathLike[str] | str | None = None,
    ttl_seconds: int = DEFAULT_INPUT_TTL_SECONDS,
) -> dict[str, object]:
    input_kind = _kind(kind)
    if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
        raise ValueError("input TTL must be a positive integer")
    managed_root = secure_store.ensure_private_dir(input_store_root(root=root))
    secure_store.ensure_private_dir(managed_root / "locks")
    _cleanup_expired_inputs(managed_root)

    for _attempt in range(32):
        input_id = f"{input_kind}-{secrets.token_hex(16)}"
        path = _input_path(managed_root, input_id)
        metadata_path = _metadata_path(managed_root, input_id)
        allocated_at = time.time()
        expires_timestamp = allocated_at + ttl_seconds
        try:
            secure_store.create_private_file(path)
        except FileExistsError:
            continue
        try:
            secure_store.atomic_write_json(
                metadata_path,
                {
                    "schemaVersion": INPUT_METADATA_SCHEMA_VERSION,
                    "inputId": input_id,
                    "kind": input_kind,
                    "allocatedAt": allocated_at,
                    "expiresAt": expires_timestamp,
                },
                repair_existing=False,
            )
        except BaseException:
            try:
                secure_store.secure_unlink(path, missing_ok=True, repair_mode=False)
            finally:
                raise
        expires_at = datetime.fromtimestamp(
            expires_timestamp,
            tz=timezone.utc,
        ).isoformat()
        return {
            "inputId": input_id,
            "kind": input_kind,
            "path": str(path),
            "expiresAt": expires_at,
        }
    raise RuntimeError("could not allocate a unique managed input handle")


def _read_fd(fd: int, maximum: int) -> bytes:
    chunks: list[bytes] = []
    remaining = maximum + 1
    while remaining > 0:
        chunk = os.read(fd, min(65536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def validate_input_text(text: str, kind: str) -> str:
    """Validate a native-text payload without rewriting user intent."""
    _kind(kind)
    if not isinstance(text, str):
        raise ValueError("managed input must be text")
    if not text:
        raise ValueError("managed input is empty")
    if "\x00" in text:
        raise ValueError("managed input contains NUL")
    if any(pattern.search(text) for pattern in _SENSITIVE_VALUE_PATTERNS):
        raise ValueError(
            "managed input appears to contain a credential; remove secrets and retry"
        )
    return text


def consume_input(
    input_id: str,
    kind: str,
    *,
    root: os.PathLike[str] | str | None = None,
    ttl_seconds: int = DEFAULT_INPUT_TTL_SECONDS,
    max_bytes: int = MAX_INPUT_BYTES,
) -> str:
    input_kind = _kind(kind)
    managed_id = _validated_input_id(input_id, input_kind)
    if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
        raise ValueError("input TTL must be a positive integer")
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("input size limit must be a positive integer")

    managed_root = secure_store.ensure_private_dir(input_store_root(root=root))
    _cleanup_expired_inputs(managed_root, exclude_input_id=managed_id)
    path = _input_path(managed_root, managed_id)
    metadata_path = _metadata_path(managed_root, managed_id)
    lock = _lock_path(managed_root, managed_id)
    with secure_store.file_lock(lock, exclusive=True, blocking=True) as acquired:
        if not acquired:
            raise RuntimeError("could not acquire managed input lock")
        try:
            metadata, metadata_info = _read_metadata(
                metadata_path,
                managed_id,
                input_kind,
            )
        except FileNotFoundError as exc:
            # Pre-metadata development handles cannot prove their allocation
            # deadline. Remove a safely owned input rather than accepting it.
            secure_store.secure_unlink(path, missing_ok=True, repair_mode=False)
            raise ValueError("managed input handle has no trusted deadline") from exc
        try:
            fd, info = secure_store.open_private_file(
                path,
                os.O_RDONLY,
                repair_mode=False,
            )
        except FileNotFoundError:
            _unlink_metadata(metadata_path, metadata_info)
            raise
        try:
            now = time.time()
            allocated_at = _metadata_number(metadata["allocatedAt"], "allocatedAt")
            expires_at = _metadata_number(metadata["expiresAt"], "expiresAt")
            if (
                now > expires_at
                or info.st_mtime < allocated_at - _FUTURE_MTIME_TOLERANCE_SECONDS
                or info.st_mtime > now + _FUTURE_MTIME_TOLERANCE_SECONDS
            ):
                secure_store.secure_unlink(
                    path,
                    missing_ok=False,
                    expected_identity=(info.st_dev, info.st_ino),
                    repair_mode=False,
                )
                _unlink_metadata(metadata_path, metadata_info)
                raise ValueError("managed input handle has expired")
            if info.st_size > max_bytes:
                secure_store.secure_unlink(
                    path,
                    missing_ok=False,
                    expected_identity=(info.st_dev, info.st_ino),
                    repair_mode=False,
                )
                _unlink_metadata(metadata_path, metadata_info)
                raise ValueError("managed input exceeds the size limit")

            payload = _read_fd(fd, max_bytes)
            if len(payload) > max_bytes:
                secure_store.secure_unlink(
                    path,
                    missing_ok=False,
                    expected_identity=(info.st_dev, info.st_ino),
                    repair_mode=False,
                )
                _unlink_metadata(metadata_path, metadata_info)
                raise ValueError("managed input exceeds the size limit")
            after_read = os.fstat(fd)
            if (
                (after_read.st_dev, after_read.st_ino) != (info.st_dev, info.st_ino)
                or after_read.st_size != info.st_size
                or after_read.st_mtime_ns != info.st_mtime_ns
                or len(payload) != after_read.st_size
            ):
                raise RuntimeError("managed input changed while it was being consumed")
            try:
                text = payload.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                secure_store.secure_unlink(
                    path,
                    missing_ok=False,
                    expected_identity=(info.st_dev, info.st_ino),
                    repair_mode=False,
                )
                _unlink_metadata(metadata_path, metadata_info)
                raise ValueError("managed input is not valid UTF-8") from exc
            try:
                validate_input_text(text, input_kind)
            except ValueError:
                secure_store.secure_unlink(
                    path,
                    missing_ok=False,
                    expected_identity=(info.st_dev, info.st_ino),
                    repair_mode=False,
                )
                _unlink_metadata(metadata_path, metadata_info)
                raise

            # The handle ceases to exist before the caller can perform any
            # credential or network operation.
            secure_store.secure_unlink(
                path,
                missing_ok=False,
                expected_identity=(info.st_dev, info.st_ino),
                repair_mode=False,
            )
            _unlink_metadata(metadata_path, metadata_info)
            return text
        finally:
            os.close(fd)
