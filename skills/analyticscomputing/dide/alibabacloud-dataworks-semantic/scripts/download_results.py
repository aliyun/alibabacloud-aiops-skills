#!/usr/bin/env python3
"""Safely download artifacts returned by DownloadSemanticResults."""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
DEFAULT_MAX_BYTES = 100 * 1024 * 1024


def _first(item: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in item:
            return item[name]
    return None


def extract_results(payload: Any) -> list[dict[str, Any]]:
    """Extract the documented artifact list with common CLI casing variants."""
    if not isinstance(payload, dict):
        return []
    envelope = _first(payload, "Data", "data")
    candidate = _first(envelope, "Results", "results") if isinstance(envelope, dict) else None
    if candidate is None:
        candidate = _first(payload, "Results", "results")
    if not isinstance(candidate, list) or not candidate:
        return []
    if not all(isinstance(item, dict) and _first(item, "DownloadUrl", "downloadUrl") is not None for item in candidate):
        return []
    return candidate


def safe_file_name(value: Any) -> str:
    if not isinstance(value, str) or not value or CONTROL_CHARACTERS.search(value):
        raise ValueError("artifact has an empty or invalid file name")
    if value in {".", ".."} or Path(value).name != value or "/" in value or "\\" in value:
        raise ValueError("artifact file name contains a path component")
    return value


def file_name_from_url(url: str) -> str:
    """Derive a name only from the URL path when POP omits FileName."""
    parsed = urllib.parse.urlsplit(url)
    encoded_name = posixpath.basename(parsed.path)
    return safe_file_name(urllib.parse.unquote(encoded_name))


def is_alibaba_cloud_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    normalized = hostname.rstrip(".").lower()
    return normalized == "aliyuncs.com" or normalized.endswith(".aliyuncs.com")


def validate_output_directory(value: Path) -> Path:
    """Resolve a writable output directory while rejecting explicit traversal."""
    expanded = value.expanduser()
    if ".." in expanded.parts:
        raise ValueError("output directory must not contain '..' traversal")

    resolved = expanded.resolve(strict=False)
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("output directory is not a directory")

    existing_parent = resolved
    while not existing_parent.exists() and existing_parent != existing_parent.parent:
        existing_parent = existing_parent.parent

    if not existing_parent.is_dir():
        raise ValueError("output directory has no valid parent directory")
    if not (existing_parent.stat().st_mode & 0o222):
        raise ValueError("output directory is not writable")
    if not os.access(existing_parent, os.W_OK | os.X_OK):
        raise ValueError("output directory is not writable")

    return resolved


def prepare_output_directory(value: Path) -> Path:
    try:
        output_dir = validate_output_directory(value)
        output_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, RuntimeError, ValueError):
        raise SystemExit("output directory is unsafe or not writable") from None

    if not (output_dir.stat().st_mode & 0o222):
        raise SystemExit("output directory is unsafe or not writable")
    if not os.access(output_dir, os.W_OK | os.X_OK):
        raise SystemExit("output directory is unsafe or not writable")

    return output_dir


class HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme.lower() != "https" or not is_alibaba_cloud_host(parsed.hostname):
            raise urllib.error.URLError("refusing a redirect outside Alibaba Cloud HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_to_temp(url: str, destination: Path, timeout: int, max_bytes: int) -> tuple[Path, int]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https" or not is_alibaba_cloud_host(parsed.hostname):
        raise ValueError("artifact URL must be Alibaba Cloud HTTPS")
    opener = urllib.request.build_opener(
        HttpsOnlyRedirectHandler(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )
    request = urllib.request.Request(url, headers={"User-Agent": "DataWorksSemanticSkill/1.0"})
    temp_path: Path | None = None
    total = 0
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = urllib.parse.urlsplit(response.geturl())
            if final_url.scheme.lower() != "https" or not is_alibaba_cloud_host(final_url.hostname):
                raise ValueError("artifact response resolved outside Alibaba Cloud HTTPS")
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
            ) as output:
                temp_path = Path(output.name)
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"artifact exceeds the {max_bytes}-byte limit")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        if total == 0:
            raise ValueError("artifact is empty")
        completed_path = temp_path
        temp_path = None
        return completed_path, total
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download exact-run DataWorks semantic artifacts without printing presigned URLs."
    )
    parser.add_argument("--response", type=Path, help="JSON response file from DownloadSemanticResults")
    parser.add_argument("--job-name")
    parser.add_argument("--job-run-id")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate and prepare the output directory before requesting presigned URLs",
    )
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args()

    if args.timeout <= 0 or args.max_bytes <= 0:
        parser.error("timeout and max-bytes must be positive")

    output_dir = prepare_output_directory(args.output_dir)
    if args.validate_only:
        print(f"validated output directory: {output_dir}")
        return 0

    if args.response is None or not args.job_name or not args.job_run_id:
        parser.error("--response, --job-name, and --job-run-id are required unless --validate-only is used")

    try:
        response_mode = args.response.stat().st_mode
        if response_mode & 0o077:
            raise SystemExit("response file permissions must be owner-only")
        payload = json.loads(args.response.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise SystemExit("response file is unreadable or invalid JSON") from None
    results = extract_results(payload)
    if not results:
        raise SystemExit("no artifact results found in the response")

    planned: list[tuple[str, str, Path]] = []
    seen_names: set[str] = set()
    for item in results:
        job_name = _first(item, "JobName", "jobName")
        job_run_id = _first(item, "JobRunId", "jobRunId")
        if job_name != args.job_name or job_run_id != args.job_run_id:
            raise SystemExit("artifact identity does not match the requested job and run")
        url = _first(item, "DownloadUrl", "downloadUrl")
        if not isinstance(url, str) or not url:
            raise SystemExit("artifact has no public download URL")
        provided_name = _first(item, "FileName", "fileName")
        name = safe_file_name(provided_name) if provided_name is not None else file_name_from_url(url)
        if name in seen_names:
            raise SystemExit(f"duplicate artifact file name: {name}")
        destination = output_dir / name
        if destination.exists():
            raise SystemExit(f"destination already exists: {destination}")
        seen_names.add(name)
        planned.append((name, url, destination))

    staged: list[tuple[str, Path, Path, int]] = []
    try:
        for name, url, destination in planned:
            try:
                temp_path, size = download_to_temp(url, destination, args.timeout, args.max_bytes)
            except Exception as error:
                raise SystemExit(f"failed to download {name}: {type(error).__name__}") from None
            staged.append((name, temp_path, destination, size))

        committed: list[tuple[Path, Path]] = []
        try:
            for _, temp_path, destination, _ in staged:
                try:
                    os.link(temp_path, destination)
                except FileExistsError:
                    raise SystemExit(f"destination appeared during download: {destination}") from None
                committed.append((temp_path, destination))
        except BaseException:
            for temp_path, destination in committed:
                if destination.exists() and os.path.samefile(temp_path, destination):
                    destination.unlink()
            raise
        for _, temp_path, _, _ in staged:
            temp_path.unlink()

        downloaded = [(name, size) for name, _, _, size in staged]
    finally:
        for _, temp_path, _, _ in staged:
            temp_path.unlink(missing_ok=True)

    for name, size in downloaded:
        print(f"downloaded {name} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
