#!/usr/bin/env python3
"""Standard-library bridge from an external Skill to the packaged iac-code A2A runtime.

This file deliberately remains importable by CPython 3.8 through 3.14 and is
the only executable entry point shipped by the Skill.
"""

import argparse
import contextlib
import ctypes
import errno
import hashlib
import json
import math
import os
import pathlib
import platform
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile

SKILL_VERSION = "0.3.0"
RUNTIME_TAG = "v0.14.0"
IAC_CODE_VERSION = "0.14.0"
RUNTIME_PYTHON = "cp312"
SKILL_DISTRIBUTION = "agenthub"
SKILL_NAME = "alibabacloud-iac-code"
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/alibabacloud-iac-code/{session-id}"
MANIFEST_URL = "https://ros-public-tools.oss-cn-beijing.aliyuncs.com/github-releases/aliyun/iac-code/skill-runtime/releases/v0.14.0/runtime-manifest.json"
# Replaced in a temporary staging directory by skill-runtime/package_skill.py.
MANIFEST_SHA256 = "a00d36ad6cfbaed31594b5003f669e2a24148b2a4b4127e401c6eb7f38f0fc2e"
SCHEMA_VERSION = 1
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_SPOOL_BYTES = 8 * 1024 * 1024
MAX_POLL_BYTES = 4096
MAX_FOLLOW_BYTES = 16 * 1024
MAX_PROJECTION_BYTES = 4096
MAX_INPUT_PROJECTION_BYTES = 3000
MAX_POLL_EVENTS = 12
MAX_PUBLIC_TEXT = 800
MAX_FINAL_TEXT_BYTES = 10 * 1024
MAX_TURN_RESULT_BYTES = 2 * 1024 * 1024
MAX_PIPELINE_RESULT_BYTES = 2400
MAX_STEP_CONCLUSION_SUMMARY_BYTES = 1200
MAX_USER_UPDATE_TEXT = 280
MAX_FOLLOW_PROGRESS_LINES = 48
MAX_FOLLOW_PROGRESS_BYTES = 4096
MAX_AUTO_CLEANUP_TASKS_PER_FOLLOW = 4
MAX_CHANNEL_LENGTH = 128
MAX_SKILL_CONFIG_BYTES = 16 * 1024
MAX_PERMISSION_WAIT_SECONDS = 10 * 365 * 24 * 60 * 60
SKILL_CHANNEL_PREFIX = "skill/"
FOLLOW_HEARTBEAT_SECONDS = 12.0
DEFAULT_FOLLOW_SECONDS = 60.0
MAX_FOLLOW_SECONDS = 120.0
INSTALL_LOCK_TIMEOUT = 30.0
DOWNLOAD_ATTEMPTS = 3
RUNTIME_START_TIMEOUT = 20.0
RUNTIME_STOP_TIMEOUT = 5.0
RUNTIME_IDLE_TIMEOUT_SECONDS = 30 * 60
WORKER_IDENTITY_TIMEOUT = 10.0
TERMINAL_STATES = {
    "completed",
    "failed",
    "canceled",
    "rejected",
    "task_state_completed",
    "task_state_failed",
    "task_state_canceled",
    "task_state_rejected",
}
INPUT_STATES = {"input-required", "task_state_input_required"}
TURN_COMPLETED_STATE = "turn_completed"
PIPELINE_RESULT_FIELDS = {"selling": "deployment"}
PIPELINE_NORMAL_HANDOFFS = {"selling"}
STEP_BOUNDARY_EVENT_TYPES = {
    "step_started",
    "step_completed",
    "step_failed",
    "candidate_step_started",
    "candidate_step_completed",
    "candidate_step_failed",
}
CLEANUP_EVENT_TYPES = {"cleanup_started", "cleanup_progress", "cleanup_completed", "cleanup_failed"}
CLEANUP_PENDING_STATES = {"pending", "started", "in_progress", "running"}
CLEANUP_TERMINAL_STATES = {"completed", "failed", "none", "unavailable"}
PROGRESS_BOUNDARY_EVENT_TYPES = STEP_BOUNDARY_EVENT_TYPES | CLEANUP_EVENT_TYPES
CACHE_RESERVED_DIRECTORIES = {"jobs", "servers"}
SUPPORTED_LANGUAGES = ("en", "zh", "es", "fr", "de", "ja", "pt")
SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent
_ACTIVE_LANGUAGE = "en"
_SECRET_PATTERN = re.compile(
    r"(?i)(authorization\s*:\s*bearer\s+|access[_-]?key[_-]?(?:secret|id)?\s*[=:]\s*|"
    r"api[_-]?key\s*[=:]\s*|token\s*[=:]\s*|password\s*[=:]\s*)([^\s,;]+)"
)


