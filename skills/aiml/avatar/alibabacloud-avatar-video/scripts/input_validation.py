"""Shared CLI input checks: path confinement, http(s) URLs, readable files."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

_MAX_TEXT_FILE_BYTES = 10 * 1024 * 1024


def resolve_under_cwd(user_path: str, *, field: str = "path") -> Path:
    """Resolve a user path under the current working directory; reject traversal."""
    base = Path.cwd().resolve(strict=False)
    candidate = (base / user_path).resolve(strict=False)
    try:
        candidate.relative_to(base)
    except ValueError as e:
        raise ValueError(
            f"{field} must resolve inside the current working directory ({base}): {user_path!r}"
        ) from e
    return candidate


def validate_http_https_url(url: str, *, field: str = "URL") -> str:
    u = url.strip()
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{field} must use http or https scheme: {url!r}")
    if not parsed.netloc:
        raise ValueError(f"{field} must include a host: {url!r}")
    return u


def validate_readable_file(path_str: str, *, field: str = "file") -> Path:
    p = Path(path_str).expanduser()
    if not p.is_file():
        raise ValueError(f"{field} must be an existing regular file: {path_str!r}")
    return p.resolve()


def read_text_file_limited(path_str: str, *, field: str = "--text-file") -> str:
    path = validate_readable_file(path_str, field=field)
    size = path.stat().st_size
    if size > _MAX_TEXT_FILE_BYTES:
        raise ValueError(
            f"{field} exceeds max size ({_MAX_TEXT_FILE_BYTES // (1024 * 1024)} MiB): {path_str!r}"
        )
    return path.read_text(encoding="utf-8").strip()


def mk_temp_path_for_ffmpeg(suffix: str, prefix: str) -> str:
    """Create an empty file with a random name and return its path (fd closed for ffmpeg)."""
    import tempfile

    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    try:
        os.close(fd)
    except OSError:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return path
