#!/usr/bin/env python3
"""Small, fail-closed primitives for private local state.

The module deliberately uses descriptor-based validation around every file
open.  Callers are still responsible for holding an application-level lock
for a complete read/modify/write transaction.
"""

from __future__ import annotations

import contextlib
import errno
import fcntl
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping


PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class SecureStoreError(ValueError):
    """Managed state failed a security invariant."""


def resolve_path(value: os.PathLike[str] | str) -> Path:
    raw = os.fspath(value)
    if not raw or "\x00" in raw:
        raise SecureStoreError("managed state path is empty or contains NUL")
    return Path(os.path.abspath(os.path.expanduser(raw)))


def resolve_path_env(
    env_name: str,
    default: os.PathLike[str] | str,
    *,
    env: Mapping[str, str] | None = None,
) -> Path:
    source = os.environ if env is None else env
    configured = source.get(env_name)
    return resolve_path(configured if configured else default)


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _require_nofollow() -> None:
    if not _O_NOFOLLOW:
        raise SecureStoreError("this platform does not provide O_NOFOLLOW")


def _assert_same_object(
    before: os.stat_result,
    after: os.stat_result,
    path: Path,
) -> None:
    if _identity(before) != _identity(after):
        raise SecureStoreError(f"managed state changed while opening: {path}")