def _skill_user_agent():
    if SKILL_DISTRIBUTION != "agenthub":
        return USER_AGENT_TEMPLATE
    value = os.environ.get("SKILL_SESSION_ID", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{32}", value) is None:
        value = uuid.uuid4().hex
        os.environ["SKILL_SESSION_ID"] = value
    return USER_AGENT_TEMPLATE.replace("{session-id}", value)


_SKILL_USER_AGENT = _skill_user_agent()


class BridgeError(Exception):
    def __init__(self, code, message, retryable=False, details=None):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
        self.retryable = bool(retryable)
        self.details = details or {}

    def payload(self):
        value = {
            "ok": False,
            "preferredLanguage": _ACTIVE_LANGUAGE,
            "error": {"code": self.code, "message": self.message, "retryable": self.retryable},
        }
        if self.details:
            value["error"]["details"] = self.details
        return value


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_stdout(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _progress_bytes(stage, message):
    return _json_bytes({"type": "progress", "stage": stage, "message": message}) + b"\n"


def _progress(stage, message):
    message = _localized_progress_text(message)
    sys.stderr.write(_progress_bytes(stage, message).decode("utf-8"))
    sys.stderr.flush()


def _set_output_language(language):
    global _ACTIVE_LANGUAGE
    _ACTIVE_LANGUAGE = language if language in SUPPORTED_LANGUAGES else "en"


def _localized_progress_text(message):
    if _ACTIVE_LANGUAGE != "zh":
        return message
    translations = {
        "Downloading the pinned runtime manifest": "正在下载固定版本的 Runtime 清单",
        "Downloading the CPython 3.12 iac-code runtime": "正在下载自带 CPython 3.12 的 iac-code Runtime",
        "Verifying and extracting the runtime": "正在校验并解压 Runtime",
        "Starting or reusing the local A2A runtime": "正在启动或复用本地 A2A Runtime",
    }
    return translations.get(message, message)


def _config_root():
    raw = os.environ.get("IAC_CODE_CONFIG_DIR") or os.path.join("~", ".iac-code")
    return pathlib.Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def _bridge_root():
    return _config_root() / "skill-runtime"


def _secure_directory(path):
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(str(path), 0o700)


def _atomic_json(path, value, mode=0o600):
    _secure_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            os.chmod(temporary, mode)
        os.replace(temporary, str(path))
    finally:
        with contextlib.suppress(OSError):
            os.unlink(temporary)


def _atomic_text(path, value, mode=0o600):
    _secure_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            os.chmod(temporary, mode)
        os.replace(temporary, str(path))
    finally:
        with contextlib.suppress(OSError):
            os.unlink(temporary)


def _load_json(path, code="job_not_found"):
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError) as exc:
        raise BridgeError(code, "Local bridge state is unavailable or invalid.") from exc
    if not isinstance(value, dict):
        raise BridgeError(code, "Local bridge state is unavailable or invalid.")
    return value


def _sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def _normalized_system(value=None):
    value = (value or platform.system()).lower()
    mapping = {"darwin": "darwin", "linux": "linux", "windows": "windows"}
    if value not in mapping:
        raise BridgeError("unsupported_target", "No iac-code runtime is published for this operating system.")
    return mapping[value]


def _normalized_arch(value=None):
    value = (value or platform.machine()).lower().replace("-", "_")
    mapping = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    if value not in mapping:
        raise BridgeError("unsupported_target", "No iac-code runtime is published for this CPU architecture.")
    return mapping[value]


def _number_tuple(value):
    parts = re.findall(r"\d+", value or "")
    if not parts:
        raise BridgeError("incompatible_host", "The host compatibility version could not be determined.")
    return tuple(int(item) for item in parts)


def _version_at_least(actual, minimum):
    left = list(_number_tuple(actual))
    right = list(_number_tuple(minimum))
    width = max(len(left), len(right))
    left.extend([0] * (width - len(left)))
    right.extend([0] * (width - len(right)))
    return tuple(left) >= tuple(right)


def detect_host(system=None, machine=None, libc_name=None, libc_version=None, os_version=None):
    system_name = _normalized_system(system)
    arch = _normalized_arch(machine)
    host = {"os": system_name, "arch": arch}
    if system_name == "linux":
        detected_name, detected_version = platform.libc_ver()
        name = (libc_name if libc_name is not None else detected_name).lower()
        version = libc_version if libc_version is not None else detected_version
        if name not in {"glibc", "gnu libc", "libc"} or not version:
            raise BridgeError("incompatible_host", "The GNU libc version could not be determined.")
        host.update({"nativeAbi": "gnu", "libcName": "glibc", "libcVersion": version})
    elif system_name == "darwin":
        version = os_version if os_version is not None else platform.mac_ver()[0]
        if not version:
            raise BridgeError("incompatible_host", "The macOS version could not be determined.")
        host.update({"nativeAbi": "macos", "osVersion": version})
    else:
        version = os_version if os_version is not None else platform.version()
        if not version:
            raise BridgeError("incompatible_host", "The Windows version could not be determined.")
        host.update({"nativeAbi": "msvc", "osVersion": version})
    return host


def validate_manifest(value, expected_runtime_tag=RUNTIME_TAG):
    if not isinstance(value, dict) or value.get("schemaVersion") != SCHEMA_VERSION:
        raise BridgeError("manifest_verification_failed", "The runtime manifest schema is invalid.")
    expected_kind = (
        "iac-code-skill-runtime-candidate"
        if expected_runtime_tag.startswith("candidate-")
        else "iac-code-skill-runtime-release"
    )
    identity_field = "candidateId" if expected_kind.endswith("candidate") else "runtimeTag"
    if (
        value.get("kind") != expected_kind
        or value.get(identity_field) != expected_runtime_tag
        or value.get("iacCodeVersion") != IAC_CODE_VERSION
        or value.get("runtimePython") != RUNTIME_PYTHON
        or not re.fullmatch(r"[0-9a-f]{40}", str(value.get("sourceCommit")))
        or not re.fullmatch(r"[0-9a-f]{40}", str(value.get("publisherCommit")))
        or not isinstance(value.get("publishedAt"), str)
    ):
        raise BridgeError("manifest_verification_failed", "The runtime manifest release identity is invalid.")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise BridgeError("manifest_verification_failed", "The runtime manifest has no artifacts.")
    targets = set()
    required = {
        "target",
        "os",
        "arch",
        "nativeAbi",
        "runtimePython",
        "compatibility",
        "url",
        "sha256",
        "size",
        "archive",
        "executable",
    }
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not required.issubset(artifact):
            raise BridgeError("manifest_verification_failed", "A runtime artifact entry is incomplete.")
        target = artifact.get("target")
        if not isinstance(target, str) or not target or target in targets:
            raise BridgeError("manifest_verification_failed", "Runtime artifact targets must be unique.")
        targets.add(target)
        if artifact.get("runtimePython") != RUNTIME_PYTHON:
            raise BridgeError("manifest_verification_failed", "The runtime artifact does not contain CPython 3.12.")
        expected_target = "{}-{}-{}-{}".format(
            artifact.get("os"),
            artifact.get("arch"),
            artifact.get("nativeAbi"),
            RUNTIME_PYTHON,
        )
        if target != expected_target:
            raise BridgeError("manifest_verification_failed", "The runtime artifact target identity is invalid.")
        expected_native_abi = {"darwin": "macos", "linux": "gnu", "windows": "msvc"}.get(artifact.get("os"))
        if expected_native_abi is None or artifact.get("nativeAbi") != expected_native_abi:
            raise BridgeError("manifest_verification_failed", "The runtime artifact native ABI is invalid.")
        if not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256"))):
            raise BridgeError("manifest_verification_failed", "The runtime artifact digest is invalid.")
        if not isinstance(artifact.get("size"), int) or not 0 < artifact["size"] <= MAX_ARCHIVE_BYTES:
            raise BridgeError("manifest_verification_failed", "The runtime artifact size is invalid.")
        if artifact.get("archive") not in {"tar.gz", "zip"}:
            raise BridgeError("manifest_verification_failed", "The runtime archive format is invalid.")
        expected_archive = "zip" if artifact.get("os") == "windows" else "tar.gz"
        if artifact.get("archive") != expected_archive:
            raise BridgeError(
                "manifest_verification_failed", "The runtime archive does not match its operating system."
            )
        executable = pathlib.PurePosixPath(str(artifact.get("executable")))
        if executable.is_absolute() or ".." in executable.parts:
            raise BridgeError("manifest_verification_failed", "The runtime executable path is invalid.")
    return value


def select_artifact(manifest, host):
    matches = [
        item
        for item in manifest["artifacts"]
        if item["os"] == host["os"] and item["arch"] == host["arch"] and item["nativeAbi"] == host["nativeAbi"]
    ]
    if len(matches) != 1:
        raise BridgeError(
            "unsupported_target" if not matches else "manifest_verification_failed",
            "The runtime manifest does not contain exactly one artifact for this host.",
        )
    artifact = matches[0]
    compatibility = artifact["compatibility"]
    if not isinstance(compatibility, dict):
        raise BridgeError("manifest_verification_failed", "The runtime compatibility declaration is invalid.")
    if host["os"] == "linux":
        libc = compatibility.get("libc")
        if not isinstance(libc, dict) or libc.get("name") != "glibc" or not isinstance(libc.get("minVersion"), str):
            raise BridgeError("manifest_verification_failed", "The GNU runtime compatibility declaration is invalid.")
        if not _version_at_least(host["libcVersion"], libc["minVersion"]):
            raise BridgeError("incompatible_host", "The host glibc version is below the runtime baseline.")
    else:
        minimum = compatibility.get("minOsVersion")
        if not isinstance(minimum, str) or not minimum:
            raise BridgeError("manifest_verification_failed", "The minimum OS version is missing.")
        if not _version_at_least(host["osVersion"], minimum):
            raise BridgeError("incompatible_host", "The host OS version is below the runtime baseline.")
    return artifact


class InstallLock(object):
    def __init__(self, path, timeout=INSTALL_LOCK_TIMEOUT):
        self.path = path
        self.timeout = timeout
        self.handle = None

    def __enter__(self):
        _secure_directory(self.path.parent)
        self.handle = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self.handle.write(b"0")
            self.handle.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    self.handle.seek(0)
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError) as exc:
                if getattr(exc, "errno", None) not in {None, errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    self.handle.close()
                    self.handle = None
                    raise BridgeError(
                        "runtime_install_locked", "Another process is still installing this runtime.", True
                    )
                time.sleep(0.1)

    def __exit__(self, _type, _value, _traceback):
        if self.handle is None:
            return
        with contextlib.suppress(OSError):
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def _download(url, destination, maximum, expected_size=None):
    request = urllib.request.Request(url, headers={"User-Agent": _SKILL_USER_AGENT})
    downloaded = 0
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > maximum:
                    raise BridgeError("artifact_verification_failed", "The downloaded runtime exceeded its size limit.")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    except BridgeError:
        raise
    except (OSError, urllib.error.URLError) as exc:
        raise BridgeError("a2a_transport_failed", "The OSS download failed.", True) from exc
    if expected_size is not None and downloaded != expected_size:
        raise BridgeError("artifact_verification_failed", "The downloaded runtime size does not match the manifest.")


def _safe_archive_name(raw, seen):
    raw = raw.replace("\\", "/")
    path = pathlib.PurePosixPath(raw)
    if not raw or raw.startswith("/") or path.is_absolute() or ".." in path.parts:
        raise BridgeError("artifact_verification_failed", "The runtime archive contains an unsafe path.")
    normalized = "/".join(part for part in path.parts if part not in {"", "."})
    identity = normalized.casefold()
    if identity in seen:
        raise BridgeError("artifact_verification_failed", "The runtime archive contains duplicate paths.")
    seen.add(identity)
    return normalized


def _safe_tar_link(member_name, link_name, hard_link=False):
    member = pathlib.PurePosixPath(member_name.replace("\\", "/"))
    link = pathlib.PurePosixPath(link_name.replace("\\", "/"))
    if not link_name or link_name.startswith("/") or link.is_absolute():
        raise BridgeError("artifact_verification_failed", "The runtime archive contains an unsafe link.")
    combined = link if hard_link else member.parent / link
    depth = 0
    for part in combined.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            depth -= 1
            if depth < 0:
                raise BridgeError("artifact_verification_failed", "The runtime archive contains an unsafe link.")
        else:
            depth += 1


def safe_extract(archive_path, archive_type, destination):
    seen = set()
    if archive_type == "zip":
        with zipfile.ZipFile(str(archive_path)) as archive:
            for item in archive.infolist():
                _safe_archive_name(item.filename, seen)
                unix_mode = (item.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(unix_mode):
                    raise BridgeError(
                        "artifact_verification_failed", "Runtime archives may not contain symbolic links."
                    )
            archive.extractall(str(destination))
        return
    with tarfile.open(str(archive_path), mode="r:gz") as archive:
        for item in archive.getmembers():
            _safe_archive_name(item.name, seen)
            if item.issym():
                _safe_tar_link(item.name, item.linkname)
            elif item.islnk():
                _safe_tar_link(item.name, item.linkname, hard_link=True)
            elif item.isdev() or item.isfifo():
                raise BridgeError("artifact_verification_failed", "Runtime archives may not contain devices or FIFOs.")
        archive.extractall(str(destination))


def _fetch_manifest():
    temporary = pathlib.Path(tempfile.mkstemp(prefix="iac-code-manifest-", suffix=".json")[1])
    try:
        _progress("manifest", "Downloading the pinned runtime manifest")
        _download(MANIFEST_URL, temporary, MAX_MANIFEST_BYTES)
        digest, _size = _sha256_file(temporary)
        if digest != MANIFEST_SHA256:
            raise BridgeError("manifest_verification_failed", "The runtime manifest digest does not match the Skill.")
        try:
            value = json.loads(temporary.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BridgeError("manifest_verification_failed", "The runtime manifest is not valid JSON.") from exc
        return validate_manifest(value)
    finally:
        with contextlib.suppress(OSError):
            temporary.unlink()


def _runtime_paths(artifact):
    root = _bridge_root() / RUNTIME_TAG / artifact["target"]
    install = root / "runtime"
    executable = install.joinpath(*pathlib.PurePosixPath(artifact["executable"]).parts)
    return root, install, executable


def _installed_runtime(artifact):
    root, install, executable = _runtime_paths(artifact)
    marker = install / ".iac-code-runtime.json"
    if not executable.is_file() or not marker.is_file():
        return None
    try:
        value = _load_json(marker, "artifact_verification_failed")
    except BridgeError:
        return None
    expected = {
        "runtimeTag": RUNTIME_TAG,
        "target": artifact["target"],
        "artifactSha256": artifact["sha256"],
        "runtimePython": RUNTIME_PYTHON,
    }
    if any(value.get(key) != item for key, item in expected.items()):
        return None
    return executable


def ensure_runtime():
    host = detect_host()
    manifest = _fetch_manifest()
    artifact = select_artifact(manifest, host)
    cached = _installed_runtime(artifact)
    if cached is not None:
        return artifact, cached, True
    root, install, executable = _runtime_paths(artifact)
    _secure_directory(root)
    with InstallLock(root / ".install.lock"):
        cached = _installed_runtime(artifact)
        if cached is not None:
            return artifact, cached, True
        for stale in root.glob(".install-*"):
            if stale.is_dir():
                shutil.rmtree(str(stale), ignore_errors=True)
            else:
                with contextlib.suppress(OSError):
                    stale.unlink()
        last_error = None
        for attempt in range(DOWNLOAD_ATTEMPTS):
            archive_path = root / (".install-{}.part".format(uuid.uuid4().hex))
            extract_path = root / (".install-{}".format(uuid.uuid4().hex))
            extract_path.mkdir()
            try:
                _progress("download", "Downloading the CPython 3.12 iac-code runtime")
                _download(artifact["url"], archive_path, MAX_ARCHIVE_BYTES, artifact["size"])
                digest, size = _sha256_file(archive_path)
                if digest != artifact["sha256"] or size != artifact["size"]:
                    raise BridgeError("artifact_verification_failed", "The runtime artifact digest does not match.")
                _progress("extract", "Verifying and extracting the runtime")
                safe_extract(archive_path, artifact["archive"], extract_path)
                staged_executable = extract_path.joinpath(*pathlib.PurePosixPath(artifact["executable"]).parts)
                version_file = extract_path / "iac-code-runtime" / "runtime-version.json"
                if not staged_executable.is_file() or not version_file.is_file():
                    raise BridgeError(
                        "artifact_verification_failed", "The runtime entry point or version file is missing."
                    )
                version = _load_json(version_file, "artifact_verification_failed")
                identity_field = "candidateId" if RUNTIME_TAG.startswith("candidate-") else "runtimeTag"
                if (
                    version.get("iacCodeVersion") != IAC_CODE_VERSION
                    or version.get("runtimePython") != RUNTIME_PYTHON
                    or version.get(identity_field) != RUNTIME_TAG
                ):
                    raise BridgeError("artifact_verification_failed", "The extracted runtime identity is invalid.")
                if os.name != "nt":
                    os.chmod(str(staged_executable), os.stat(str(staged_executable)).st_mode | stat.S_IXUSR)
                check = subprocess.run(
                    [str(staged_executable), "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=20,
                    check=False,
                )
                if check.returncode != 0 or IAC_CODE_VERSION.encode("utf-8") not in check.stdout + check.stderr:
                    raise BridgeError("artifact_verification_failed", "The extracted runtime self-check failed.")
                _atomic_json(
                    extract_path / ".iac-code-runtime.json",
                    {
                        "runtimeTag": RUNTIME_TAG,
                        "target": artifact["target"],
                        "artifactSha256": artifact["sha256"],
                        "runtimePython": RUNTIME_PYTHON,
                        "installedAt": int(time.time()),
                    },
                )
                if install.exists():
                    shutil.rmtree(str(install))
                os.replace(str(extract_path), str(install))
                return artifact, executable, False
            except BridgeError as exc:
                last_error = exc
                if exc.code != "a2a_transport_failed" and exc.code != "artifact_verification_failed":
                    raise
                if attempt + 1 < DOWNLOAD_ATTEMPTS:
                    time.sleep(0.2 * (attempt + 1))
            finally:
                with contextlib.suppress(OSError):
                    archive_path.unlink()
                if extract_path.exists():
                    shutil.rmtree(str(extract_path), ignore_errors=True)
        if last_error is not None:
            raise last_error
        raise BridgeError("artifact_verification_failed", "The runtime could not be installed.")


def _runtime_directory_size(path):
    total = 0
    for root, directories, files in os.walk(str(path), followlinks=False):
        for name in directories + files:
            candidate = pathlib.Path(root) / name
            with contextlib.suppress(OSError):
                total += candidate.lstat().st_size
    return total


def _active_runtime_identities():
    active = set()
    servers = _bridge_root() / "servers"
    if not servers.is_dir():
        return active
    for record_path in servers.glob("*/runtime.json"):
        try:
            record = _load_json(record_path, "runtime_identity_mismatch")
        except BridgeError:
            continue
        runtime_tag = record.get("runtimeTag")
        target = record.get("target")
        if isinstance(runtime_tag, str) and isinstance(target, str) and _pid_alive(record.get("pid")):
            active.add((runtime_tag, target))
    return active


def _runtime_cache_entries():
    root = _bridge_root()
    if not root.is_dir():
        return []
    active = _active_runtime_identities()
    entries = []
    for tag_path in sorted(root.iterdir(), key=lambda item: item.name):
        if (
            tag_path.name in CACHE_RESERVED_DIRECTORIES
            or tag_path.name.startswith(".")
            or tag_path.is_symlink()
            or not tag_path.is_dir()
        ):
            continue
        for target_path in sorted(tag_path.iterdir(), key=lambda item: item.name):
            if target_path.is_symlink() or not target_path.is_dir():
                continue
            runtime_path = target_path / "runtime"
            marker_path = runtime_path / ".iac-code-runtime.json"
            if runtime_path.is_symlink() or not runtime_path.is_dir() or not marker_path.is_file():
                continue
            try:
                marker = _load_json(marker_path, "artifact_verification_failed")
            except BridgeError:
                continue
            runtime_tag = marker.get("runtimeTag")
            target = marker.get("target")
            if runtime_tag != tag_path.name or target != target_path.name:
                continue
            installed_at = marker.get("installedAt")
            entries.append(
                {
                    "runtimeTag": runtime_tag,
                    "target": target,
                    "runtimePython": (
                        marker.get("runtimePython") if isinstance(marker.get("runtimePython"), str) else None
                    ),
                    "installedAt": installed_at if isinstance(installed_at, int) and installed_at >= 0 else None,
                    "sizeBytes": _runtime_directory_size(runtime_path),
                    "current": runtime_tag == RUNTIME_TAG,
                    "candidate": runtime_tag.startswith("candidate-"),
                    "active": (runtime_tag, target) in active,
                    "_targetPath": target_path,
                    "_runtimePath": runtime_path,
                }
            )
    return entries


def _public_runtime_cache_entry(entry):
    return {key: value for key, value in entry.items() if not key.startswith("_")}


def list_runtime_cache(_args=None):
    entries = _runtime_cache_entries()
    return {
        "ok": True,
        "currentRuntimeTag": RUNTIME_TAG,
        "runtimeCount": len(entries),
        "totalSizeBytes": sum(entry["sizeBytes"] for entry in entries),
        "runtimes": [_public_runtime_cache_entry(entry) for entry in entries],
    }


def clean_runtime_cache(args):
    if not args.confirm:
        raise BridgeError(
            "cache_cleanup_confirmation_required",
            "Runtime cache cleanup requires explicit confirmation with --confirm.",
        )
    entries = _runtime_cache_entries()
    if args.runtime_tag:
        selected = [entry for entry in entries if entry["runtimeTag"] == args.runtime_tag]
        if not selected:
            raise BridgeError("runtime_cache_not_found", "The requested Runtime tag is not installed.")
    else:
        selected = [entry for entry in entries if entry["candidate"]]

    deleted = []
    skipped = []
    for entry in selected:
        public = _public_runtime_cache_entry(entry)
        if entry["current"]:
            skipped.append({**public, "reason": "current_runtime"})
            continue
        target_path = entry["_targetPath"]
        runtime_path = entry["_runtimePath"]
        with InstallLock(target_path / ".install.lock"):
            active = (entry["runtimeTag"], entry["target"]) in _active_runtime_identities()
            if active:
                public["active"] = True
                skipped.append({**public, "reason": "active_runtime"})
                continue
            if not runtime_path.is_dir() or runtime_path.is_symlink():
                skipped.append({**public, "reason": "runtime_not_found"})
                continue
            shutil.rmtree(str(runtime_path))
        deleted.append(public)

    return {
        "ok": True,
        "deletedCount": len(deleted),
        "freedBytes": sum(entry["sizeBytes"] for entry in deleted),
        "deleted": deleted,
        "skipped": skipped,
    }


def _runtime_key(mode, pipeline_name, target, permission_wait_policy=None):
    identity_parts = [RUNTIME_TAG, target, mode, pipeline_name or ""]
    if permission_wait_policy is not None:
        identity_parts.append(json.dumps(permission_wait_policy, sort_keys=True, separators=(",", ":")))
    identity = "\0".join(identity_parts)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _runtime_record_path(mode, pipeline_name, target, permission_wait_policy=None):
    return (
        _bridge_root() / "servers" / _runtime_key(mode, pipeline_name, target, permission_wait_policy) / "runtime.json"
    )


def _pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _http_json(url, token=None, method="GET", payload=None, timeout=10):
    data = _json_bytes(payload) if payload is not None else None
    headers = {"Accept": "application/json", "A2A-Version": "1.0", "User-Agent": _SKILL_USER_AGENT}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise BridgeError("a2a_transport_failed", "The local A2A runtime did not respond.", True) from exc
    if len(raw) > 2 * 1024 * 1024:
        raise BridgeError("a2a_transport_failed", "The local A2A response exceeded its limit.")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BridgeError("a2a_transport_failed", "The local A2A response was invalid.") from exc
    if not isinstance(value, dict):
        raise BridgeError("a2a_transport_failed", "The local A2A response was invalid.")
    return value


def _safe_readiness_section(value, fields):
    if not isinstance(value, dict) or not isinstance(value.get("ready"), bool):
        raise BridgeError("a2a_transport_failed", "The local A2A readiness response was invalid.")
    section = {"ready": value["ready"]}
    for field in fields:
        item = value.get(field)
        if item is None:
            section[field] = None
        elif isinstance(item, str):
            section[field] = _sanitize_text(item, 120)
    missing = value.get("missing")
    if not isinstance(missing, list) or any(not isinstance(item, str) for item in missing):
        raise BridgeError("a2a_transport_failed", "The local A2A readiness response was invalid.")
    section["missing"] = [_sanitize_text(item, 80) for item in missing[:12] if item]
    return section


def _runtime_configuration_readiness(record, require_cloud):
    response = _http_json(
        "http://127.0.0.1:{}/iac-code/readiness".format(record["port"]),
        record.get("token"),
        timeout=5,
    )
    if response.get("schemaVersion") != 1:
        raise BridgeError("a2a_transport_failed", "The local A2A readiness response was invalid.")
    readiness = {
        "schemaVersion": 1,
        "llm": _safe_readiness_section(
            response.get("llm"),
            ("source", "provider", "providerDisplay", "model"),
        ),
        "cloud": _safe_readiness_section(
            response.get("cloud"),
            ("provider", "mode", "regionId"),
        ),
    }
    readiness["llm"]["requiredForStart"] = True
    readiness["cloud"]["requiredForStart"] = bool(require_cloud)
    if not readiness["llm"]["ready"]:
        message = (
            "iac-code \u7684 LLM \u914d\u7f6e\u4e0d\u5b8c\u6574\uff0c"
            "\u8bf7\u5148\u5728 iac-code \u4e2d\u914d\u7f6e\u6a21\u578b\u63d0\u4f9b\u5546\u548c API Key\u3002"
            if _ACTIVE_LANGUAGE == "zh"
            else "iac-code's LLM configuration is incomplete. Configure its model provider and API key first."
        )
        raise BridgeError(
            "llm_not_configured",
            message,
            False,
            {"configurationReadiness": readiness},
        )
    if require_cloud and not readiness["cloud"]["ready"]:
        message = (
            "\u8be5 Pipeline \u9700\u8981\u963f\u91cc\u4e91\u51ed\u8bc1\uff0c"
            "\u8bf7\u5148\u5728 iac-code \u4e2d\u5b8c\u6210\u4e91\u51ed\u8bc1\u914d\u7f6e\u3002"
            if _ACTIVE_LANGUAGE == "zh"
            else "This Pipeline requires Alibaba Cloud credentials. Configure them in iac-code first."
        )
        raise BridgeError(
            "cloud_credentials_not_configured",
            message,
            False,
            {"configurationReadiness": readiness},
        )
    if not readiness["cloud"]["ready"]:
        _progress(
            "preflight",
            (
                "尚未配置完整的阿里云凭证；当前仅适合不调用云 API 的模板任务"
                if _ACTIVE_LANGUAGE == "zh"
                else "Alibaba Cloud credentials are incomplete; only tasks that do not call cloud APIs can proceed"
            ),
        )
    return readiness


def _runtime_matches(record, mode, pipeline_name, target, permission_wait_policy=None):
    expected = {
        "runtimeTag": RUNTIME_TAG,
        "iacCodeVersion": IAC_CODE_VERSION,
        "target": target,
        "mode": mode,
        "pipelineName": pipeline_name or "",
        "permissionWaitPolicy": permission_wait_policy,
    }
    if any(record.get(key) != value for key, value in expected.items()) or not _pid_alive(record.get("pid")):
        return False
    base = "http://127.0.0.1:{}/".format(record.get("port"))
    try:
        health = _http_json(base + "health", record.get("token"), timeout=2)
        card = _http_json(base + ".well-known/agent-card.json", record.get("token"), timeout=2)
    except BridgeError:
        return False
    if health.get("status") != "healthy" or health.get("version") != IAC_CODE_VERSION:
        return False
    if health.get("mode") != mode:
        return False
    return card.get("version") == IAC_CODE_VERSION


def _runtime_record_for_job(job):
    record_path = job.get("runtimeRecord")
    target = job.get("target")
    mode = job.get("mode")
    pipeline_name = job.get("pipelineName")
    workspace = job.get("workspace")
    generation = job.get("runtimeGeneration")
    if not all(isinstance(value, str) and value for value in (record_path, target, mode, workspace, generation)):
        raise BridgeError("runtime_identity_mismatch", "The Skill job runtime identity is incomplete.")
    if mode not in {"normal", "pipeline"} or not isinstance(pipeline_name, str):
        raise BridgeError("runtime_identity_mismatch", "The Skill job Pipeline identity is invalid.")
    if (mode == "pipeline") != bool(pipeline_name):
        raise BridgeError("runtime_identity_mismatch", "The Skill job mode and Pipeline identity do not match.")
    record = _load_json(pathlib.Path(record_path), "runtime_identity_mismatch")
    if record.get("generation") != job.get("runtimeGeneration"):
        raise BridgeError("runtime_identity_mismatch", "The Skill job runtime generation is no longer active.")
    if not _runtime_matches(record, mode, pipeline_name, target, job.get("permissionWaitPolicy")):
        raise BridgeError("runtime_identity_mismatch", "The Skill job runtime identity no longer matches.")
    return record


def _free_port():
    family = socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _stop_spawned_process(process):
    if process.poll() is not None:
        return
    with contextlib.suppress(OSError):
        process.terminate()
    try:
        process.wait(timeout=RUNTIME_STOP_TIMEOUT)
        return
    except subprocess.TimeoutExpired:
        pass
    except OSError:
        return
    with contextlib.suppress(OSError):
        process.kill()
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=RUNTIME_STOP_TIMEOUT)


def _remove_runtime_record(record_path, generation):
    if not record_path.is_file():
        return
    with contextlib.suppress(BridgeError, OSError):
        current = _load_json(record_path, "runtime_identity_mismatch")
        if current.get("generation") == generation:
            record_path.unlink()


def ensure_server(executable, artifact, mode, pipeline_name, permission_wait_policy=None):
    runtimes = _bridge_root() / "servers"
    _secure_directory(runtimes)
    key = _runtime_key(mode, pipeline_name, artifact["target"], permission_wait_policy)
    root = runtimes / key
    _secure_directory(root)
    record_path = root / "runtime.json"
    with InstallLock(root / ".runtime.lock", timeout=10):
        if record_path.is_file():
            with contextlib.suppress(BridgeError):
                record = _load_json(record_path, "runtime_identity_mismatch")
                if _runtime_matches(record, mode, pipeline_name, artifact["target"], permission_wait_policy):
                    return record
        token = secrets.token_urlsafe(32)
        port = _free_port()
        generation = uuid.uuid4().hex
        persistence = root / "a2a"
        artifacts = root / "artifacts"
        _secure_directory(persistence)
        _secure_directory(artifacts)
        config = {
            "token": token,
            "persistence_dir": str(persistence),
            "artifact_dir": str(artifacts),
            "auto_approve_permissions": False,
            "thinking_exposure": ["tool-trace"],
            "log_to_stdout": False,
            "idle_shutdown_seconds": RUNTIME_IDLE_TIMEOUT_SECONDS,
        }
        if permission_wait_policy is not None:
            config["permission_wait"] = {
                "resident_timeout_seconds": permission_wait_policy["residentTimeoutSeconds"],
                "sub_pipeline_timeout_seconds": permission_wait_policy["subPipelineTimeoutSeconds"],
                "timeout_grace_seconds": permission_wait_policy["timeoutGraceSeconds"],
            }
        config_path = root / "a2a.json"
        _atomic_json(config_path, config)
        log_path = root / "runtime.log"
        environment = dict(os.environ)
        environment["IAC_CODE_MODE"] = mode
        environment.pop("IACCODE_A2A_ALLOWED_CWDS", None)
        environment["IAC_CODE_A2A_TRUST_REQUEST_CWD"] = "1"
        environment["IAC_CODE_SKILL_RUNTIME_GENERATION"] = generation
        if pipeline_name:
            environment["IAC_CODE_PIPELINE_NAME"] = pipeline_name
        else:
            environment.pop("IAC_CODE_PIPELINE_NAME", None)
        command = [
            str(executable),
            "a2a",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--config",
            str(config_path),
        ]
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        process = None
        ready = False
        try:
            with log_path.open("ab", buffering=0) as log:
                process = subprocess.Popen(
                    command,
                    cwd=str(root),
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=os.name != "nt",
                    creationflags=creationflags,
                )
            record = {
                "schemaVersion": 2,
                "runtimeTag": RUNTIME_TAG,
                "skillVersion": SKILL_VERSION,
                "iacCodeVersion": IAC_CODE_VERSION,
                "target": artifact["target"],
                "generation": generation,
                "mode": mode,
                "pipelineName": pipeline_name or "",
                "permissionWaitPolicy": permission_wait_policy,
                "pid": process.pid,
                "port": port,
                "token": token,
                "logPath": str(log_path),
                "startedAt": int(time.time()),
            }
            _atomic_json(record_path, record)
            deadline = time.monotonic() + RUNTIME_START_TIMEOUT
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                if _runtime_matches(record, mode, pipeline_name, artifact["target"], permission_wait_policy):
                    ready = True
                    return record
                time.sleep(0.15)
            raise BridgeError(
                "runtime_start_failed",
                "The local iac-code A2A runtime failed its health check.",
                True,
                {"logPath": str(log_path)},
            )
        finally:
            if process is not None and not ready:
                _stop_spawned_process(process)
                _remove_runtime_record(record_path, generation)


def _sanitize_text(value, maximum=MAX_PUBLIC_TEXT):
    if not isinstance(value, str):
        return ""
    value = _SECRET_PATTERN.sub(lambda match: match.group(1) + "[REDACTED]", value)
    value = " ".join(value.split())
    return value[:maximum]


def _truncate_utf8(value, maximum):
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum:
        return value
    return encoded[:maximum].decode("utf-8", "ignore")


def _sanitize_stream_text(value, maximum=MAX_TURN_RESULT_BYTES):
    if not isinstance(value, str):
        return ""
    value = _SECRET_PATTERN.sub(lambda match: match.group(1) + "[REDACTED]", value)
    value = "".join(character for character in value if character in "\n\r\t" or ord(character) >= 32)
    return _truncate_utf8(value, maximum)


def _event_payload(result):
    if not isinstance(result, dict):
        return result
    for key in ("statusUpdate", "artifactUpdate"):
        value = result.get(key)
        if isinstance(value, dict):
            return value
    return result


def _state_from_result(result):
    def normalize(value):
        normalized = value.lower().replace("-", "_")
        if normalized.startswith("task_state_"):
            normalized = normalized[len("task_state_") :]
        return normalized.replace("_", "-")

    if not isinstance(result, dict):
        return ""
    result = _event_payload(result)
    status = result.get("status")
    if isinstance(status, dict) and isinstance(status.get("state"), str):
        return normalize(status["state"])
    task = result.get("task")
    if isinstance(task, dict):
        status = task.get("status")
        if isinstance(status, dict) and isinstance(status.get("state"), str):
            return normalize(status["state"])
    return ""


def _message_text_from_result(result):
    candidates = []
    if isinstance(result, dict):
        result = _event_payload(result)
        status = result.get("status")
        if isinstance(status, dict):
            candidates.append(status.get("message"))
        candidates.append(result.get("message"))
        task = result.get("task")
        if isinstance(task, dict) and isinstance(task.get("status"), dict):
            candidates.append(task["status"].get("message"))
    pieces = []
    for message in candidates:
        if not isinstance(message, dict) or not isinstance(message.get("parts"), list):
            continue
        for part in message["parts"]:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                pieces.append(part["text"])
        if pieces:
            break
    return "".join(pieces)


def _message_from_result(result):
    return _sanitize_text(_message_text_from_result(result))


def _turn_text_from_result(result):
    return _sanitize_stream_text(_message_text_from_result(result))


def _metadata_from_result(result):
    candidates = []
    if isinstance(result, dict):
        result = _event_payload(result)
        candidates.append(result.get("metadata"))
        status = result.get("status")
        if isinstance(status, dict):
            candidates.append(status.get("metadata"))
        task = result.get("task")
        if isinstance(task, dict):
            candidates.append(task.get("metadata"))
    for value in candidates:
        if isinstance(value, dict) and isinstance(value.get("iac_code"), dict):
            return value["iac_code"]
    return {}


def _task_identity(result):
    if not isinstance(result, dict):
        return None, None
    result = _event_payload(result)
    task_id = result.get("taskId") or result.get("id")
    context_id = result.get("contextId")
    task = result.get("task")
    if isinstance(task, dict):
        task_id = task_id or task.get("id") or task.get("taskId")
        context_id = context_id or task.get("contextId")
    return task_id if isinstance(task_id, str) else None, context_id if isinstance(context_id, str) else None


def _safe_input_envelope(value):
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    common = {"schemaVersion", "kind", "requestTaskId", "contextId", "inputId", "prompt", "options", "required"}
    if kind == "permission":
        common.update(
            {
                "toolUseId",
                "toolName",
                "title",
                "purpose",
                "effect",
                "target",
                "isReadOnly",
                "safeSummary",
                "deploymentSummary",
                "language",
            }
        )
    elif kind == "ask_user_question":
        common.update({"allowFreeText", "freeTextPrompt"})
    elif kind not in {"ask_user_question", "candidate_selection"}:
        return None
    projected = {key: value[key] for key in common if key in value}
    projected["prompt"] = _sanitize_text(projected.get("prompt"), 600)
    if "allowFreeText" in projected:
        projected["allowFreeText"] = projected["allowFreeText"] is True
    if "freeTextPrompt" in projected:
        projected["freeTextPrompt"] = _sanitize_text(projected["freeTextPrompt"], 400)
    if "safeSummary" in projected:
        projected["safeSummary"] = _sanitize_text(projected["safeSummary"], 1000)
    for key, maximum in (("title", 200), ("purpose", 500), ("effect", 80), ("target", 500)):
        if key in projected:
            projected[key] = _sanitize_text(projected[key], maximum)
    if "isReadOnly" in projected:
        projected["isReadOnly"] = projected["isReadOnly"] is True
    if "language" in projected:
        projected["language"] = _sanitize_text(projected["language"], 10)
    if "deploymentSummary" in projected:
        projected["deploymentSummary"] = _safe_deployment_summary(projected["deploymentSummary"])
    options = projected.get("options")
    if isinstance(options, list):
        safe_options = []
        for item in options[:20]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            safe_item = {
                "id": _sanitize_text(item.get("id"), 120),
                "label": _sanitize_text(item.get("label"), 200),
            }
            if kind == "candidate_selection":
                for key, maximum in (
                    ("summary", 600),
                    ("totalMonthlyCost", 300),
                ):
                    if key in item:
                        safe_item[key] = _sanitize_text(item.get(key), maximum)
                if "architectureDiagram" in item:
                    safe_item["architectureDiagram"] = _sanitize_stream_text(
                        item.get("architectureDiagram"),
                        1600,
                    )
                cost_items = item.get("costItems")
                if isinstance(cost_items, list):
                    safe_item["costItems"] = [
                        {
                            key: _sanitize_text(cost_item.get(key), maximum)
                            for key, maximum in (("name", 200), ("spec", 300), ("monthlyCost", 300))
                            if key in cost_item
                        }
                        for cost_item in cost_items[:12]
                        if isinstance(cost_item, dict)
                    ]
            safe_options.append(safe_item)
        projected["options"] = safe_options
    return projected


def _safe_deployment_summary(value):
    if not isinstance(value, dict):
        return None
    summary = {
        key: _sanitize_text(value.get(key), maximum)
        for key, maximum in (
            ("candidateName", 200),
            ("action", 80),
            ("region", 120),
            ("stackName", 200),
            ("template", 300),
            ("totalMonthlyCost", 300),
        )
        if key in value
    }
    resources = value.get("resources")
    if isinstance(resources, list):
        summary["resources"] = [
            {
                key: _sanitize_text(resource.get(key), maximum)
                for key, maximum in (("name", 200), ("spec", 300), ("monthlyCost", 300))
                if key in resource
            }
            for resource in resources[:12]
            if isinstance(resource, dict)
        ]
    return summary or None


def _safe_cleanup_summary(value):
    if not isinstance(value, dict):
        return None
    status = value.get("status") or value.get("cleanupStatus")
    if not isinstance(status, str) or status not in CLEANUP_PENDING_STATES | CLEANUP_TERMINAL_STATES:
        return None
    summary = {"status": status}
    resource_count = value.get("resourceCount")
    if isinstance(resource_count, int) and 0 <= resource_count <= 10000:
        summary["resourceCount"] = resource_count
    status_message = value.get("statusMessage")
    if isinstance(status_message, str) and status_message:
        summary["statusMessage"] = _sanitize_text(status_message, 400)
    resources = value.get("resources")
    if isinstance(resources, list):
        public_resources = []
        for resource in resources[:12]:
            if not isinstance(resource, dict):
                continue
            public_resource = {}
            for key, maximum in (
                ("provider", 80),
                ("resourceType", 120),
                ("resourceId", 240),
                ("resourceName", 200),
                ("regionId", 120),
                ("sourceStepId", 120),
                ("cleanupStatus", 80),
                ("progressStatus", 120),
            ):
                item = resource.get(key)
                if isinstance(item, str) and item:
                    public_resource[key] = _sanitize_text(item, maximum)
            if public_resource:
                public_resources.append(public_resource)
        summary["resources"] = public_resources
    while len(_json_bytes(summary)) > 800 and summary.get("resources"):
        summary["resources"].pop()
    return summary


def _safe_pipeline_result(value):
    """Project the selling Pipeline deployment conclusion into the bounded public result."""
    if not isinstance(value, dict):
        return None
    result = {}
    for key, maximum in (("status", 80), ("stack_id", 240), ("error", 800)):
        raw = value.get(key)
        if isinstance(raw, str) and raw:
            result[key] = _sanitize_text(raw, maximum)
    resources = value.get("resources_created")
    if isinstance(resources, list):
        result["resources_created"] = [
            _sanitize_text(resource, 240) for resource in resources[:24] if isinstance(resource, str) and resource
        ]
    outputs = value.get("outputs")
    if isinstance(outputs, dict):
        result["outputs"] = {
            _sanitize_text(str(key), 120): _sanitize_text(str(output), 300)
            for key, output in list(outputs.items())[:24]
            if isinstance(key, str) and isinstance(output, (str, int, float, bool))
        }
    if not result:
        return None
    while len(_json_bytes(result)) > MAX_PIPELINE_RESULT_BYTES:
        resource_values = result.get("resources_created")
        output_values = result.get("outputs")
        if isinstance(resource_values, list) and len(resource_values) > 8:
            resource_values.pop()
            continue
        if isinstance(output_values, dict) and len(output_values) > 12:
            output_values.pop(next(reversed(output_values)))
            continue
        changed = False
        if isinstance(resource_values, list):
            for index, item in enumerate(resource_values):
                if isinstance(item, str) and len(item) > 40:
                    resource_values[index] = item[: max(40, len(item) // 2)]
                    changed = True
        if isinstance(output_values, dict):
            for key, item in list(output_values.items()):
                if isinstance(item, str) and len(item) > 40:
                    output_values[key] = item[: max(40, len(item) // 2)]
                    changed = True
        if not changed:
            break
    if len(_json_bytes(result)) > MAX_PIPELINE_RESULT_BYTES:
        result = {key: result[key] for key in ("status", "stack_id") if key in result}
    return result or None


def _safe_summary_scalar(value, maximum):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return _sanitize_text(value, maximum)
    return None


def _safe_intent_conclusion_summary(value):
    if not isinstance(value, dict):
        return None
    summary = {}
    for source, target, maximum in (
        ("user_message_summary", "requirementSummary", 360),
        ("cloud_platform", "cloudPlatform", 80),
        ("business_type", "businessType", 120),
    ):
        item = value.get(source)
        if isinstance(item, str) and item:
            summary[target] = _sanitize_text(item, maximum)

    non_functional = value.get("non_functional")
    if isinstance(non_functional, dict):
        region = non_functional.get("region_preference")
        if isinstance(region, str) and region:
            summary["region"] = _sanitize_text(region, 120)

    resource_intents = value.get("resource_intents")
    if isinstance(resource_intents, list):
        resources = []
        for resource in resource_intents[:10]:
            if not isinstance(resource, dict):
                continue
            public_resource = {
                key: _sanitize_text(resource.get(key), maximum)
                for key, maximum in (("product", 100), ("action", 40), ("role", 100))
                if isinstance(resource.get(key), str) and resource.get(key)
            }
            if public_resource:
                resources.append(public_resource)
        if resources:
            summary["resources"] = resources

    hard_constraints = value.get("hard_constraints")
    if isinstance(hard_constraints, list):
        constraints = []
        for constraint in hard_constraints[:8]:
            if not isinstance(constraint, dict):
                continue
            public_constraint = {
                key: _sanitize_text(constraint.get(key), maximum)
                for key, maximum in (("target", 100), ("property", 80), ("operator", 24), ("unit", 32))
                if isinstance(constraint.get(key), str) and constraint.get(key)
            }
            property_name = str(constraint.get("property") or "")
            if not re.search(r"(?i)(password|secret|token|credential|access.?key)", property_name):
                constraint_value = _safe_summary_scalar(constraint.get("value"), 160)
                if constraint_value not in (None, ""):
                    public_constraint["value"] = constraint_value
            if public_constraint:
                constraints.append(public_constraint)
        if constraints:
            summary["hardConstraints"] = constraints

    while len(_json_bytes(summary)) > MAX_STEP_CONCLUSION_SUMMARY_BYTES:
        constraints = summary.get("hardConstraints")
        resources = summary.get("resources")
        if isinstance(constraints, list) and constraints:
            constraints.pop()
            if not constraints:
                summary.pop("hardConstraints", None)
            continue
        if isinstance(resources, list) and len(resources) > 3:
            resources.pop()
            continue
        requirement = summary.get("requirementSummary")
        if isinstance(requirement, str) and len(requirement) > 120:
            summary["requirementSummary"] = requirement[: max(120, len(requirement) // 2)]
            continue
        role_removed = False
        if isinstance(resources, list):
            for resource in reversed(resources):
                if isinstance(resource, dict) and "role" in resource:
                    resource.pop("role")
                    role_removed = True
                    break
        if role_removed:
            continue
        if "businessType" in summary:
            summary.pop("businessType")
            continue
        if "cloudPlatform" in summary:
            summary.pop("cloudPlatform")
            continue
        if isinstance(resources, list) and len(resources) > 1:
            resources.pop()
            continue
        break
    return summary or None


def _safe_architecture_conclusion_summary(value):
    if not isinstance(value, dict):
        return None
    raw_candidates = value.get("candidates")
    if not isinstance(raw_candidates, list):
        return None
    candidates = []
    for candidate in raw_candidates[:4]:
        if not isinstance(candidate, dict):
            continue
        public_candidate = {}
        for source, target, maximum in (
            ("name", "name", 160),
            ("topology", "topology", 300),
            ("monthly_estimate", "monthlyEstimate", 160),
        ):
            item = candidate.get(source)
            if isinstance(item, str) and item:
                public_candidate[target] = _sanitize_text(item, maximum)
        products = candidate.get("products")
        if isinstance(products, list):
            public_products = [
                _sanitize_text(product, 80) for product in products[:8] if isinstance(product, str) and product
            ]
            if public_products:
                public_candidate["products"] = public_products
        for source, target in (("pros", "pros"), ("cons", "cons")):
            items = candidate.get(source)
            if isinstance(items, list):
                public_items = [_sanitize_text(item, 140) for item in items[:2] if isinstance(item, str) and item]
                if public_items:
                    public_candidate[target] = public_items
        if public_candidate:
            candidates.append(public_candidate)

    summary = {"candidateCount": len(raw_candidates), "candidates": candidates}
    while len(_json_bytes(summary)) > MAX_STEP_CONCLUSION_SUMMARY_BYTES:
        changed = False
        for key in ("cons", "pros", "products"):
            for candidate in reversed(candidates):
                values = candidate.get(key)
                if isinstance(values, list) and values:
                    values.pop()
                    if not values:
                        candidate.pop(key, None)
                    changed = True
                    break
            if changed:
                break
        if changed:
            continue
        if len(candidates) > 2:
            candidates.pop()
            continue
        for candidate in reversed(candidates):
            topology = candidate.get("topology")
            if isinstance(topology, str) and len(topology) > 100:
                candidate["topology"] = topology[: max(100, len(topology) // 2)]
                changed = True
                break
        if changed:
            continue
        for key in ("topology", "monthlyEstimate"):
            for candidate in reversed(candidates):
                if key in candidate:
                    candidate.pop(key)
                    changed = True
                    break
            if changed:
                break
        if changed:
            continue
        if len(candidates) > 1:
            candidates.pop()
            continue
        break
    return summary if candidates else None


def _safe_step_conclusion_summary(step_id, conclusion_field, value):
    if step_id == "intent_parsing" or conclusion_field == "intent":
        return _safe_intent_conclusion_summary(value)
    if step_id == "architecture_planning" or conclusion_field == "architecture":
        return _safe_architecture_conclusion_summary(value)
    return None


def _bounded_input_projection(projection):
    """Keep an input-required control event answerable within the spool/poll budget."""
    bounded = dict(projection)
    envelope = bounded.get("inputRequired")
    if not isinstance(envelope, dict):
        return bounded
    envelope = dict(envelope)
    options = envelope.get("options")
    if isinstance(options, list):
        envelope["options"] = [dict(item) for item in options if isinstance(item, dict)]
    bounded["inputRequired"] = envelope

    def shrink(key, minimum):
        value = envelope.get(key)
        if not isinstance(value, str) or len(value) <= minimum:
            return False
        envelope[key] = value[: max(minimum, len(value) // 2)]
        return True

    while len(_json_bytes(bounded)) > MAX_INPUT_PROJECTION_BYTES:
        changed = shrink("safeSummary", 160)
        changed = shrink("purpose", 100) or changed
        changed = shrink("target", 80) or changed
        changed = shrink("title", 60) or changed
        changed = shrink("prompt", 120) or changed
        changed = shrink("freeTextPrompt", 80) or changed
        changed = shrink("toolName", 40) or changed
        option_values = envelope.get("options")
        if isinstance(option_values, list):
            for option in option_values:
                label = option.get("label")
                if isinstance(label, str) and len(label) > 16:
                    option["label"] = label[: max(16, len(label) // 2)]
                    changed = True
                for key, minimum in (("summary", 80), ("architectureDiagram", 120), ("totalMonthlyCost", 20)):
                    value = option.get(key)
                    if isinstance(value, str) and len(value) > minimum:
                        option[key] = value[: max(minimum, len(value) // 2)]
                        changed = True
                cost_items = option.get("costItems")
                if isinstance(cost_items, list):
                    for cost_item in cost_items:
                        for key, minimum in (("name", 16), ("spec", 16), ("monthlyCost", 12)):
                            value = cost_item.get(key)
                            if isinstance(value, str) and len(value) > minimum:
                                cost_item[key] = value[: max(minimum, len(value) // 2)]
                                changed = True
        deployment_summary = envelope.get("deploymentSummary")
        if isinstance(deployment_summary, dict):
            resources = deployment_summary.get("resources")
            if isinstance(resources, list) and len(resources) > 1:
                resources.pop()
                changed = True
        if not changed:
            break
    if len(_json_bytes(bounded)) > MAX_INPUT_PROJECTION_BYTES:
        option_values = envelope.get("options")
        if isinstance(option_values, list):
            for key in ("costItems", "architectureDiagram", "summary", "totalMonthlyCost"):
                for option in option_values:
                    option.pop(key, None)
                if len(_json_bytes(bounded)) <= MAX_INPUT_PROJECTION_BYTES:
                    break
    if len(_json_bytes(bounded)) > MAX_INPUT_PROJECTION_BYTES:
        envelope.pop("deploymentSummary", None)
    if len(_json_bytes(bounded)) > MAX_INPUT_PROJECTION_BYTES:
        raise BridgeError(
            "a2a_transport_failed",
            "The A2A input request exceeded the bounded Skill protocol.",
        )
    if bounded != projection:
        bounded["trimmed"] = True
    return bounded


def project_frame(frame):
    result = frame.get("result") if isinstance(frame, dict) else None
    if not isinstance(result, dict):
        return {"type": "diagnostic", "category": "unknown", "count": 1, "time": int(time.time())}
    event_payload = _event_payload(result)
    task_id, context_id = _task_identity(result)
    state = _state_from_result(result)
    metadata = _metadata_from_result(result)
    projected = {"type": "status", "time": int(time.time())}
    if task_id:
        projected["taskId"] = task_id
    if context_id:
        projected["contextId"] = context_id
    if state:
        projected["state"] = state
    input_value = _safe_input_envelope(metadata.get("input"))
    if input_value is None and state == "working" and isinstance(metadata.get("pendingPermissions"), list):
        input_value = next(
            (
                safe
                for value in metadata["pendingPermissions"]
                if (safe := _safe_input_envelope(value)) is not None and safe.get("kind") == "permission"
            ),
            None,
        )
    if input_value is not None:
        projection_type = (
            "permission-requested"
            if state == "working" and input_value.get("kind") == "permission"
            else "input-required"
        )
        projected.update({"type": projection_type, "inputRequired": input_value})
        return _bounded_input_projection(projected)
    cleanup_only = _safe_cleanup_summary(metadata.get("cleanupOnly"))
    if cleanup_only is not None:
        projected["cleanup"] = cleanup_only
        projected["cleanupOnly"] = True
    assistant_final = metadata.get("assistantFinal")
    if isinstance(assistant_final, dict) and assistant_final.get("complete") is True:
        projected.update(
            {
                "type": "assistant-final",
                "finalText": _sanitize_stream_text(_message_text_from_result(result)),
                "finalTextComplete": True,
            }
        )
        return projected
    pipeline_values = []
    if isinstance(metadata.get("pipelineBatch"), dict) and isinstance(metadata["pipelineBatch"].get("events"), list):
        pipeline_values = metadata["pipelineBatch"]["events"]
    elif isinstance(metadata.get("pipeline"), dict):
        pipeline_values = [metadata["pipeline"]]
    if pipeline_values:
        for item in pipeline_values:
            if not isinstance(item, dict):
                continue
            data = item.get("data")
            if not isinstance(data, dict):
                continue
            conclusion_field = data.get("conclusionField")
            if item.get("eventType") == "step_completed" and conclusion_field in PIPELINE_RESULT_FIELDS.values():
                pipeline_result = _safe_pipeline_result(data.get("conclusion"))
                if pipeline_result is not None:
                    projected["pipelineResultField"] = conclusion_field
                    projected["pipelineResult"] = pipeline_result
            if (
                item.get("eventType") == "pipeline_handoff_ready"
                and item.get("visibility") in {None, "committed"}
                and data.get("action") == "switch_to_normal"
                and data.get("targetMode") == "normal"
            ):
                projected["normalHandoffReady"] = True
                cleanup = _safe_cleanup_summary(data.get("cleanup"))
                if cleanup is not None:
                    projected["cleanup"] = cleanup
        milestones = []
        allowed_types = {
            "pipeline_started",
            "pipeline_resumed",
            "step_started",
            "step_completed",
            "step_failed",
            "candidate_started",
            "candidate_step_started",
            "candidate_step_completed",
            "candidate_step_failed",
            "candidate_completed",
            "candidate_selected",
            "tool_started",
            "tool_result",
            "artifact_created",
            "pipeline_completed",
            "pipeline_failed",
            "pipeline_canceled",
            "input_required",
            "permission_requested",
            "permission_resolved",
            "pipeline_handoff_ready",
            "cleanup_started",
            "cleanup_progress",
            "cleanup_completed",
            "cleanup_failed",
        }
        resolved_input_ids = []
        recent_ids = {id(item) for item in pipeline_values[-MAX_POLL_EVENTS:]}
        selected_items = [
            item
            for item in pipeline_values
            if id(item) in recent_ids
            or (isinstance(item, dict) and item.get("eventType") in PROGRESS_BOUNDARY_EVENT_TYPES)
        ]
        for item in selected_items:
            if not isinstance(item, dict) or item.get("eventType") not in allowed_types:
                continue
            milestone = {
                "eventType": item.get("eventType"),
                "status": item.get("status"),
                "sequence": item.get("sequence"),
            }
            for key in ("step", "parentStep", "candidate", "candidateStep"):
                value = item.get(key)
                if isinstance(value, dict):
                    milestone[key] = {
                        field: value[field]
                        for field in ("id", "name", "index", "total")
                        if field in value and isinstance(value[field], (str, int))
                    }
            data = item.get("data")
            if isinstance(data, dict):
                public_message = data.get("message") or data.get("summary") or data.get("description")
                if isinstance(public_message, str):
                    milestone["message"] = _sanitize_text(public_message, 400)
                if item.get("eventType") == "step_completed":
                    step = item.get("step")
                    step_id = step.get("id") if isinstance(step, dict) else None
                    conclusion_summary = _safe_step_conclusion_summary(
                        step_id,
                        data.get("conclusionField"),
                        data.get("conclusion"),
                    )
                    if conclusion_summary is not None:
                        milestone["conclusionSummary"] = conclusion_summary
                tool_name = data.get("toolName") or data.get("name")
                if isinstance(tool_name, str):
                    milestone["toolName"] = _sanitize_text(tool_name, 120)
                tool_use_id = data.get("toolUseId")
                if isinstance(tool_use_id, str):
                    milestone["toolUseId"] = tool_use_id[:128]
            if item.get("eventType") == "permission_resolved":
                permission = item.get("permission")
                input_id = permission.get("inputId") if isinstance(permission, dict) else None
                if not isinstance(input_id, str) and isinstance(data, dict):
                    input_id = data.get("inputId")
                if isinstance(input_id, str) and input_id:
                    resolved_input_ids.append(input_id)
            milestones.append(milestone)
        if milestones:
            projected.update({"type": "milestone", "milestones": milestones})
        if resolved_input_ids:
            projected["resolvedInputIds"] = resolved_input_ids
    tool = metadata.get("tool")
    if isinstance(tool, dict) and tool.get("status") in {"started", "completed", "failed", "progress"}:
        projected.update(
            {
                "type": "milestone",
                "milestones": [
                    {
                        "eventType": "tool_" + str(tool.get("status")),
                        "toolName": _sanitize_text(tool.get("name"), 120),
                        "toolUseId": str(tool.get("toolUseId") or "")[:128],
                    }
                ],
            }
        )
    text = _message_from_result(result)
    if text:
        projected["text"] = text
        if projected["type"] == "status":
            projected["type"] = "text"
    artifacts = []
    artifact = event_payload.get("artifact")
    if isinstance(artifact, dict):
        parts = artifact.get("parts")
        artifact_metadata = artifact.get("metadata")
        artifact_metadata = artifact_metadata if isinstance(artifact_metadata, dict) else {}
        url = None
        filename = artifact.get("name")
        if isinstance(parts, list) and parts and isinstance(parts[0], dict):
            url = parts[0].get("url")
            filename = filename or parts[0].get("filename")
        if isinstance(url, str):
            projected_artifact = {
                "id": str(artifact.get("artifactId") or "")[:128],
                "name": _sanitize_text(filename, 200),
                "uri": url[:1000],
            }
            for key in ("mediaType", "byteSize", "sha256", "sourcePath"):
                value = artifact_metadata.get(key)
                if isinstance(value, str):
                    projected_artifact[key] = _sanitize_stream_text(value, 1000)
                elif key == "byteSize" and isinstance(value, int):
                    projected_artifact[key] = value
            artifacts.append(projected_artifact)
    if artifacts:
        projected["artifacts"] = artifacts
        projected["type"] = "artifact"
    if state in TERMINAL_STATES:
        projected["type"] = "terminal"
    elif state in INPUT_STATES and input_value is None:
        projected["type"] = "status"
    encoded = _json_bytes(projected)
    if len(encoded) > 2048:
        projected.pop("text", None)
        projected["trimmed"] = True
        milestones = projected.get("milestones")
        if isinstance(milestones, list):
            while len(_json_bytes(projected)) + 1 > MAX_PROJECTION_BYTES and milestones:
                non_boundary_index = next(
                    (
                        index
                        for index, milestone in enumerate(milestones)
                        if not isinstance(milestone, dict)
                        or milestone.get("eventType") not in STEP_BOUNDARY_EVENT_TYPES
                    ),
                    None,
                )
                milestones.pop(non_boundary_index if non_boundary_index is not None else 0)
            if not milestones:
                projected.pop("milestones", None)
    return projected


def _job_root(job_id):
    if not re.fullmatch(r"[0-9a-f]{32}", job_id or ""):
        raise BridgeError("job_not_found", "The requested Skill job does not exist.")
    return _bridge_root() / "jobs" / job_id


def _job_paths(job_id):
    root = _job_root(job_id)
    return root, root / "job.json", root / "events.jsonl"


def _turn_text_path(root, turn):
    return root / ("turn-{}-text.txt".format(turn))


def _append_turn_text(root, job, value):
    if not value:
        return
    path = _turn_text_path(root, int(job.get("turn") or 1))
    encoded = value.encode("utf-8")
    current_size = path.stat().st_size if path.exists() else 0
    if current_size + len(encoded) > MAX_TURN_RESULT_BYTES:
        raise BridgeError("a2a_transport_failed", "The bounded normal-turn result exceeded its limit.")
    with path.open("ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        os.chmod(str(path), 0o600)


def _deduplicated_artifacts(values):
    artifacts = []
    identities = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        identity = (value.get("id"), value.get("uri"), value.get("name"))
        if identity in identities:
            continue
        identities.add(identity)
        artifacts.append(value)
    return artifacts


def _public_workspace_artifact(value, workspace):
    if not isinstance(value, dict):
        return value
    artifact = dict(value)
    source_path = artifact.pop("sourcePath", None)
    if not isinstance(source_path, str) or not source_path:
        return artifact
    try:
        source = pathlib.Path(source_path).resolve()
        source.relative_to(pathlib.Path(workspace).resolve())
    except (OSError, ValueError):
        return artifact
    if not source.is_file():
        return artifact
    a2a_uri = artifact.get("uri")
    if isinstance(a2a_uri, str) and a2a_uri:
        artifact["a2aUri"] = a2a_uri
    artifact["uri"] = source.as_uri()
    return artifact


def _wire_projection(projection):
    wire = dict(projection)
    if wire.get("type") in {"assistant-final", "turn_completed"}:
        final_text = wire.pop("finalText", "")
        if isinstance(final_text, str) and final_text:
            wire["finalTextPreview"] = _truncate_utf8(final_text, 1000)
            wire["finalTextAvailable"] = True
    if wire.get("type") in {"input-required", "permission-requested"}:
        wire = _bounded_input_projection(wire)
    data = _json_bytes(wire) + b"\n"
    if len(data) <= MAX_PROJECTION_BYTES:
        return wire, data
    if wire.get("type") in {"terminal", "turn_completed"}:
        wire = {
            key: wire[key]
            for key in (
                "type",
                "state",
                "taskId",
                "contextId",
                "time",
                "finalTextAvailable",
                "finalTextComplete",
                "pipelineResultField",
                "pipelineResult",
                "normalHandoffReady",
                "cleanup",
                "cleanupOnly",
            )
            if key in wire
        }
        wire["trimmed"] = True
        return wire, _json_bytes(wire) + b"\n"
    return {"type": "diagnostic", "category": "projection_trimmed", "count": 1}, _json_bytes(
        {"type": "diagnostic", "category": "projection_trimmed", "count": 1}
    ) + b"\n"


def _append_projection(job_id, projection, turn_text=""):
    root, job_path, spool = _job_paths(job_id)
    _secure_directory(root)
    original = (
        _bounded_input_projection(projection)
        if projection.get("type") in {"input-required", "permission-requested"}
        else dict(projection)
    )
    _wire, data = _wire_projection(original)
    with InstallLock(root / ".job.lock", timeout=10):
        job = _load_json(job_path)
        context_id = original.get("contextId")
        previous_context = job.get("contextId")
        if isinstance(context_id, str) and isinstance(previous_context, str) and context_id != previous_context:
            raise BridgeError("runtime_identity_mismatch", "The A2A task changed the Skill job context.")
        if spool.exists() and spool.stat().st_size + len(data) > MAX_SPOOL_BYTES:
            raise BridgeError("a2a_transport_failed", "The bounded Skill event spool is full.")
        task_id = original.get("taskId")
        if isinstance(task_id, str):
            previous_task = job.get("taskId")
            if isinstance(previous_task, str) and previous_task != task_id:
                history = job.setdefault("taskHistory", [])
                if previous_task not in history:
                    history.append(previous_task)
            job["taskId"] = task_id
        if isinstance(context_id, str):
            job["contextId"] = context_id
        if isinstance(original.get("state"), str):
            job["state"] = original["state"]
        result_field = original.get("pipelineResultField")
        pipeline_result = original.get("pipelineResult")
        if (
            job.get("mode") == "pipeline"
            and result_field == PIPELINE_RESULT_FIELDS.get(job.get("pipelineName"))
            and isinstance(pipeline_result, dict)
        ):
            job["pipelineResult"] = pipeline_result
        if original.get("normalHandoffReady") is True and job.get("mode") == "pipeline":
            job["normalHandoffReady"] = True
            job["conversationMode"] = "normal"
        cleanup = original.get("cleanup")
        if isinstance(cleanup, dict):
            previous_cleanup = job.get("cleanup")
            merged_cleanup = dict(previous_cleanup) if isinstance(previous_cleanup, dict) else {}
            merged_cleanup.update(cleanup)
            if "resources" not in cleanup and isinstance(previous_cleanup, dict):
                previous_resources = previous_cleanup.get("resources")
                if isinstance(previous_resources, list):
                    merged_cleanup["resources"] = previous_resources
            job["cleanup"] = merged_cleanup
        if original.get("cleanupOnly") is True:
            job["cleanupOnlyActive"] = True
        _append_turn_text(root, job, turn_text)
        if isinstance(original.get("artifacts"), list):
            public_artifacts = [_public_workspace_artifact(value, job["workspace"]) for value in original["artifacts"]]
            job["turnArtifacts"] = _deduplicated_artifacts(list(job.get("turnArtifacts") or []) + public_artifacts)
        if original.get("type") == "input-required":
            job["inputRequired"] = original.get("inputRequired")
            job["state"] = "input-required"
        elif original.get("type") == "permission-requested":
            pending = original.get("inputRequired")
            if isinstance(pending, dict):
                pending_values = job.setdefault("pendingPermissions", [])
                if not any(
                    isinstance(value, dict) and value.get("inputId") == pending.get("inputId")
                    for value in pending_values
                ):
                    pending_values.append(pending)
                if not isinstance(job.get("inputRequired"), dict):
                    job["inputRequired"] = pending
        elif original.get("type") == "assistant-final":
            _atomic_text(_turn_text_path(root, int(job.get("turn") or 1)), original.get("finalText", ""))
            job["assistantFinalReceived"] = True
        elif original.get("type") == "turn_completed":
            job["state"] = TURN_COMPLETED_STATE
            job["finalText"] = original.get("finalText", "")
            job["finalTextComplete"] = original.get("finalTextComplete") is True
            job["finalArtifacts"] = _deduplicated_artifacts(list(original.get("artifacts") or []))
            job["turnCompletedAt"] = int(time.time())
            job.pop("inputRequired", None)
        elif original.get("type") == "terminal":
            if (
                original.get("state") == "completed"
                and job.get("mode") == "pipeline"
                and job.get("pipelineName") in PIPELINE_NORMAL_HANDOFFS
            ):
                job["conversationMode"] = "normal"
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
        resolved_input_ids = original.get("resolvedInputIds")
        if isinstance(resolved_input_ids, list):
            resolved = {value for value in resolved_input_ids if isinstance(value, str)}
            pending_values = [
                value
                for value in job.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") not in resolved
            ]
            if pending_values:
                job["pendingPermissions"] = pending_values
                current = job.get("inputRequired")
                if not isinstance(current, dict) or current.get("inputId") in resolved:
                    job["inputRequired"] = pending_values[0]
            else:
                job.pop("pendingPermissions", None)
                current = job.get("inputRequired")
                if isinstance(current, dict) and current.get("inputId") in resolved:
                    job.pop("inputRequired", None)
        with spool.open("ab") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            os.chmod(str(spool), 0o600)
        _atomic_json(job_path, job)


def _job_uses_normal_conversation(job):
    return job.get("mode") == "normal" or job.get("conversationMode") == "normal"


def _complete_normal_turn(job_id):
    root, job_path, _spool = _job_paths(job_id)
    job = _load_json(job_path)
    if not _job_uses_normal_conversation(job):
        return
    if job.get("state") == TURN_COMPLETED_STATE:
        return
    turn = int(job.get("turn") or 1)
    path = _turn_text_path(root, turn)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    artifacts = list(job.get("turnArtifacts") or [])
    complete = len(text.encode("utf-8")) <= MAX_FINAL_TEXT_BYTES
    if complete:
        final_text = text
    else:
        result_directory = pathlib.Path(job["workspace"]) / ".iac-code-skill-results"
        result_name = "{}-turn-{}.txt".format(job_id, turn)
        result_path = result_directory / result_name
        _atomic_text(result_path, text)
        artifacts.append(
            {
                "id": "normal-turn-{}".format(turn),
                "name": result_name,
                "uri": result_path.resolve().as_uri(),
                "mediaType": "text/plain",
            }
        )
        final_text = _truncate_utf8(text, 1500)
        if final_text:
            final_text += "\n\n[The complete response is available in the result artifact.]"
        else:
            final_text = "The complete response is available in the result artifact."
    _append_projection(
        job_id,
        {
            "type": "turn_completed",
            "state": TURN_COMPLETED_STATE,
            "taskId": job.get("taskId"),
            "contextId": job.get("contextId"),
            "turn": turn,
            "finalText": final_text,
            "finalTextComplete": complete,
            "artifacts": _deduplicated_artifacts(artifacts),
            "time": int(time.time()),
        },
    )


def _jsonrpc_payload(method, params):
    return {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}


def _stream_jsonrpc(record, payload):
    url = "http://127.0.0.1:{}/".format(record["port"])
    request = urllib.request.Request(
        url,
        data=_json_bytes(payload),
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "A2A-Version": "1.0",
            "User-Agent": _SKILL_USER_AGENT,
            "Authorization": "Bearer " + record["token"],
        },
        method="POST",
    )
    try:
        response = urllib.request.urlopen(request, timeout=300)
    except (OSError, urllib.error.URLError) as exc:
        raise BridgeError("a2a_transport_failed", "The local A2A stream could not be opened.", True) from exc
    with response:
        data_lines = []
        while True:
            raw = response.readline(1024 * 1024 + 1)
            if not raw:
                break
            if len(raw) > 1024 * 1024:
                raise BridgeError("a2a_transport_failed", "An A2A event exceeded the bridge limit.")
            line = raw.decode("utf-8", "strict").rstrip("\r\n")
            if not line:
                if data_lines:
                    value = json.loads("\n".join(data_lines))
                    if isinstance(value, dict):
                        yield value
                    data_lines = []
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if data_lines:
            value = json.loads("\n".join(data_lines))
            if isinstance(value, dict):
                yield value


def _validate_response_correlation(response, pending):
    if not isinstance(response, dict) or not isinstance(pending, dict):
        raise BridgeError("input_response_mismatch", "The response correlation is incomplete.")
    if response.get("kind") != pending.get("kind"):
        raise BridgeError("input_response_mismatch", "The response kind does not match the pending input.")
    required = ["requestTaskId", "contextId", "inputId"]
    if pending.get("kind") == "permission":
        required.append("toolUseId")
    for key in required:
        supplied = response.get(key)
        expected = pending.get(key)
        if not isinstance(supplied, str) or not supplied or supplied != expected:
            raise BridgeError(
                "input_response_mismatch",
                "The response must include correlation fields matching the pending input.",
            )


def _worker_payload(job, prompt=None, response=None, cleanup_only=False):
    iac_metadata = {
        "cwd": job["workspace"],
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "candidatePresentation": "rich-v1",
    }
    channel = _normalize_telemetry_channel(job.get("channel")) if job.get("channel") is not None else None
    if channel is not None:
        iac_metadata["channel"] = channel
    if cleanup_only:
        iac_metadata["cleanupOnly"] = True
    message = {
        "messageId": str(uuid.uuid4()),
        "role": "ROLE_USER",
        "metadata": {"iac_code": iac_metadata},
    }
    if response is None:
        message["parts"] = [{"text": prompt}]
        if job.get("contextId"):
            message["contextId"] = job["contextId"]
    elif response.get("kind") == "permission":
        pending = job.get("inputRequired")
        if not isinstance(pending, dict):
            raise BridgeError("input_response_mismatch", "The job has no pending permission input.")
        _validate_response_correlation(response, pending)
        decision = response.get("decision")
        if decision not in {"allow_once", "deny"}:
            raise BridgeError("input_response_mismatch", "Permission decision must be allow_once or deny.")
        task_id = pending.get("requestTaskId")
        context_id = pending.get("contextId")
        message.update(
            {
                "taskId": task_id,
                "contextId": context_id,
                "parts": [
                    {
                        "mediaType": "application/json",
                        "data": {
                            "schemaVersion": 1,
                            "kind": "permission",
                            "requestTaskId": task_id,
                            "inputId": pending.get("inputId"),
                            "toolUseId": pending.get("toolUseId"),
                            "decision": decision,
                        },
                    }
                ],
            }
        )
    else:
        pending = job.get("inputRequired")
        if not isinstance(pending, dict):
            raise BridgeError("input_response_mismatch", "The job has no pending input.")
        _validate_response_correlation(response, pending)
        answer = response.get("answer") if isinstance(response, dict) else None
        if answer is None:
            answer = response
        message.update(
            {
                "taskId": job.get("taskId"),
                "contextId": job.get("contextId"),
                "parts": [{"text": answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)}],
            }
        )
    sideband_permission = (
        response is not None
        and response.get("kind") == "permission"
        and any(
            isinstance(value, dict) and value.get("inputId") == response.get("inputId")
            for value in job.get("pendingPermissions", [])
        )
    )
    return _jsonrpc_payload(
        "SendMessage" if sideband_permission else "SendStreamingMessage",
        {"message": message, "configuration": {"acceptedOutputModes": ["text/plain"]}},
    )


def _validate_permission_ack(frame, response):
    result = frame.get("result") if isinstance(frame, dict) else None
    message = result.get("message") if isinstance(result, dict) and isinstance(result.get("message"), dict) else result
    if not isinstance(message, dict) or message.get("role") not in {"ROLE_AGENT", "agent"}:
        raise BridgeError("a2a_transport_failed", "The A2A runtime did not return a permission ACK.", True)
    parts = message.get("parts")
    if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
        raise BridgeError("a2a_transport_failed", "The A2A permission ACK is malformed.", True)
    data = parts[0].get("data")
    expected_decision = response.get("decision")
    if (
        not isinstance(data, dict)
        or data.get("kind") != "permission_ack"
        or data.get("accepted") is not True
        or data.get("inputId") != response.get("inputId")
        or data.get("toolUseId") != response.get("toolUseId")
        or data.get("decision") not in {expected_decision, "deny"}
    ):
        raise BridgeError("a2a_transport_failed", "The A2A permission ACK correlation is invalid.", True)
    return data


def _remove_job_pending_permission(job, input_id):
    remaining = [
        value
        for value in job.get("pendingPermissions", [])
        if isinstance(value, dict) and value.get("inputId") != input_id
    ]
    if remaining:
        job["pendingPermissions"] = remaining
        current = job.get("inputRequired")
        if not isinstance(current, dict) or current.get("inputId") == input_id:
            job["inputRequired"] = remaining[0]
    else:
        job.pop("pendingPermissions", None)
        current = job.get("inputRequired")
        if isinstance(current, dict) and current.get("inputId") == input_id:
            job.pop("inputRequired", None)


def _subscription_after_stream(record, job_id):
    _root, job_path, _spool = _job_paths(job_id)
    job = _load_json(job_path)
    task_id = job.get("taskId")
    if not isinstance(task_id, str):
        return None
    status = _http_json(
        "http://127.0.0.1:{}/".format(record["port"]),
        record["token"],
        method="POST",
        payload=_jsonrpc_payload("GetTask", {"id": task_id}),
        timeout=10,
    )
    projection = project_frame(status)
    _append_projection(job_id, projection)
    if projection.get("type") in {"terminal", "input-required"}:
        return None
    if projection.get("state") in INPUT_STATES:
        # A normal turn ends in INPUT_REQUIRED without an envelope to mean that
        # the context can accept a later user message; it is not an open prompt.
        _complete_normal_turn(job_id)
        return None
    return _jsonrpc_payload("SubscribeToTask", {"id": task_id})


def worker(job_id, request_path):
    root, job_path, _spool = _job_paths(job_id)
    job = _load_json(job_path)
    record = _runtime_record_for_job(job)
    payload = _load_json(pathlib.Path(request_path), "input_response_mismatch")
    attempts = 0
    while attempts < 3:
        attempts += 1
        try:
            for frame in _stream_jsonrpc(record, payload):
                projection = project_frame(frame)
                _append_projection(job_id, projection)
                if projection.get("type") == "terminal" or projection.get("type") == "input-required":
                    return 0
            payload = _subscription_after_stream(record, job_id)
            if payload is None:
                return 0
        except (BridgeError, ValueError, UnicodeDecodeError):
            job = _load_json(job_path)
            task_id = job.get("taskId")
            if not isinstance(task_id, str):
                if attempts >= 3:
                    raise
                time.sleep(0.2 * attempts)
                continue
            payload = _subscription_after_stream(record, job_id)
            if payload is None:
                return 0
    raise BridgeError("a2a_transport_failed", "The local A2A stream could not be resumed.", True)


def _spawn_worker(job_id, payload):
    root, _job_path, _spool = _job_paths(job_id)
    request_path = root / ("request-{}.json".format(uuid.uuid4().hex))
    _atomic_json(request_path, payload)
    command = [
        sys.executable,
        str(pathlib.Path(__file__).resolve()),
        "_worker",
        "--job-id",
        job_id,
        "--request",
        str(request_path),
    ]
    log_path = root / "worker.log"
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    with log_path.open("ab", buffering=0) as log:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=os.name != "nt",
            creationflags=creationflags,
        )
    return process.pid


def _read_workspace_prompt(workspace, prompt_file):
    prompt_path = pathlib.Path(prompt_file).resolve()
    try:
        prompt_path.relative_to(workspace)
    except ValueError as exc:
        raise BridgeError("runtime_identity_mismatch", "The prompt file must be inside the workspace.") from exc
    try:
        prompt = prompt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise BridgeError("a2a_transport_failed", "The prompt file could not be read as UTF-8.") from exc
    if not prompt.strip() or len(prompt.encode("utf-8")) > 1024 * 1024:
        raise BridgeError("a2a_transport_failed", "The prompt file is empty or too large.")
    return prompt


def _preferred_language(prompt, requested):
    if requested in SUPPORTED_LANGUAGES:
        return requested
    if re.search(r"[\u3040-\u30ff]", prompt):
        return "ja"
    if re.search(r"[\u3400-\u9fff]", prompt):
        return "zh"
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "").lower().split("_", 1)[0].split(".", 1)[0]
        if value in SUPPORTED_LANGUAGES:
            return value
    return "en"


def _normalize_telemetry_channel(value):
    if value is None:
        return None
    channel = value.strip() if isinstance(value, str) else ""
    if channel.startswith(SKILL_CHANNEL_PREFIX):
        channel = channel[len(SKILL_CHANNEL_PREFIX) :].strip()
    if channel:
        return SKILL_CHANNEL_PREFIX + channel[: MAX_CHANNEL_LENGTH - len(SKILL_CHANNEL_PREFIX)]
    raise BridgeError("skill_configuration_invalid", "The Skill telemetry channel must be a non-empty string.")


def _permission_wait_number(value, name, allow_zero):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BridgeError(
            "skill_configuration_invalid",
            "{} must be a finite {} number no greater than {} seconds or null.".format(
                name,
                "non-negative" if allow_zero else "positive",
                MAX_PERMISSION_WAIT_SECONDS,
            ),
        )
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise BridgeError(
            "skill_configuration_invalid",
            "{} must be a finite number no greater than {} seconds or null.".format(
                name,
                MAX_PERMISSION_WAIT_SECONDS,
            ),
        ) from exc
    if (
        not math.isfinite(number)
        or number < 0
        or (number == 0 and not allow_zero)
        or number > MAX_PERMISSION_WAIT_SECONDS
    ):
        raise BridgeError(
            "skill_configuration_invalid",
            "{} must be a finite {} number no greater than {} seconds or null.".format(
                name,
                "non-negative" if allow_zero else "positive",
                MAX_PERMISSION_WAIT_SECONDS,
            ),
        )
    return number


def _normalize_permission_wait_policy(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise BridgeError("skill_configuration_invalid", "permissionWaitPolicy must be a JSON object.")
    allowed = {"residentTimeoutSeconds", "subPipelineTimeoutSeconds", "timeoutGraceSeconds"}
    unknown = sorted(str(key) for key in value if key not in allowed)
    if unknown:
        raise BridgeError(
            "skill_configuration_invalid",
            "Unknown permissionWaitPolicy fields: {}.".format(", ".join(unknown)),
        )

    def optional_timeout(name):
        raw = value.get(name)
        return None if raw is None else _permission_wait_number(raw, "permissionWaitPolicy." + name, False)

    grace = value.get("timeoutGraceSeconds", 30)
    if grace is None:
        raise BridgeError(
            "skill_configuration_invalid",
            "permissionWaitPolicy.timeoutGraceSeconds must be a finite non-negative number.",
        )
    return {
        "residentTimeoutSeconds": optional_timeout("residentTimeoutSeconds"),
        "subPipelineTimeoutSeconds": optional_timeout("subPipelineTimeoutSeconds"),
        "timeoutGraceSeconds": _permission_wait_number(
            grace,
            "permissionWaitPolicy.timeoutGraceSeconds",
            True,
        ),
    }


def _skill_config():
    config_path = SKILL_ROOT / "config.json"
    try:
        encoded = config_path.read_bytes()
    except FileNotFoundError:
        return {"channel": None, "permissionWaitPolicy": None}
    except OSError as exc:
        raise BridgeError("skill_configuration_invalid", "The installed Skill config could not be read.") from exc
    if len(encoded) > MAX_SKILL_CONFIG_BYTES:
        raise BridgeError("skill_configuration_invalid", "The installed Skill config is too large.")
    try:
        config = json.loads(encoded.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BridgeError("skill_configuration_invalid", "The installed Skill config is not valid UTF-8 JSON.") from exc
    if not isinstance(config, dict):
        raise BridgeError("skill_configuration_invalid", "The installed Skill config must be a JSON object.")
    unknown = sorted(str(key) for key in config if key not in {"channel", "permissionWaitPolicy"})
    if unknown:
        raise BridgeError(
            "skill_configuration_invalid",
            "Unknown installed Skill config fields: {}.".format(", ".join(unknown)),
        )
    return {
        "channel": _normalize_telemetry_channel(config.get("channel")) if config.get("channel") is not None else None,
        "permissionWaitPolicy": _normalize_permission_wait_policy(config.get("permissionWaitPolicy")),
    }


def _skill_telemetry_channel():
    return _skill_config()["channel"]


def _identity_result(job_id, job, cursor, worker_pid):
    return {
        "ok": True,
        "jobId": job_id,
        "taskId": job["taskId"],
        "contextId": job["contextId"],
        "cursor": cursor,
        "state": job.get("state", "working"),
        "turn": int(job.get("turn") or 1),
        "workerPid": worker_pid,
        "preferredLanguage": job.get("preferredLanguage", "en"),
    }


def _wait_for_task_identity(job_id, previous_task_id, cursor, worker_pid):
    _root, job_path, _spool = _job_paths(job_id)
    deadline = time.monotonic() + WORKER_IDENTITY_TIMEOUT
    while time.monotonic() < deadline:
        current = _load_json(job_path)
        task_id = current.get("taskId")
        if (
            isinstance(task_id, str)
            and task_id
            and task_id != previous_task_id
            and isinstance(current.get("contextId"), str)
            and current["contextId"]
        ):
            return _identity_result(job_id, current, cursor, worker_pid)
        if not _pid_alive(worker_pid):
            break
        time.sleep(0.05)
    raise BridgeError("a2a_transport_failed", "The A2A task identity was not received in time.", True)


def _follow_after_command(args, result):
    if not getattr(args, "follow", False):
        return result
    followed = follow_job(
        argparse.Namespace(
            job_id=result["jobId"],
            cursor=result["cursor"],
            wait_seconds=getattr(args, "follow_seconds", DEFAULT_FOLLOW_SECONDS),
        )
    )
    followed["workerPid"] = result.get("workerPid")
    return _bounded_result(followed, MAX_FOLLOW_BYTES, preserve_final=True)


def start_job(args):
    workspace = pathlib.Path(args.cwd).expanduser()
    if not workspace.is_absolute() or not workspace.exists() or not workspace.is_dir():
        raise BridgeError("runtime_identity_mismatch", "The Skill workspace must be an existing absolute directory.")
    workspace = workspace.resolve()
    if args.mode == "pipeline" and not args.pipeline_name:
        raise BridgeError("runtime_identity_mismatch", "Pipeline mode requires --pipeline-name.")
    if args.mode == "normal" and args.pipeline_name:
        raise BridgeError("runtime_identity_mismatch", "Normal mode cannot use a Pipeline name.")
    prompt = _read_workspace_prompt(workspace, args.prompt_file)
    preferred_language = _preferred_language(prompt, args.language)
    _set_output_language(preferred_language)
    skill_config = _skill_config()
    channel = skill_config["channel"]
    permission_wait_policy = skill_config["permissionWaitPolicy"]
    artifact, executable, cache_hit = ensure_runtime()
    _progress("start", "Starting or reusing the local A2A runtime")
    record = ensure_server(
        executable,
        artifact,
        args.mode,
        args.pipeline_name,
        permission_wait_policy,
    )
    readiness = _runtime_configuration_readiness(
        record,
        require_cloud=args.mode == "pipeline" and args.pipeline_name == "selling",
    )
    job_id = uuid.uuid4().hex
    root, job_path, spool = _job_paths(job_id)
    _secure_directory(root)
    spool.touch()
    if os.name != "nt":
        os.chmod(str(spool), 0o600)
    runtime_record = _runtime_record_path(
        args.mode,
        args.pipeline_name,
        artifact["target"],
        permission_wait_policy,
    )
    job = {
        "schemaVersion": 1,
        "jobId": job_id,
        "runtimeIdentityVersion": 2,
        "runtimeTag": RUNTIME_TAG,
        "runtimeGeneration": record["generation"],
        "target": artifact["target"],
        "mode": args.mode,
        "conversationMode": args.mode,
        "pipelineName": args.pipeline_name or "",
        "workspace": str(workspace),
        "preferredLanguage": preferred_language,
        "runtimeRecord": str(runtime_record),
        "state": "submitted",
        "cursor": 0,
        "turn": 1,
        "taskHistory": [],
        "turnArtifacts": [],
        "createdAt": int(time.time()),
        "turnStartedAt": int(time.time()),
    }
    if channel is not None:
        job["channel"] = channel
    if permission_wait_policy is not None:
        job["permissionWaitPolicy"] = permission_wait_policy
    _atomic_json(job_path, job)
    payload = _worker_payload(job, prompt=prompt)
    worker_pid = _spawn_worker(job_id, payload)
    result = _wait_for_task_identity(job_id, None, 0, worker_pid)
    result["runtimeCacheHit"] = cache_hit
    followed = _follow_after_command(args, result)
    followed["runtimeCacheHit"] = cache_hit
    followed["configurationReadiness"] = readiness
    return _bounded_result(followed, MAX_FOLLOW_BYTES, preserve_final=True)


def _ensure_job_runtime(job_id):
    root, job_path, _spool = _job_paths(job_id)
    job = _load_json(job_path)
    _set_output_language(job.get("preferredLanguage"))
    if job.get("runtimeIdentityVersion") != 2 or job.get("runtimeTag") != RUNTIME_TAG:
        return job, _runtime_record_for_job(job)
    try:
        return job, _runtime_record_for_job(job)
    except BridgeError as exc:
        if exc.code != "runtime_identity_mismatch":
            raise

    mode = job.get("mode")
    pipeline_name = job.get("pipelineName")
    target = job.get("target")
    workspace = job.get("workspace")
    if (
        mode not in {"normal", "pipeline"}
        or not isinstance(pipeline_name, str)
        or (mode == "pipeline") != bool(pipeline_name)
        or not isinstance(target, str)
        or not target
        or not isinstance(workspace, str)
        or not workspace
    ):
        raise BridgeError("runtime_identity_mismatch", "The Skill job runtime identity is incomplete.")

    artifact, executable, _cache_hit = ensure_runtime()
    if artifact.get("target") != target:
        raise BridgeError("runtime_identity_mismatch", "The Skill job Runtime target is no longer available.")
    _progress("start", "Starting or reusing the local A2A runtime")
    permission_wait_policy = job.get("permissionWaitPolicy")
    record = ensure_server(executable, artifact, mode, pipeline_name, permission_wait_policy)
    runtime_record = _runtime_record_path(mode, pipeline_name, target, permission_wait_policy)
    with InstallLock(root / ".job.lock", timeout=10):
        current = _load_json(job_path)
        immutable = (
            "runtimeIdentityVersion",
            "runtimeTag",
            "target",
            "mode",
            "pipelineName",
            "workspace",
            "permissionWaitPolicy",
        )
        if any(current.get(key) != job.get(key) for key in immutable):
            raise BridgeError("runtime_identity_mismatch", "The Skill job runtime identity changed during recovery.")
        current["runtimeGeneration"] = record["generation"]
        current["runtimeRecord"] = str(runtime_record)
        _atomic_json(job_path, current)
    return current, record


def _read_spool(spool):
    if not spool.exists():
        return []
    values = []
    with spool.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                values.append(value)
    return values


def _bounded_result(result, maximum, preserve_final):
    while len(_json_bytes(result)) > maximum:
        if result.get("milestones"):
            result["milestones"].pop(0)
        elif result.get("artifacts") and len(result["artifacts"]) > 1:
            result["artifacts"].pop(0)
        elif result.get("artifacts") and result.get("pipelineResult"):
            result["artifacts"].pop(0)
        elif result.get("latestText"):
            result["latestText"] = _truncate_utf8(
                result["latestText"], max(0, len(result["latestText"].encode("utf-8")) // 2)
            )
        elif result.get("heartbeat"):
            result.pop("heartbeat", None)
        elif result.get("finalText") and not preserve_final:
            current_size = len(result["finalText"].encode("utf-8"))
            if current_size <= 120:
                result.pop("finalText", None)
            else:
                result["finalText"] = _truncate_utf8(result["finalText"], max(120, current_size // 2))
            result["finalTextTruncatedForPoll"] = True
        elif result.get("folded"):
            result["folded"] = {}
        else:
            raise BridgeError("a2a_transport_failed", "The bounded Skill result exceeded its protocol limit.")
    return result


def _job_result(
    job_id,
    cursor,
    maximum,
    preserve_final,
    include_heartbeat=True,
    end_cursor=None,
    boundary_reached=False,
):
    _root, job_path, spool = _job_paths(job_id)
    values = _read_spool(spool)
    start = max(0, cursor)
    end = len(values) if end_cursor is None else min(len(values), max(start, int(end_cursor)))
    unseen = values[start:end]
    milestones = []
    latest_text = ""
    folded = {}
    last_milestone_signature = None
    job = _load_json(job_path)
    _set_output_language(job.get("preferredLanguage"))
    state = "working" if boundary_reached else job.get("state", "unknown")
    current_task_id = job.get("taskId")
    for item in unseen:
        item_task_id = item.get("taskId")
        if isinstance(current_task_id, str) and isinstance(item_task_id, str) and item_task_id != current_task_id:
            folded["stale_task_event"] = folded.get("stale_task_event", 0) + 1
            continue
        if isinstance(item.get("text"), str):
            latest_text = item["text"]
        if isinstance(item.get("milestones"), list):
            for milestone in item["milestones"]:
                if isinstance(milestone, dict):
                    signature = _json_bytes(milestone)
                    if signature == last_milestone_signature:
                        folded["duplicate_milestone"] = folded.get("duplicate_milestone", 0) + 1
                        continue
                    milestones.append(milestone)
                    last_milestone_signature = signature
        category = item.get("category")
        if isinstance(category, str):
            folded[category] = folded.get(category, 0) + int(item.get("count") or 1)
    result = {
        "ok": True,
        "jobId": job_id,
        "state": state,
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "cursor": end,
        "turn": int(job.get("turn") or 1),
        "milestones": milestones[-MAX_POLL_EVENTS:],
        "latestText": latest_text,
        "folded": folded,
        "artifacts": _deduplicated_artifacts(list(job.get("turnArtifacts") or []))[-MAX_POLL_EVENTS:],
    }
    if boundary_reached:
        result["boundaryReached"] = True
        user_updates = _step_boundary_user_updates(result["milestones"])
        if user_updates:
            result["presentationRequired"] = True
            result["userUpdates"] = user_updates
    for key in ("taskId", "contextId"):
        if isinstance(job.get(key), str):
            result[key] = job[key]
    if job.get("conversationMode") in {"normal", "pipeline"}:
        result["conversationMode"] = job["conversationMode"]
    if not boundary_reached and isinstance(job.get("cleanup"), dict):
        result["cleanup"] = job["cleanup"]
    if not boundary_reached and isinstance(job.get("inputRequired"), dict):
        result["inputRequired"] = job["inputRequired"]
    if not boundary_reached and state == TURN_COMPLETED_STATE:
        result["finalText"] = job.get("finalText", "")
        result["finalTextComplete"] = job.get("finalTextComplete") is True
        result["artifacts"] = list(job.get("finalArtifacts") or [])[-MAX_POLL_EVENTS:]
        result.pop("latestText", None)
    cleanup_status = job.get("cleanup", {}).get("status") if isinstance(job.get("cleanup"), dict) else None
    if (
        not boundary_reached
        and isinstance(job.get("pipelineResult"), dict)
        and cleanup_status not in CLEANUP_PENDING_STATES
        and ((job.get("mode") == "pipeline" and state in TERMINAL_STATES) or cleanup_status in CLEANUP_TERMINAL_STATES)
    ):
        result["pipelineResult"] = job["pipelineResult"]
        result.pop("latestText", None)
    if (
        include_heartbeat
        and not unseen
        and state not in TERMINAL_STATES
        and state not in INPUT_STATES | {TURN_COMPLETED_STATE}
    ):
        elapsed = max(0, int(time.time()) - int(job.get("turnStartedAt", job.get("createdAt", time.time()))))
        result["heartbeat"] = (
            "iac-code \u4ecd\u5728\u5904\u7406\u4e2d\uff08{} \u79d2\uff09\u3002".format(elapsed)
            if _ACTIVE_LANGUAGE == "zh"
            else "iac-code is still working ({}s).".format(elapsed)
        )
    return _bounded_result(result, maximum, preserve_final)


def poll_job(args):
    _root, _job_path, spool = _job_paths(args.job_id)
    deadline = time.monotonic() + max(0.0, min(args.wait_seconds, 30.0))
    while True:
        values = _read_spool(spool)
        if len(values) > args.cursor or time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    return _job_result(args.job_id, args.cursor, MAX_POLL_BYTES, preserve_final=False)


def _step_display_name(step_id):
    names = {
        "zh": {
            "intent_parsing": "理解部署需求",
            "architecture_planning": "设计候选架构",
            "evaluate_candidates": "生成并评估候选方案",
            "confirm_and_select": "展示并确认方案",
            "deploying": "部署选定方案",
            "template_generating": "生成 IaC 模板",
            "reviewing": "审查 IaC 模板",
            "cost_estimating": "估算方案成本",
        },
        "en": {
            "intent_parsing": "understand deployment requirements",
            "architecture_planning": "design candidate architectures",
            "evaluate_candidates": "generate and evaluate candidate plans",
            "confirm_and_select": "present and confirm a plan",
            "deploying": "deploy the selected plan",
            "template_generating": "generate the IaC template",
            "reviewing": "review the IaC template",
            "cost_estimating": "estimate plan cost",
        },
    }
    language_names = names.get(_ACTIVE_LANGUAGE, names["en"])
    if step_id in language_names:
        return language_names[step_id]
    return str(step_id or "step").replace("_", " ").replace("-", " ")


def _step_progress_detail(milestone):
    event_type = milestone.get("eventType")
    coordinate = milestone.get("candidateStep") if str(event_type).startswith("candidate_step_") else None
    if not isinstance(coordinate, dict):
        coordinate = milestone.get("step")
    if not isinstance(coordinate, dict):
        coordinate = milestone.get("parentStep")
    coordinate = coordinate if isinstance(coordinate, dict) else {}
    step_id = coordinate.get("id") or coordinate.get("name")
    detail = _step_display_name(step_id) if step_id else ""
    index = coordinate.get("index")
    total = coordinate.get("total")
    if isinstance(index, int):
        position = "{}/{}".format(index, total) if isinstance(total, int) else str(index)
        detail = "{} {}".format(position, detail).strip()
    candidate = milestone.get("candidate")
    if str(event_type).startswith("candidate_step_") and isinstance(candidate, dict):
        candidate_name = _sanitize_text(candidate.get("name") or candidate.get("id"), 80)
        if candidate_name:
            separator = " · "
            detail = "{}{}{}".format(candidate_name, separator, detail) if detail else candidate_name
    message = _sanitize_text(milestone.get("message"), 160)
    if message and message not in {step_id, detail}:
        detail = "{} — {}".format(detail, message) if detail else message
    conclusion = _format_step_conclusion_summary(milestone.get("conclusionSummary"))
    if conclusion:
        separator = "；结论：" if _ACTIVE_LANGUAGE == "zh" else "; conclusion: "
        detail = "{}{}{}".format(detail, separator, conclusion) if detail else conclusion
    return detail


def _format_step_conclusion_summary(summary):
    if not isinstance(summary, dict):
        return ""
    requirement = _sanitize_text(summary.get("requirementSummary"), 180)
    region = _sanitize_text(summary.get("region"), 80)
    resources = summary.get("resources")
    resource_names = []
    if isinstance(resources, list):
        for resource in resources[:6]:
            if not isinstance(resource, dict):
                continue
            product = _sanitize_text(resource.get("product"), 60)
            action = _sanitize_text(resource.get("action"), 32)
            if _ACTIVE_LANGUAGE == "zh":
                action = {
                    "create": "新建",
                    "use_existing": "复用",
                    "reference": "引用",
                    "forbid": "禁止",
                }.get(action, action)
            if product:
                resource_names.append("{} ({})".format(product, action) if action else product)
    candidates = summary.get("candidates")
    candidate_names = []
    if isinstance(candidates, list):
        for candidate in candidates[:4]:
            if not isinstance(candidate, dict):
                continue
            name = _sanitize_text(candidate.get("name"), 80)
            estimate = _sanitize_text(candidate.get("monthlyEstimate"), 80)
            if name:
                candidate_names.append("{} ({})".format(name, estimate) if estimate else name)

    parts = []
    if requirement:
        parts.append(requirement)
    if region:
        parts.append(("地域 " if _ACTIVE_LANGUAGE == "zh" else "region ") + region)
    if resource_names:
        parts.append(("资源 " if _ACTIVE_LANGUAGE == "zh" else "resources ") + "、".join(resource_names))
    if candidate_names:
        candidate_count = summary.get("candidateCount")
        prefix = (
            "{} 个候选方案 ".format(candidate_count)
            if _ACTIVE_LANGUAGE == "zh"
            else "{} candidates ".format(candidate_count)
        )
        parts.append(prefix + "、".join(candidate_names))
    separator = "；" if _ACTIVE_LANGUAGE == "zh" else "; "
    return _sanitize_text(separator.join(parts), 520)


def _progress_signature(milestone):
    event_type = _sanitize_text(milestone.get("eventType"), 80) or "progress"
    values = [event_type]
    for key in ("sequence", "toolUseId"):
        value = milestone.get(key)
        if isinstance(value, (str, int)):
            values.append(str(value))
    for key in ("step", "parentStep", "candidate", "candidateStep"):
        coordinate = milestone.get(key)
        if isinstance(coordinate, dict):
            values.append("{}:{}:{}".format(key, coordinate.get("id", ""), coordinate.get("index", "")))
    return "|".join(values)


def _format_progress_milestone(milestone):
    event_type = _sanitize_text(milestone.get("eventType"), 80)
    if event_type in STEP_BOUNDARY_EVENT_TYPES:
        detail = _step_progress_detail(milestone)
    else:
        detail = (
            _sanitize_text(milestone.get("message"), 220)
            or _sanitize_text(milestone.get("toolName"), 100)
            or _sanitize_text(milestone.get("status"), 80)
        )
    if _ACTIVE_LANGUAGE == "zh":
        event_labels = {
            "pipeline_started": "Pipeline 已开始",
            "pipeline_resumed": "Pipeline 已恢复",
            "step_started": "步骤开始",
            "step_completed": "步骤完成",
            "step_failed": "步骤失败",
            "candidate_started": "候选方案已开始",
            "candidate_step_started": "候选步骤开始",
            "candidate_step_completed": "候选步骤完成",
            "candidate_step_failed": "候选步骤失败",
            "candidate_completed": "候选方案已完成",
            "candidate_selected": "候选方案已选择",
            "tool_started": "工具已开始",
            "tool_completed": "工具已完成",
            "tool_result": "工具已返回结果",
            "artifact_created": "产物已生成",
            "pipeline_completed": "Pipeline 已完成",
            "pipeline_failed": "Pipeline 失败",
            "pipeline_canceled": "Pipeline 已取消",
            "input_required": "需要用户输入",
            "permission_requested": "需要权限确认",
            "permission_resolved": "权限确认已处理",
            "cleanup_started": "回滚资源清理已开始",
            "cleanup_progress": "回滚资源清理中",
            "cleanup_completed": "回滚资源清理完成",
            "cleanup_failed": "回滚资源清理失败",
        }
        label = event_labels.get(event_type, event_type or "进度")
        message = "{}{}".format(label, "：" + detail if detail else "")
    else:
        labels = {
            "step_started": "Step started",
            "step_completed": "Step completed",
            "step_failed": "Step failed",
            "candidate_step_started": "Candidate step started",
            "candidate_step_completed": "Candidate step completed",
            "candidate_step_failed": "Candidate step failed",
            "cleanup_started": "Rollback cleanup started",
            "cleanup_progress": "Rollback cleanup in progress",
            "cleanup_completed": "Rollback cleanup completed",
            "cleanup_failed": "Rollback cleanup failed",
        }
        label = labels.get(event_type, event_type or "progress")
        message = "{}{}".format(label, ": " + detail if detail else "")
    return _progress_signature(milestone), message


def _step_boundary_user_updates(milestones):
    if not isinstance(milestones, list):
        return []
    updates = []
    seen = set()
    for milestone in milestones:
        if not isinstance(milestone, dict) or milestone.get("eventType") not in STEP_BOUNDARY_EVENT_TYPES:
            continue
        signature, message = _format_progress_milestone(milestone)
        if signature in seen or not message:
            continue
        updates.append(_sanitize_text(message, MAX_USER_UPDATE_TEXT))
        seen.add(signature)
    return updates


def _follow_progress_messages(item):
    milestones = item.get("milestones")
    if isinstance(milestones, list) and milestones:
        boundary_messages = []
        latest_other = None
        for milestone in milestones:
            if not isinstance(milestone, dict):
                continue
            formatted = _format_progress_milestone(milestone)
            if milestone.get("eventType") in PROGRESS_BOUNDARY_EVENT_TYPES:
                boundary_messages.append(formatted)
            else:
                latest_other = formatted
        if latest_other is not None:
            boundary_messages.append(latest_other)
        if boundary_messages:
            return boundary_messages
    state = item.get("state")
    if isinstance(state, str) and state not in {"submitted", "working", "input-required"}:
        state_text = _sanitize_text(state, 80)
        message = "iac-code 状态：" + state_text if _ACTIVE_LANGUAGE == "zh" else "iac-code state: " + state_text
        return [("state:" + state, message)]
    return []


def _follow_progress_message(item):
    messages = _follow_progress_messages(item)
    return messages[-1] if messages else (None, None)


def _has_step_boundary(item):
    milestones = item.get("milestones")
    return isinstance(milestones, list) and any(
        isinstance(milestone, dict) and milestone.get("eventType") in STEP_BOUNDARY_EVENT_TYPES
        for milestone in milestones
    )


def _bounded_follow_seconds(value):
    seconds = float(value)
    if seconds != seconds:
        return 0.0
    return max(0.0, min(seconds, MAX_FOLLOW_SECONDS))


def _follow_job_once(args):
    root, job_path, spool = _job_paths(args.job_id)
    initial_job = _load_json(job_path)
    _set_output_language(initial_job.get("preferredLanguage"))
    wait_seconds = _bounded_follow_seconds(args.wait_seconds)
    started_at = time.monotonic()
    deadline = started_at + wait_seconds
    shared_deadline = getattr(args, "follow_deadline", None)
    if isinstance(shared_deadline, (int, float)):
        deadline = min(deadline, float(shared_deadline))
    cursor = max(0, int(args.cursor))
    progress_lines = 0
    progress_bytes = 0
    seen_progress_signatures = set()
    last_heartbeat = started_at
    boundary = False
    progress_boundary_cursor = None

    def emit(signature, message):
        nonlocal progress_lines, progress_bytes
        if not message or signature in seen_progress_signatures:
            return
        message = _localized_progress_text(message)
        encoded = _progress_bytes("follow", message)
        if progress_lines >= MAX_FOLLOW_PROGRESS_LINES or progress_bytes + len(encoded) > MAX_FOLLOW_PROGRESS_BYTES:
            return
        _progress("follow", message)
        progress_lines += 1
        progress_bytes += len(encoded)
        seen_progress_signatures.add(signature)

    _secure_directory(root)
    spool.touch(exist_ok=True)
    with spool.open("r", encoding="utf-8") as handle:
        consumed = 0
        while consumed < cursor and handle.readline():
            consumed += 1
        cursor = consumed
        while True:
            line = handle.readline()
            if line:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(item, dict):
                    continue
                cursor += 1
                job = _load_json(job_path)
                current_task_id = job.get("taskId")
                item_task_id = item.get("taskId")
                if (
                    isinstance(current_task_id, str)
                    and isinstance(item_task_id, str)
                    and item_task_id != current_task_id
                ):
                    continue
                for signature, message in _follow_progress_messages(item):
                    emit(signature, message)
                if _has_step_boundary(item):
                    progress_boundary_cursor = cursor
                    boundary = True
                    break
                continue

            job = _load_json(job_path)
            state = job.get("state")
            if state in TERMINAL_STATES or state == TURN_COMPLETED_STATE or isinstance(job.get("inputRequired"), dict):
                boundary = True
                break
            now = time.monotonic()
            if now >= deadline:
                break
            if now - last_heartbeat >= FOLLOW_HEARTBEAT_SECONDS:
                elapsed = max(0, int(time.time()) - int(job.get("turnStartedAt", job.get("createdAt", time.time()))))
                emit(
                    "heartbeat:{}".format(elapsed // int(FOLLOW_HEARTBEAT_SECONDS)),
                    (
                        "iac-code 仍在处理中（{} 秒）。".format(elapsed)
                        if _ACTIVE_LANGUAGE == "zh"
                        else "iac-code is still working ({}s).".format(elapsed)
                    ),
                )
                last_heartbeat = now
            time.sleep(0.1)

    if boundary:
        with InstallLock(root / ".job.lock", timeout=10):
            pass
    result = _job_result(
        args.job_id,
        args.cursor,
        MAX_FOLLOW_BYTES,
        preserve_final=True,
        include_heartbeat=False,
        end_cursor=progress_boundary_cursor,
        boundary_reached=progress_boundary_cursor is not None,
    )
    if not boundary:
        result["followTimedOut"] = True
    result["progressLines"] = progress_lines
    result["progressBytes"] = progress_bytes
    return _bounded_result(result, MAX_FOLLOW_BYTES, preserve_final=True)


def _cleanup_is_pending(job):
    cleanup = job.get("cleanup")
    return isinstance(cleanup, dict) and cleanup.get("status") in CLEANUP_PENDING_STATES


def _start_cleanup_only_task(job_id):
    root, job_path, spool = _job_paths(job_id)
    job, _record = _ensure_job_runtime(job_id)
    cursor = len(_read_spool(spool))
    with InstallLock(root / ".job.lock", timeout=10):
        current = _load_json(job_path)
        if not _cleanup_is_pending(current) or isinstance(current.get("inputRequired"), dict):
            return None
        previous_task_id = current.get("taskId")
        if not isinstance(previous_task_id, str) or not previous_task_id:
            raise BridgeError("runtime_identity_mismatch", "The cleanup handoff has no prior A2A task identity.")
        if "pipelineTerminalState" not in current:
            if current.get("state") not in TERMINAL_STATES:
                raise BridgeError(
                    "runtime_identity_mismatch",
                    "The cleanup handoff is not at a Pipeline terminal state.",
                )
            current["pipelineTerminalState"] = current["state"]
            current["pipelineArtifacts"] = list(current.get("turnArtifacts") or [])
        history = current.setdefault("taskHistory", [])
        if previous_task_id not in history:
            history.append(previous_task_id)
        current["state"] = "submitted"
        current["conversationMode"] = "normal"
        current["cleanupOnlyActive"] = True
        current["cleanupAttempts"] = int(current.get("cleanupAttempts") or 0) + 1
        current["turnStartedAt"] = int(time.time())
        current["turnArtifacts"] = []
        current.pop("taskId", None)
        current.pop("inputRequired", None)
        current.pop("pendingPermissions", None)
        current.pop("finalText", None)
        current.pop("finalTextComplete", None)
        current.pop("finalArtifacts", None)
        current.pop("turnCompletedAt", None)
        _atomic_json(job_path, current)
    payload = _worker_payload(current, prompt="continue", cleanup_only=True)
    worker_pid = _spawn_worker(job_id, payload)
    _progress(
        "cleanup",
        "正在清理 Pipeline 回滚残留资源" if _ACTIVE_LANGUAGE == "zh" else "Cleaning up Pipeline rollback resources",
    )
    return _wait_for_task_identity(job_id, previous_task_id, cursor, worker_pid)


def _finish_cleanup_only_task(job_id):
    root, job_path, _spool = _job_paths(job_id)
    with InstallLock(root / ".job.lock", timeout=10):
        job = _load_json(job_path)
        cleanup = job.get("cleanup")
        cleanup_status = cleanup.get("status") if isinstance(cleanup, dict) else None
        if cleanup_status not in CLEANUP_TERMINAL_STATES:
            return False
        terminal_state = job.get("pipelineTerminalState")
        if terminal_state not in TERMINAL_STATES:
            terminal_state = "completed"
        job["state"] = terminal_state
        job["turnArtifacts"] = list(job.get("pipelineArtifacts") or [])
        job["cleanupOnlyActive"] = False
        job.pop("finalText", None)
        job.pop("finalTextComplete", None)
        job.pop("finalArtifacts", None)
        job.pop("turnCompletedAt", None)
        _atomic_json(job_path, job)
    return True


def _mark_cleanup_follow_up_required(job_id):
    root, job_path, _spool = _job_paths(job_id)
    with InstallLock(root / ".job.lock", timeout=10):
        job = _load_json(job_path)
        if _cleanup_is_pending(job) and not isinstance(job.get("inputRequired"), dict):
            job["state"] = "cleanup_pending"
            job.pop("finalText", None)
            job.pop("finalTextComplete", None)
            job.pop("finalArtifacts", None)
            job.pop("turnCompletedAt", None)
            _atomic_json(job_path, job)


def _advance_pipeline_cleanup(args, result):
    follow_deadline = getattr(args, "follow_deadline", None)
    if not isinstance(follow_deadline, (int, float)):
        follow_deadline = time.monotonic() + _bounded_follow_seconds(
            getattr(args, "wait_seconds", DEFAULT_FOLLOW_SECONDS)
        )
    for _attempt in range(MAX_AUTO_CLEANUP_TASKS_PER_FOLLOW):
        job = _load_json(_job_paths(args.job_id)[1])
        if isinstance(job.get("inputRequired"), dict):
            return result
        cleanup = job.get("cleanup")
        cleanup_status = cleanup.get("status") if isinstance(cleanup, dict) else None
        if cleanup_status in CLEANUP_TERMINAL_STATES:
            if job.get("cleanupOnlyActive") is True:
                _finish_cleanup_only_task(args.job_id)
                return _job_result(args.job_id, args.cursor, MAX_FOLLOW_BYTES, preserve_final=True)
            return result
        if not _cleanup_is_pending(job):
            return result
        if job.get("state") not in TERMINAL_STATES | {TURN_COMPLETED_STATE, "cleanup_pending"}:
            return result
        identity = _start_cleanup_only_task(args.job_id)
        if identity is None:
            return result
        result = _follow_job_once(
            argparse.Namespace(
                job_id=args.job_id,
                cursor=identity["cursor"],
                wait_seconds=getattr(args, "wait_seconds", DEFAULT_FOLLOW_SECONDS),
                follow_deadline=follow_deadline,
            )
        )
        if result.get("followTimedOut") or isinstance(result.get("inputRequired"), dict):
            return result
    _mark_cleanup_follow_up_required(args.job_id)
    pending = _job_result(args.job_id, args.cursor, MAX_FOLLOW_BYTES, preserve_final=True)
    pending["cleanupFollowUpRequired"] = True
    return _bounded_result(pending, MAX_FOLLOW_BYTES, preserve_final=True)


def follow_job(args):
    wait_seconds = getattr(args, "wait_seconds", DEFAULT_FOLLOW_SECONDS)
    follow_args = argparse.Namespace(
        job_id=args.job_id,
        cursor=args.cursor,
        wait_seconds=wait_seconds,
        follow_deadline=time.monotonic() + _bounded_follow_seconds(wait_seconds),
    )
    job = _load_json(_job_paths(args.job_id)[1])
    if (
        job.get("state") == "cleanup_pending"
        and _cleanup_is_pending(job)
        and not isinstance(job.get("inputRequired"), dict)
    ):
        identity = _start_cleanup_only_task(args.job_id)
        if identity is None:
            result = _job_result(args.job_id, args.cursor, MAX_FOLLOW_BYTES, preserve_final=True)
        else:
            result = _follow_job_once(
                argparse.Namespace(
                    job_id=args.job_id,
                    cursor=identity["cursor"],
                    wait_seconds=wait_seconds,
                    follow_deadline=follow_args.follow_deadline,
                )
            )
    else:
        result = _follow_job_once(follow_args)
    return _advance_pipeline_cleanup(follow_args, result)


def respond_job(args):
    root, job_path, spool = _job_paths(args.job_id)
    job, record = _ensure_job_runtime(args.job_id)
    pending = job.get("inputRequired")
    if not isinstance(pending, dict):
        raise BridgeError("input_response_mismatch", "The Skill job is not waiting for input.")
    input_file = getattr(args, "input_file", None)
    inline_decision = getattr(args, "decision", None)
    if input_file:
        if any(getattr(args, key, None) for key in ("input_id", "tool_use_id", "decision")):
            raise BridgeError(
                "input_response_mismatch",
                "Use either an input file or an inline permission decision, not both.",
            )
        response = _load_json(pathlib.Path(input_file).resolve(), "input_response_mismatch")
    else:
        if pending.get("kind") != "permission":
            raise BridgeError(
                "input_response_mismatch",
                "Questions and candidate selections still require an input file.",
            )
        input_id = getattr(args, "input_id", None)
        tool_use_id = getattr(args, "tool_use_id", None)
        if not all(isinstance(value, str) and value for value in (input_id, tool_use_id, inline_decision)):
            raise BridgeError(
                "input_response_mismatch",
                "An inline permission response requires input-id, tool-use-id, and decision.",
            )
        response = {
            "kind": "permission",
            "requestTaskId": pending.get("requestTaskId"),
            "contextId": pending.get("contextId"),
            "inputId": input_id,
            "toolUseId": tool_use_id,
            "decision": inline_decision,
        }
    _validate_response_correlation(response, pending)
    payload = _worker_payload(job, response=response)
    cursor = len(_read_spool(spool))
    if payload.get("method") == "SendMessage":
        ack_frame = _http_json(
            "http://127.0.0.1:{}/".format(record["port"]),
            record["token"],
            method="POST",
            payload=payload,
            timeout=30,
        )
        ack = _validate_permission_ack(ack_frame, response)
        with InstallLock(root / ".job.lock", timeout=10):
            current = _load_json(job_path)
            _remove_job_pending_permission(current, response.get("inputId"))
            if current.get("state") not in INPUT_STATES | TERMINAL_STATES | {TURN_COMPLETED_STATE}:
                current["state"] = "working"
            _atomic_json(job_path, current)
        result = {
            "ok": True,
            "jobId": args.job_id,
            "state": current.get("state", "working"),
            "preferredLanguage": job.get("preferredLanguage", "en"),
            "cursor": cursor,
            "taskId": job.get("taskId"),
            "contextId": job.get("contextId"),
            "turn": int(job.get("turn") or 1),
            "permissionAck": ack,
        }
        return _follow_after_command(args, result)
    with InstallLock(root / ".job.lock", timeout=10):
        current = _load_json(job_path)
        if current.get("inputRequired") != pending:
            raise BridgeError("input_response_mismatch", "The pending input changed before the response was sent.")
        current["state"] = "working"
        current.pop("inputRequired", None)
        _atomic_json(job_path, current)
    worker_pid = _spawn_worker(args.job_id, payload)
    result = {
        "ok": True,
        "jobId": args.job_id,
        "state": "working",
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "cursor": cursor,
        "taskId": job.get("taskId"),
        "contextId": job.get("contextId"),
        "turn": int(job.get("turn") or 1),
        "workerPid": worker_pid,
    }
    return _follow_after_command(args, result)


def continue_job(args):
    root, job_path, spool = _job_paths(args.job_id)
    job, record = _ensure_job_runtime(args.job_id)
    if not _job_uses_normal_conversation(job):
        raise BridgeError(
            "input_response_mismatch",
            "Only a normal conversation or a completed Pipeline handoff can continue with a new turn.",
        )
    pipeline_handoff = (
        job.get("mode") == "pipeline"
        and job.get("state") in TERMINAL_STATES
        and (
            job.get("normalHandoffReady") is True
            or (job.get("state") == "completed" and job.get("pipelineName") in PIPELINE_NORMAL_HANDOFFS)
        )
    )
    expected_state = job.get("state")
    if (job.get("state") != TURN_COMPLETED_STATE and not pipeline_handoff) or isinstance(
        job.get("inputRequired"), dict
    ):
        raise BridgeError("input_response_mismatch", "The Skill conversation has not completed its current turn.")
    context_id = job.get("contextId")
    previous_task_id = job.get("taskId")
    if not isinstance(context_id, str) or not context_id or not isinstance(previous_task_id, str):
        raise BridgeError("runtime_identity_mismatch", "The Skill conversation context is incomplete.")
    workspace = pathlib.Path(job["workspace"]).resolve()
    prompt = _read_workspace_prompt(workspace, args.prompt_file)
    readiness = _runtime_configuration_readiness(record, require_cloud=False)
    payload = _worker_payload(job, prompt=prompt)
    cursor = len(_read_spool(spool))
    with InstallLock(root / ".job.lock", timeout=10):
        current = _load_json(job_path)
        if (
            current.get("state") != expected_state
            or current.get("contextId") != context_id
            or current.get("taskId") != previous_task_id
            or not _job_uses_normal_conversation(current)
        ):
            raise BridgeError("input_response_mismatch", "The Skill conversation changed before the next turn started.")
        history = current.setdefault("taskHistory", [])
        if previous_task_id not in history:
            history.append(previous_task_id)
        current["turn"] = int(current.get("turn") or 1) + 1
        current["state"] = "submitted"
        current["conversationMode"] = "normal"
        current["turnArtifacts"] = []
        current["turnStartedAt"] = int(time.time())
        current.pop("taskId", None)
        current.pop("finalText", None)
        current.pop("finalTextComplete", None)
        current.pop("finalArtifacts", None)
        current.pop("turnCompletedAt", None)
        current.pop("pipelineResult", None)
        _atomic_json(job_path, current)
    worker_pid = _spawn_worker(args.job_id, payload)
    result = _wait_for_task_identity(args.job_id, previous_task_id, cursor, worker_pid)
    if result.get("contextId") != context_id:
        raise BridgeError("runtime_identity_mismatch", "The continued A2A task did not reuse the Skill job context.")
    followed = _follow_after_command(args, result)
    followed["configurationReadiness"] = readiness
    return _bounded_result(followed, MAX_FOLLOW_BYTES, preserve_final=True)


def cancel_job(args):
    _root, job_path, _spool = _job_paths(args.job_id)
    job, record = _ensure_job_runtime(args.job_id)
    task_id = job.get("taskId")
    if not isinstance(task_id, str):
        raise BridgeError("job_not_found", "The Skill job has no A2A task identity.")
    response = _http_json(
        "http://127.0.0.1:{}/".format(record["port"]),
        record["token"],
        method="POST",
        payload=_jsonrpc_payload("CancelTask", {"id": task_id}),
    )
    job["state"] = "canceled"
    job.pop("inputRequired", None)
    _atomic_json(job_path, job)
    return {
        "ok": True,
        "jobId": args.job_id,
        "state": "canceled",
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "a2a": bool(response.get("result")),
    }


def _parser():
    parser = argparse.ArgumentParser(prog="iac_code.py")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ensure-runtime")
    cache = commands.add_parser("cache")
    cache_commands = cache.add_subparsers(dest="cache_command", required=True)
    cache_commands.add_parser("list")
    cache_clean = cache_commands.add_parser("clean")
    cache_selection = cache_clean.add_mutually_exclusive_group(required=True)
    cache_selection.add_argument("--runtime-tag")
    cache_selection.add_argument("--candidates", action="store_true")
    cache_clean.add_argument("--confirm", action="store_true")
    start = commands.add_parser("start")
    start.add_argument("--mode", choices=("normal", "pipeline"), default="normal")
    start.add_argument("--pipeline-name", default="")
    start.add_argument("--cwd", required=True)
    start.add_argument("--prompt-file", required=True)
    start.add_argument("--language", choices=("auto",) + SUPPORTED_LANGUAGES, default="auto")
    start.add_argument("--follow", action="store_true")
    start.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)
    continue_parser = commands.add_parser("continue")
    continue_parser.add_argument("--job-id", required=True)
    continue_parser.add_argument("--prompt-file", required=True)
    continue_parser.add_argument("--follow", action="store_true")
    continue_parser.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)
    follow = commands.add_parser("follow")
    follow.add_argument("--job-id", required=True)
    follow.add_argument("--cursor", type=int, default=0)
    follow.add_argument("--wait-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)
    poll = commands.add_parser("poll")
    poll.add_argument("--job-id", required=True)
    poll.add_argument("--cursor", type=int, default=0)
    poll.add_argument("--wait-seconds", type=float, default=5.0)
    respond = commands.add_parser("respond")
    respond.add_argument("--job-id", required=True)
    respond.add_argument("--input-file")
    respond.add_argument("--input-id")
    respond.add_argument("--tool-use-id")
    respond.add_argument("--decision", choices=("allow_once", "deny"))
    respond.add_argument("--follow", action="store_true")
    respond.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)
    cancel = commands.add_parser("cancel")
    cancel.add_argument("--job-id", required=True)
    worker_parser = commands.add_parser("_worker", help=argparse.SUPPRESS)
    worker_parser.add_argument("--job-id", required=True)
    worker_parser.add_argument("--request", required=True)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "ensure-runtime":
            artifact, executable, cache_hit = ensure_runtime()
            result = {
                "ok": True,
                "skillVersion": SKILL_VERSION,
                "runtimeTag": RUNTIME_TAG,
                "target": artifact["target"],
                "runtime": str(executable),
                "cacheHit": cache_hit,
            }
        elif args.command == "cache":
            result = list_runtime_cache(args) if args.cache_command == "list" else clean_runtime_cache(args)
        elif args.command == "start":
            result = start_job(args)
        elif args.command == "continue":
            result = continue_job(args)
        elif args.command == "follow":
            result = follow_job(args)
        elif args.command == "poll":
            result = poll_job(args)
        elif args.command == "respond":
            result = respond_job(args)
        elif args.command == "cancel":
            result = cancel_job(args)
        else:
            return worker(args.job_id, args.request)
        _write_stdout(result)
        return 0
    except BridgeError as exc:
        if args.command == "_worker":
            with contextlib.suppress(Exception):
                _append_projection(
                    args.job_id,
                    {"type": "terminal", "state": "failed", "text": _sanitize_text(exc.message, 500)},
                )
        _write_stdout(exc.payload())
        return 2
    except Exception as exc:
        error = BridgeError("bridge_internal_error", _sanitize_text(str(exc), 500) or "The Skill bridge failed.")
        if args.command == "_worker":
            with contextlib.suppress(Exception):
                _append_projection(
                    args.job_id,
                    {"type": "terminal", "state": "failed", "text": error.message},
                )
        _write_stdout(error.payload())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