def _validate_ancestor(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        # macOS exposes trusted system aliases such as /var -> /private/var.
        # They are outside the managed subtree and cannot be replaced by the
        # current user.  User-owned or nested symlink ancestors remain fatal.
        if path.parent != Path(path.anchor) or info.st_uid != 0:
            raise SecureStoreError(f"managed state ancestor is a symlink: {path}")
        followed = path.stat()
        if not stat.S_ISDIR(followed.st_mode):
            raise SecureStoreError(f"system ancestor alias is not a directory: {path}")
        return
    if not stat.S_ISDIR(info.st_mode):
        raise SecureStoreError(f"managed state ancestor is not a directory: {path}")
    mode = stat.S_IMODE(info.st_mode)
    public_write = mode & 0o022
    if public_write and not (mode & stat.S_ISVTX):
        raise SecureStoreError(f"managed state ancestor is publicly writable: {path}")


def _validate_private_directory(path: Path, *, repair_mode: bool) -> None:
    _require_nofollow()
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise SecureStoreError(f"managed directory is not a real directory: {path}")
    flags = os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW
    if _O_DIRECTORY:
        flags |= _O_DIRECTORY
    fd = os.open(path, flags)
    try:
        current = os.fstat(fd)
        _assert_same_object(before, current, path)
        if current.st_uid != os.geteuid():
            raise SecureStoreError(f"managed directory is owned by another user: {path}")
        mode = stat.S_IMODE(current.st_mode)
        if mode != PRIVATE_DIR_MODE:
            if not repair_mode:
                raise SecureStoreError(f"managed directory mode is not 0700: {path}")
            os.fchmod(fd, PRIVATE_DIR_MODE)
            current = os.fstat(fd)
            if stat.S_IMODE(current.st_mode) != PRIVATE_DIR_MODE:
                raise SecureStoreError(f"could not repair managed directory mode: {path}")
    finally:
        os.close(fd)


def ensure_private_dir(
    path: os.PathLike[str] | str,
    *,
    repair_mode: bool = True,
) -> Path:
    """Create a private directory without accepting symlinked components."""

    target = resolve_path(path)
    if target == Path(target.anchor):
        raise SecureStoreError("filesystem root cannot be a managed directory")

    parts = target.parts
    cursor = Path(parts[0])
    creating = False
    for component in parts[1:]:
        cursor = cursor / component
        try:
            cursor.lstat()
        except FileNotFoundError:
            parent = cursor.parent
            _validate_ancestor(parent)
            try:
                os.mkdir(cursor, PRIVATE_DIR_MODE)
            except FileExistsError:
                pass
            creating = True

        if creating or cursor == target:
            _validate_private_directory(cursor, repair_mode=repair_mode)
        else:
            _validate_ancestor(cursor)

    return target


def _validate_regular_stat(
    info: os.stat_result,
    path: Path,
    *,
    repair_mode: bool,
    fd: int,
) -> os.stat_result:
    if not stat.S_ISREG(info.st_mode):
        raise SecureStoreError(f"managed file is not regular: {path}")
    if info.st_uid != os.geteuid():
        raise SecureStoreError(f"managed file is owned by another user: {path}")
    if info.st_nlink != 1:
        raise SecureStoreError(f"managed file has multiple hard links: {path}")
    mode = stat.S_IMODE(info.st_mode)
    if mode != PRIVATE_FILE_MODE:
        if not repair_mode:
            raise SecureStoreError(f"managed file mode is not 0600: {path}")
        os.fchmod(fd, PRIVATE_FILE_MODE)
        info = os.fstat(fd)
        if stat.S_IMODE(info.st_mode) != PRIVATE_FILE_MODE:
            raise SecureStoreError(f"could not repair managed file mode: {path}")
    return info


def open_private_file(
    path: os.PathLike[str] | str,
    flags: int = os.O_RDONLY,
    *,
    create: bool = False,
    exclusive: bool = False,
    repair_mode: bool = True,
) -> tuple[int, os.stat_result]:
    """Open and validate a private regular file, returning its descriptor/stat."""

    _require_nofollow()
    managed_path = resolve_path(path)
    ensure_private_dir(managed_path.parent)
    before: os.stat_result | None
    try:
        before = managed_path.lstat()
        if stat.S_ISLNK(before.st_mode):
            raise SecureStoreError(f"managed file is a symlink: {managed_path}")
        if not stat.S_ISREG(before.st_mode):
            raise SecureStoreError(f"managed file is not regular: {managed_path}")
        if before.st_uid != os.geteuid():
            raise SecureStoreError(f"managed file is owned by another user: {managed_path}")
        if before.st_nlink != 1:
            raise SecureStoreError(f"managed file has multiple hard links: {managed_path}")
        if stat.S_IMODE(before.st_mode) != PRIVATE_FILE_MODE and not repair_mode:
            raise SecureStoreError(f"managed file mode is not 0600: {managed_path}")
    except FileNotFoundError:
        before = None

    open_flags = flags | _O_CLOEXEC | _O_NOFOLLOW
    if create:
        open_flags |= os.O_CREAT
    if exclusive:
        open_flags |= os.O_EXCL
    try:
        fd = os.open(managed_path, open_flags, PRIVATE_FILE_MODE)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.EMLINK):
            raise SecureStoreError(f"managed file refused no-follow open: {managed_path}") from exc
        raise
    try:
        current = os.fstat(fd)
        if before is not None:
            _assert_same_object(before, current, managed_path)
        current = _validate_regular_stat(
            current,
            managed_path,
            repair_mode=repair_mode,
            fd=fd,
        )
        after = managed_path.lstat()
        if stat.S_ISLNK(after.st_mode):
            raise SecureStoreError(f"managed file became a symlink: {managed_path}")
        _assert_same_object(current, after, managed_path)
        return fd, current
    except Exception:
        os.close(fd)
        raise


def create_private_file(path: os.PathLike[str] | str) -> Path:
    managed_path = resolve_path(path)
    fd, _info = open_private_file(
        managed_path,
        os.O_WRONLY,
        create=True,
        exclusive=True,
        repair_mode=False,
    )
    try:
        os.fchmod(fd, PRIVATE_FILE_MODE)
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_directory(managed_path.parent)
    return managed_path


def read_private_bytes(
    path: os.PathLike[str] | str,
    *,
    max_bytes: int | None = None,
    repair_mode: bool = True,
) -> tuple[bytes, os.stat_result]:
    fd, info = open_private_file(path, os.O_RDONLY, repair_mode=repair_mode)
    try:
        if max_bytes is not None and info.st_size > max_bytes:
            raise SecureStoreError(f"managed file exceeds size limit: {path}")
        chunks: list[bytes] = []
        remaining = None if max_bytes is None else max_bytes + 1
        while remaining is None or remaining > 0:
            size = 65536 if remaining is None else min(65536, remaining)
            chunk = os.read(fd, size)
            if not chunk:
                break
            chunks.append(chunk)
            if remaining is not None:
                remaining -= len(chunk)
        payload = b"".join(chunks)
        if max_bytes is not None and len(payload) > max_bytes:
            raise SecureStoreError(f"managed file exceeds size limit: {path}")
        return payload, info
    finally:
        os.close(fd)


def read_json(
    path: os.PathLike[str] | str,
    *,
    repair_mode: bool = True,
) -> dict[str, Any] | None:
    try:
        payload, _info = read_private_bytes(path, repair_mode=repair_mode)
    except FileNotFoundError:
        return None
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _write_all(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(fd, payload[offset:])
        if written <= 0:
            raise OSError("short write to managed state")
        offset += written


def fsync_directory(path: os.PathLike[str] | str) -> None:
    directory = ensure_private_dir(path)
    flags = os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW
    if _O_DIRECTORY:
        flags |= _O_DIRECTORY
    fd = os.open(directory, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_bytes(
    path: os.PathLike[str] | str,
    payload: bytes,
    *,
    repair_existing: bool = True,
) -> Path:
    managed_path = resolve_path(path)
    parent = ensure_private_dir(managed_path.parent)
    try:
        existing_fd, _existing = open_private_file(
            managed_path,
            os.O_RDONLY,
            repair_mode=repair_existing,
        )
    except FileNotFoundError:
        existing_fd = None
    if existing_fd is not None:
        os.close(existing_fd)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{managed_path.name}.",
        suffix=".tmp",
        dir=parent,
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, PRIVATE_FILE_MODE)
        temp_info = os.fstat(fd)
        _validate_regular_stat(
            temp_info,
            temporary_path,
            repair_mode=False,
            fd=fd,
        )
        _write_all(fd, payload)
        os.fsync(fd)
        os.close(fd)
        fd = -1

        try:
            destination_fd, _destination = open_private_file(
                managed_path,
                os.O_RDONLY,
                repair_mode=repair_existing,
            )
        except FileNotFoundError:
            destination_fd = None
        if destination_fd is not None:
            os.close(destination_fd)
        os.replace(temporary_path, managed_path)
        fsync_directory(parent)
        return managed_path
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def atomic_write_json(
    path: os.PathLike[str] | str,
    data: Mapping[str, Any],
    *,
    repair_existing: bool = True,
) -> Path:
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return atomic_write_bytes(path, payload, repair_existing=repair_existing)


def secure_unlink(
    path: os.PathLike[str] | str,
    *,
    missing_ok: bool = True,
    expected_identity: tuple[int, int] | None = None,
    repair_mode: bool = True,
) -> bool:
    managed_path = resolve_path(path)
    try:
        fd, info = open_private_file(
            managed_path,
            os.O_RDONLY,
            repair_mode=repair_mode,
        )
    except FileNotFoundError:
        if missing_ok:
            return False
        raise
    try:
        if expected_identity is not None and _identity(info) != expected_identity:
            raise SecureStoreError(f"managed file identity changed before unlink: {managed_path}")
        latest = managed_path.lstat()
        _assert_same_object(info, latest, managed_path)
        os.unlink(managed_path)
        fsync_directory(managed_path.parent)
        return True
    finally:
        os.close(fd)


@contextlib.contextmanager
def file_lock(
    path: os.PathLike[str] | str,
    *,
    exclusive: bool = True,
    blocking: bool = True,
) -> Iterator[bool]:
    lock_path = resolve_path(path)
    fd, _info = open_private_file(
        lock_path,
        os.O_RDWR,
        create=True,
        repair_mode=True,
    )
    flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    if not blocking:
        flags |= fcntl.LOCK_NB
    try:
        try:
            fcntl.flock(fd, flags)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def update_json(
    path: os.PathLike[str] | str,
    mutator: Callable[[dict[str, Any]], Mapping[str, Any]],
    *,
    lock_path: os.PathLike[str] | str | None = None,
) -> dict[str, Any]:
    managed_path = resolve_path(path)
    sidecar = resolve_path(lock_path or f"{managed_path}.lock")
    with file_lock(sidecar, exclusive=True, blocking=True) as acquired:
        if not acquired:
            raise SecureStoreError(f"could not acquire managed state lock: {sidecar}")
        current = read_json(managed_path) or {}
        updated = dict(mutator(dict(current)))
        atomic_write_json(managed_path, updated)
        return updated
