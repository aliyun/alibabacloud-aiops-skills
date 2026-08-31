#!/usr/bin/env python3
"""Bounded Alibaba Cloud ROS Agent bridge using signed StartChat RPCs."""

import argparse
import contextlib
import errno
import hashlib
import importlib
import json
import os
import pathlib
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

MAX_PROMPT_BYTES = 1024 * 1024
MAX_CONTEXT_BYTES = 64 * 1024
MAX_CONFIG_BYTES = 16 * 1024
MAX_CLI_CONFIG_BYTES = 2 * 1024 * 1024
MAX_PLUGIN_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_SSE_LINE_BYTES = 16 * 1024 * 1024
MAX_SSE_EVENT_BYTES = 16 * 1024 * 1024
MAX_FINAL_TEXT_BYTES = 10 * 1024
MAX_DIAGNOSTIC_BYTES = 64 * 1024
MAX_RESULT_BYTES = 32 * 1024
MAX_SPOOL_BYTES = 8 * 1024 * 1024
MAX_PROJECTION_BYTES = 4096
MAX_INPUT_PROJECTION_BYTES = 14 * 1024
MAX_FOLLOW_BYTES = 16 * 1024
MAX_FOLLOW_EVENTS = 16
MAX_STEP_CONCLUSION_BYTES = 1800
MAX_MANAGER_REQUEST_BYTES = 2 * 1024 * 1024
DEFAULT_FOLLOW_SECONDS = 60.0
MAX_FOLLOW_SECONDS = 120.0
DEFAULT_READ_TIMEOUT_SECONDS = 1800
MANAGER_START_TIMEOUT_SECONDS = 10.0
STOP_SESSION_WAIT_SECONDS = 10.0
STOP_REQUEST_TIMEOUT_SECONDS = 60.0
MANAGER_IDLE_SECONDS = 60
MAX_MANAGER_IDLE_SECONDS = 24 * 60 * 60
MANAGER_SCHEMA_VERSION = 3
JOB_SCHEMA_VERSION = 1
STATE_DIR_ENV = "ALICLOUD_ROS_AGENT_STATE_DIR"
MAX_ATTACHMENTS = 5
DEFAULT_ENDPOINT = "ros.aliyuncs.com"
SUPPORTED_AGENT_MODES = {"normal", "pipeline"}
DEFAULT_TRANSPORT = "code"
SUPPORTED_TRANSPORTS = {"code", "aliyun_cli"}
DEFAULT_ALIYUN_CLI_EXECUTION_MODE = "local"
SUPPORTED_ALIYUN_CLI_EXECUTION_MODES = {"local", "remote"}
ROS_PLUGIN_COMMANDS = {"start-chat", "stop-chat"}
SKILL_DISTRIBUTION = "agenthub"
SKILL_NAME = "alibabacloud-ros-agent"
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/alibabacloud-ros-agent/{session-id}"
REQUIREMENTS_FILE = "scripts/requirements.txt"


def _skill_user_agent() -> str:
    if SKILL_DISTRIBUTION != "agenthub":
        return USER_AGENT_TEMPLATE
    value = os.environ.get("SKILL_SESSION_ID", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{32}", value) is None:
        value = uuid.uuid4().hex
        os.environ["SKILL_SESSION_ID"] = value
    return USER_AGENT_TEMPLATE.replace("{session-id}", value)


USER_AGENT = _skill_user_agent()
PROFILE_ENV_NAMES = (
    "ALIBABACLOUD_PROFILE",
    "ALIBABA_CLOUD_PROFILE",
    "ALICLOUD_PROFILE",
)
REGION_ENV_NAMES = (
    "ALIBABA_CLOUD_REGION_ID",
    "ALIBABACLOUD_REGION_ID",
    "ALICLOUD_REGION_ID",
    "REGION_ID",
    "REGION",
)
SKILL_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config.json"
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
PERMISSION_DECISIONS = {"allow_once", "deny"}
PERMISSION_QUERY_PREFIX = "IAC_CODE_PERMISSION:"
TERMINAL_STATES = {"completed", "failed", "canceled", "rejected"}
PIPELINE_EVENT_TYPES = {
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
    "input_required",
    "pipeline_completed",
    "pipeline_failed",
    "pipeline_canceled",
    "cleanup_started",
    "cleanup_progress",
    "cleanup_completed",
    "cleanup_failed",
}
STEP_BOUNDARY_EVENT_TYPES = {
    "step_started",
    "step_completed",
    "step_failed",
    "candidate_step_started",
    "candidate_step_completed",
    "candidate_step_failed",
}
SECRET_PATTERN = re.compile(
    r"(?i)((?:[\"']?)(?:access[-_ ]?key(?:[-_ ]?id|[-_ ]?secret)?|security[-_ ]?token|signature|"
    r"authorization)(?:[\"']?)\s*[:=]\s*(?:[\"']?)(?:bearer\s+)?)([^\"'\s,;&}]+)"
)
SENSITIVE_CLIENT_CONTEXT_KEY_PARTS = (
    "accesskey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "profile",
    "secret",
    "signature",
    "token",
)


class BridgeError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _resolve_user_owned_path(raw_path: str, code: str, label: str) -> pathlib.Path:
    """Resolve a local path and confine it to the user's home or temp tree."""

    expanded = os.path.expandvars(os.path.expanduser(raw_path))
    normalized = os.path.normcase(os.path.realpath(expanded))
    allowed_roots = (
        os.path.normcase(os.path.realpath(str(pathlib.Path.home()))),
        os.path.normcase(os.path.realpath(tempfile.gettempdir())),
    )
    for allowed_root in allowed_roots:
        prefix = allowed_root.rstrip(os.sep) + os.sep
        if normalized.startswith(prefix):
            return pathlib.Path(normalized)
    raise BridgeError(code, "{} must be inside the current user's home or temporary directory.".format(label))


def _state_root() -> pathlib.Path:
    configured = os.environ.get(STATE_DIR_ENV)
    if configured:
        return _resolve_user_owned_path(configured, "invalid_config", "The ROS Agent state directory")
    return pathlib.Path(os.path.expanduser("~/.cache/alicloud-ros-agent")).resolve()


def _secure_directory(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(str(path), 0o700)


def _atomic_json(path: pathlib.Path, value: Dict[str, Any], mode: int = 0o600) -> None:
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


def _load_state_json(path: pathlib.Path, code: str = "job_not_found") -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError) as exc:
        raise BridgeError(code, "Local ROS Agent bridge state is unavailable or invalid.") from exc
    if not isinstance(value, dict):
        raise BridgeError(code, "Local ROS Agent bridge state is unavailable or invalid.")
    return value


class StateLock(object):
    def __init__(self, path: pathlib.Path, timeout: float = 10.0) -> None:
        self.path = path
        self.timeout = timeout
        self.handle = None  # type: Any

    def __enter__(self) -> "StateLock":
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
                    raise BridgeError("state_locked", "Another ROS Agent bridge process is updating this state.", True)
                time.sleep(0.05)

    def __exit__(self, _type: Any, _value: Any, _traceback: Any) -> None:
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


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel32.WaitForSingleObject.restype = wintypes.DWORD
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(0x00100000, False, pid)
            if not handle:
                return False
            try:
                return kernel32.WaitForSingleObject(handle, 0) == 0x00000102
            finally:
                kernel32.CloseHandle(handle)
        except (AttributeError, OSError):
            return False
    try:
        waited, _status = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            return False
    except ChildProcessError:
        pass
    except OSError:
        pass
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _job_paths(job_id: str) -> Tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    try:
        canonical_job_id = uuid.UUID(job_id).hex
    except (AttributeError, ValueError) as exc:
        raise BridgeError("job_not_found", "The requested ROS Agent job does not exist.") from exc
    if canonical_job_id != job_id:
        raise BridgeError("job_not_found", "The requested ROS Agent job does not exist.")
    root = _state_root() / "jobs" / canonical_job_id
    return root, root / "job.json", root / "events.jsonl"


def _preferred_language(text: str) -> str:
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh"
    return "en"


def _endpoint_kind(endpoint: str, error_code: str = "invalid_input") -> str:
    if len(endpoint) <= 253 and endpoint.endswith(".aliyuncs.com"):
        labels = endpoint.split(".")
        if all(
            label
            and label.isascii()
            and len(label) <= 63
            and label[0].isalnum()
            and label[-1].isalnum()
            and all(character.isalnum() or character == "-" for character in label)
            for label in labels
        ):
            return "aliyun"
    host, separator, port_text = endpoint.rpartition(":")
    if separator and host in {"localhost", "127.0.0.1"} and port_text.isascii() and port_text.isdigit():
        port = int(port_text)
        if 1 <= port <= 65535:
            return "loopback"
    raise BridgeError(
        error_code,
        "The endpoint must be an aliyuncs.com hostname or a loopback host and port, without a URL scheme or path.",
    )


def load_skill_config(path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    config_path = path if path is not None else SKILL_CONFIG_PATH
    try:
        data = config_path.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise BridgeError("invalid_config", "The Skill config.json could not be read.") from exc
    if len(data) > MAX_CONFIG_BYTES:
        raise BridgeError("invalid_config", "The Skill config.json is too large.")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BridgeError("invalid_config", "The Skill config.json must contain valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise BridgeError("invalid_config", "The Skill config.json must contain a JSON object.")
    unknown = set(value) - {
        "endpoint",
        "allowedAgentModes",
        "managerIdleSeconds",
        "transport",
        "aliyunCLIExecutionMode",
        "enableThinking",
        "aliyunCLIProfile",
    }
    if unknown:
        raise BridgeError("invalid_config", "The Skill config.json contains unsupported fields.")

    result = {}  # type: Dict[str, Any]
    if "transport" in value:
        transport = value["transport"]
        if not isinstance(transport, str) or transport not in SUPPORTED_TRANSPORTS:
            raise BridgeError("invalid_config", "transport must be code or aliyun_cli.")
        result["transport"] = transport

    if "aliyunCLIExecutionMode" in value:
        execution_mode = value["aliyunCLIExecutionMode"]
        if not isinstance(execution_mode, str) or execution_mode not in SUPPORTED_ALIYUN_CLI_EXECUTION_MODES:
            raise BridgeError("invalid_config", "aliyunCLIExecutionMode must be local or remote.")
        result["aliyunCLIExecutionMode"] = execution_mode

    if "endpoint" in value:
        endpoint = value["endpoint"]
        if not isinstance(endpoint, str) or not endpoint.strip() or endpoint != endpoint.strip():
            raise BridgeError("invalid_config", "The config endpoint must be a non-empty string without padding.")
        _endpoint_kind(endpoint, "invalid_config")
        result["endpoint"] = endpoint

    if "allowedAgentModes" in value:
        modes = value["allowedAgentModes"]
        if not isinstance(modes, list) or not modes:
            raise BridgeError("invalid_config", "allowedAgentModes must be a non-empty JSON array.")
        if any(not isinstance(mode, str) or mode not in SUPPORTED_AGENT_MODES for mode in modes):
            raise BridgeError("invalid_config", "allowedAgentModes may contain only normal and pipeline.")
        if len(set(modes)) != len(modes):
            raise BridgeError("invalid_config", "allowedAgentModes must not contain duplicates.")
        result["allowedAgentModes"] = modes

    if "managerIdleSeconds" in value:
        idle_seconds = value["managerIdleSeconds"]
        if (
            isinstance(idle_seconds, bool)
            or not isinstance(idle_seconds, int)
            or not 1 <= idle_seconds <= MAX_MANAGER_IDLE_SECONDS
        ):
            raise BridgeError(
                "invalid_config",
                "managerIdleSeconds must be an integer from 1 through {}.".format(MAX_MANAGER_IDLE_SECONDS),
            )
        result["managerIdleSeconds"] = idle_seconds

    if "enableThinking" in value:
        enable_thinking = value["enableThinking"]
        if not isinstance(enable_thinking, bool):
            raise BridgeError("invalid_config", "enableThinking must be true or false.")
        result["enableThinking"] = enable_thinking

    if "aliyunCLIProfile" in value:
        profile = value["aliyunCLIProfile"]
        if (
            not isinstance(profile, str)
            or profile != profile.strip()
            or len(profile.encode("utf-8")) > 200
            or any(character in profile for character in "\r\n\0")
        ):
            raise BridgeError(
                "invalid_config",
                "aliyunCLIProfile must be an empty or non-padded Profile name of at most 200 bytes.",
            )
        result["aliyunCLIProfile"] = profile

    execution_mode = result.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE)
    transport = result.get("transport", DEFAULT_TRANSPORT)
    if "aliyunCLIExecutionMode" in result and transport != "aliyun_cli":
        raise BridgeError(
            "invalid_config",
            "aliyunCLIExecutionMode may be configured only when transport is aliyun_cli.",
        )
    if execution_mode == "remote":
        if result.get("aliyunCLIProfile"):
            raise BridgeError(
                "invalid_config",
                "aliyunCLIProfile is not available when aliyunCLIExecutionMode is remote.",
            )
        endpoint = result.get("endpoint")
        if isinstance(endpoint, str) and _endpoint_kind(endpoint, "invalid_config") != "aliyun":
            raise BridgeError(
                "invalid_config",
                "Remote aliyun CLI execution requires a public aliyuncs.com endpoint.",
            )
    return result


def apply_skill_config(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    configured_endpoint = config.get("endpoint")
    allowed_modes = config.get("allowedAgentModes", sorted(SUPPORTED_AGENT_MODES))
    transport = config.get("transport", DEFAULT_TRANSPORT)
    cli_execution_mode = config.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE)
    enable_thinking = config.get("enableThinking", True)
    configured_profile = config.get("aliyunCLIProfile", "")
    args.manager_idle_seconds = config.get("managerIdleSeconds", MANAGER_IDLE_SECONDS)
    args.enable_thinking = enable_thinking
    args.aliyun_cli_profile = configured_profile
    args.aliyun_cli_execution_mode = cli_execution_mode
    args.profile_pinned = bool(configured_profile)
    if args.command == "check":
        args.endpoint = configured_endpoint or DEFAULT_ENDPOINT
        args.allowed_agent_modes = list(allowed_modes)
        args.transport = transport
        args.profile = configured_profile or None
        return
    if args.command not in {"chat", "start"}:
        return
    requested_endpoint = args.endpoint
    if configured_endpoint and requested_endpoint and configured_endpoint != requested_endpoint:
        raise BridgeError("config_conflict", "--endpoint conflicts with the endpoint fixed by Skill config.json.")
    args.endpoint = configured_endpoint or requested_endpoint or DEFAULT_ENDPOINT
    args.transport = transport
    endpoint_kind = _endpoint_kind(args.endpoint, "invalid_config" if configured_endpoint else "invalid_input")
    if transport == "aliyun_cli" and cli_execution_mode == "remote" and endpoint_kind != "aliyun":
        raise BridgeError("invalid_input", "Remote aliyun CLI execution requires a public aliyuncs.com endpoint.")
    if args.mode not in allowed_modes:
        raise BridgeError("mode_not_allowed", "Agent mode {} is not allowed by Skill config.json.".format(args.mode))
    requested_profile = getattr(args, "profile", None)
    if transport == "aliyun_cli" and cli_execution_mode == "remote" and requested_profile:
        raise BridgeError("config_conflict", "--profile is not available with remote aliyun CLI execution.")
    if configured_profile and requested_profile and requested_profile != configured_profile:
        raise BridgeError("config_conflict", "--profile conflicts with aliyunCLIProfile fixed by Skill config.json.")
    args.profile = configured_profile or requested_profile
    if transport == "aliyun_cli" and getattr(args, "client_context_file", None):
        raise BridgeError("unsupported_input", "The ROS CLI plugin does not support ClientContext.")
    if getattr(args, "no_thinking", False) and enable_thinking:
        raise BridgeError("config_conflict", "--no-thinking conflicts with enableThinking fixed by Skill config.json.")
    args.no_thinking = not enable_thinking


def _truncate_utf8(value: str, maximum: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum:
        return value
    return encoded[:maximum].decode("utf-8", "ignore")


def sanitize_text(value: Any, maximum: int = 4000, preserve_lines: bool = False) -> str:
    if not isinstance(value, str):
        return ""
    value = SECRET_PATTERN.sub(lambda match: match.group(1) + "[REDACTED]", value)
    value = "".join(character for character in value if character in "\n\r\t" or ord(character) >= 32)
    if not preserve_lines:
        value = " ".join(value.split())
    return _truncate_utf8(value, maximum)


def _workspace(raw_path: Optional[str] = None) -> pathlib.Path:
    path = (
        _resolve_user_owned_path(raw_path, "invalid_input", "The workspace")
        if raw_path is not None
        else pathlib.Path.cwd().resolve()
    )
    if not path.is_dir():
        raise BridgeError("invalid_input", "The workspace must be an existing directory.")
    return path


def _trusted_manager_workspace(raw_path: str) -> pathlib.Path:
    """Resolve a manager workspace under the same user-owned roots as the CLI."""

    path = _resolve_user_owned_path(raw_path, "invalid_input", "The workspace")
    if not path.is_dir():
        raise BridgeError("invalid_input", "The workspace must be an existing directory.")
    return path


def _read_workspace_file(workspace: pathlib.Path, raw_path: str, maximum: int, label: str) -> str:
    workspace_path = os.path.normcase(os.path.realpath(str(workspace)))
    resolved_path = os.path.normcase(os.path.realpath(os.path.expanduser(raw_path)))
    if not resolved_path.startswith(workspace_path.rstrip(os.sep) + os.sep):
        raise BridgeError("invalid_input", "{} must be inside the workspace.".format(label))
    path = pathlib.Path(resolved_path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise BridgeError("invalid_input", "{} could not be read.".format(label)) from exc
    if len(data) > maximum:
        raise BridgeError("invalid_input", "{} is too large.".format(label))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BridgeError("invalid_input", "{} must be UTF-8.".format(label)) from exc


def read_prompt(workspace: pathlib.Path, raw_path: str) -> str:
    prompt = _read_workspace_file(workspace, raw_path, MAX_PROMPT_BYTES, "The prompt file")
    if not prompt.strip():
        raise BridgeError("invalid_input", "The prompt file must not be empty.")
    return prompt


def _load_json_file(workspace: pathlib.Path, raw_path: str, maximum: int, label: str) -> Any:
    text = _read_workspace_file(workspace, raw_path, maximum, label)
    try:
        return json.loads(text)
    except ValueError as exc:
        raise BridgeError("invalid_input", "{} must contain valid JSON.".format(label)) from exc


def _contains_sensitive_client_context_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if any(part in normalized for part in SENSITIVE_CLIENT_CONTEXT_KEY_PARTS):
                return True
            if _contains_sensitive_client_context_key(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_sensitive_client_context_key(item) for item in value)
    return False


def load_client_context(workspace: pathlib.Path, raw_path: Optional[str]) -> Optional[str]:
    if not raw_path:
        return None
    value = _load_json_file(workspace, raw_path, MAX_CONTEXT_BYTES, "The client context file")
    if not isinstance(value, dict):
        raise BridgeError("invalid_input", "The client context must be a JSON object.")
    if _contains_sensitive_client_context_key(value):
        raise BridgeError("invalid_input", "The client context must not contain credential or secret fields.")
    compact = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    if len(compact.encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise BridgeError("invalid_input", "The compact client context is too large.")
    return compact


def _attachment_value(value: Dict[str, Any], *names: str) -> Optional[str]:
    for name in names:
        item = value.get(name)
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


def load_attachments(workspace: pathlib.Path, raw_path: Optional[str]) -> List[Dict[str, str]]:
    if not raw_path:
        return []
    value = _load_json_file(workspace, raw_path, MAX_CONTEXT_BYTES, "The attachments file")
    if not isinstance(value, list) or len(value) > MAX_ATTACHMENTS:
        raise BridgeError("invalid_input", "Attachments must be a JSON array with at most five items.")
    result = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise BridgeError("invalid_input", "Attachment {} must be an object.".format(index))
        attachment_type = _attachment_value(item, "Type", "type") or "image"
        mime_type = _attachment_value(item, "MimeType", "mimeType", "mime_type")
        object_key = _attachment_value(item, "OssObjectKey", "ossObjectKey", "oss_object_key")
        name = _attachment_value(item, "Name", "name")
        if attachment_type != "image":
            raise BridgeError("invalid_input", "Attachment {} must have Type image.".format(index))
        if mime_type not in SUPPORTED_IMAGE_TYPES:
            raise BridgeError("invalid_input", "Attachment {} has an unsupported MimeType.".format(index))
        if not object_key:
            raise BridgeError("invalid_input", "Attachment {} requires OssObjectKey.".format(index))
        projected = {"Type": attachment_type, "MimeType": mime_type, "OssObjectKey": object_key}
        if name:
            projected["Name"] = name
        result.append(projected)
    return result


def load_permission_query(
    workspace: pathlib.Path,
    raw_path: str,
    decision: str,
    session_id: str,
    mode: str,
) -> Tuple[str, Dict[str, str]]:
    value = _load_json_file(workspace, raw_path, MAX_CONTEXT_BYTES, "The permission input file")
    return build_permission_query(value, decision, session_id, mode)


def build_permission_query(
    value: Any,
    decision: str,
    session_id: str,
    mode: str,
) -> Tuple[str, Dict[str, str]]:
    if not isinstance(value, dict) or value.get("schemaVersion") != 1 or value.get("kind") != "permission":
        raise BridgeError("invalid_input", "The pending input must be a schemaVersion 1 permission.")
    if decision not in PERMISSION_DECISIONS:
        raise BridgeError("invalid_input", "The permission decision must be allow_once or deny.")
    correlation = {}
    for key in ("requestTaskId", "contextId", "inputId", "toolUseId"):
        item = value.get(key)
        if not isinstance(item, str) or not item:
            raise BridgeError("invalid_input", "The permission input file requires {}.".format(key))
        correlation[key] = item
    if correlation["contextId"] != session_id:
        raise BridgeError("invalid_input", "The permission contextId must match --session-id.")
    permission_class = value.get("permissionClass")
    allowed_classes = {"pipeline", "sub_pipeline"} if mode == "pipeline" else {"normal"}
    if permission_class is not None and permission_class not in allowed_classes:
        raise BridgeError("invalid_input", "The permissionClass does not match --mode.")
    payload = {
        "schemaVersion": 1,
        "kind": "permission",
        "requestTaskId": correlation["requestTaskId"],
        "contextId": correlation["contextId"],
        "inputId": correlation["inputId"],
        "toolUseId": correlation["toolUseId"],
        "decision": decision,
    }
    query = "{} {}".format(
        PERMISSION_QUERY_PREFIX,
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
    )
    return query, {**correlation, "decision": decision}


def resolve_aliyun(raw_path: str) -> str:
    expanded = os.path.expanduser(raw_path)
    resolved = shutil.which(expanded)
    if not resolved:
        raise BridgeError("cli_not_found", "Alibaba Cloud CLI is not installed or is not on PATH.")
    return os.path.abspath(resolved)


def build_start_chat_parameters(
    args: argparse.Namespace,
    prompt: str,
    client_context: Optional[str],
    attachments: List[Dict[str, str]],
) -> Dict[str, str]:
    parameters = {
        "Query": prompt,
        "AgentVersion": "V2",
        "EnablePartialMessage": "true",
        "EnableThinking": "false" if args.no_thinking else "true",
        "Mode": "IaCCodePipeline" if args.mode == "pipeline" else "IaCCodeNormal",
    }
    if args.session_id:
        parameters["SessionId"] = args.session_id
    if args.region_id:
        parameters["RegionId"] = args.region_id
    if client_context is not None:
        parameters["ClientContext"] = client_context
    for index, attachment in enumerate(attachments, start=1):
        for field in ("Type", "MimeType", "Name", "OssObjectKey"):
            if field in attachment:
                parameters["Attachments.{}.{}".format(index, field)] = attachment[field]
    return parameters


def build_command(
    args: argparse.Namespace,
    prompt: str,
    client_context: Optional[str],
    attachments: List[Dict[str, str]],
) -> List[str]:
    if client_context is not None:
        raise BridgeError("unsupported_input", "The ROS CLI plugin does not support ClientContext.")
    endpoint_kind = _endpoint_kind(args.endpoint or "")
    execution_mode = getattr(args, "aliyun_cli_execution_mode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE)
    if execution_mode == "remote" and endpoint_kind != "aliyun":
        raise BridgeError("invalid_input", "Remote aliyun CLI execution requires a public aliyuncs.com endpoint.")
    if execution_mode == "remote" and args.profile:
        raise BridgeError("invalid_input", "Remote aliyun CLI execution does not accept a local Profile.")
    command = [
        resolve_aliyun(args.aliyun_path),
        "ros",
        "start-chat",
        "--endpoint",
        args.endpoint,
        "--connect-timeout",
        str(args.connect_timeout),
        "--read-timeout",
        str(args.read_timeout),
        "--user-agent",
        USER_AGENT,
        "--yes",
    ]
    if endpoint_kind == "loopback":
        command.extend(["--secure", "--skip-secure-verify"])
    if args.profile:
        command.extend(["--profile", args.profile])
    if args.region_id:
        command.extend(["--region", args.region_id])
    command.extend(
        [
            "--query",
            prompt,
            "--agent-version",
            "V2",
            "--enable-partial-message",
            "true",
            "--enable-thinking",
            "false" if args.no_thinking else "true",
            "--biz-mode",
            "IaCCodePipeline" if args.mode == "pipeline" else "IaCCodeNormal",
        ]
    )
    if args.session_id:
        command.extend(["--session-id", args.session_id])
    if args.region_id:
        command.extend(["--biz-region-id", args.region_id])
    for attachment in attachments:
        values = []
        for field in ("Type", "MimeType", "Name", "OssObjectKey"):
            if field in attachment:
                values.append("{}={}".format(field, attachment[field]))
        command.extend(["--attachments", *values])
    return command


def build_stop_command(job: Dict[str, Any], session_id: str) -> List[str]:
    endpoint = str(job.get("endpoint") or "")
    endpoint_kind = _endpoint_kind(endpoint)
    execution_mode = job.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE)
    if execution_mode == "remote" and endpoint_kind != "aliyun":
        raise BridgeError("invalid_input", "Remote aliyun CLI execution requires a public aliyuncs.com endpoint.")
    if execution_mode == "remote" and job.get("profile"):
        raise BridgeError("invalid_input", "Remote aliyun CLI execution does not accept a local Profile.")
    command = [
        resolve_aliyun(str(job.get("aliyunPath") or "aliyun")),
        "ros",
        "stop-chat",
        "--endpoint",
        endpoint,
        "--connect-timeout",
        str(max(1, min(int(job.get("connectTimeout") or 10), 30))),
        "--read-timeout",
        "45",
        "--user-agent",
        USER_AGENT,
        "--yes",
    ]
    if endpoint_kind == "loopback":
        command.extend(["--secure", "--skip-secure-verify"])
    profile = job.get("profile")
    if isinstance(profile, str) and profile:
        command.extend(["--profile", profile])
    region_id = job.get("regionId")
    if isinstance(region_id, str) and region_id:
        command.extend(["--region", region_id])
    command.extend(["--agent-version", "V2", "--session-id", session_id])
    return command


def _load_code_sdk() -> Dict[str, Any]:
    try:
        return {
            "CredentialClient": getattr(importlib.import_module("alibabacloud_credentials.client"), "Client"),
            "CLIProfileCredentialsProvider": getattr(
                importlib.import_module("alibabacloud_credentials.provider.cli_profile"),
                "CLIProfileCredentialsProvider",
            ),
            "DaraRequest": getattr(importlib.import_module("darabonba.request"), "DaraRequest"),
            "OpenApiUtils": getattr(importlib.import_module("alibabacloud_tea_openapi.utils"), "Utils"),
            "requests": importlib.import_module("requests"),
        }
    except (ImportError, AttributeError) as exc:
        raise BridgeError(
            "sdk_not_installed",
            "The configured code transport requires the packages listed in {} for the Python interpreter running "
            "this bridge. Do not switch transports; install them and run check again.".format(REQUIREMENTS_FILE),
        ) from exc


def _first_nonempty_env(names: Tuple[str, ...]) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _environment_region() -> Optional[str]:
    region_id = _first_nonempty_env(REGION_ENV_NAMES)
    if region_id and re.fullmatch(r"[A-Za-z0-9-]+", region_id):
        return region_id
    return None


def _cli_config_path() -> pathlib.Path:
    return pathlib.Path(os.path.expanduser("~/.aliyun/config.json")).resolve()


def _read_cli_configuration() -> Dict[str, Any]:
    path = _cli_config_path()
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_CLI_CONFIG_BYTES + 1)
    except OSError as exc:
        raise BridgeError("credential_failed", "The Alibaba Cloud CLI configuration is unavailable.") from exc
    if len(raw) > MAX_CLI_CONFIG_BYTES:
        raise BridgeError("credential_failed", "The Alibaba Cloud CLI configuration file is too large.")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BridgeError("credential_failed", "The Alibaba Cloud CLI configuration file is invalid.") from exc
    if not isinstance(value, dict) or not isinstance(value.get("profiles"), list):
        raise BridgeError("credential_failed", "The Alibaba Cloud CLI configuration file is invalid.")
    return value


def _local_ros_plugin_status() -> Dict[str, Any]:
    configured_root = os.environ.get("ALIBABA_CLOUD_CLI_PLUGINS_DIR")
    root = (
        pathlib.Path(os.path.expanduser(configured_root))
        if configured_root
        else pathlib.Path.home() / ".aliyun" / "plugins"
    )
    manifest_path = root / "manifest.json"
    try:
        with manifest_path.open("rb") as handle:
            raw = handle.read(MAX_PLUGIN_MANIFEST_BYTES + 1)
    except FileNotFoundError:
        return {"installed": False, "ready": False}
    except OSError as exc:
        raise BridgeError("cli_check_failed", "The Alibaba Cloud CLI plugin manifest could not be read.") from exc
    if len(raw) > MAX_PLUGIN_MANIFEST_BYTES:
        raise BridgeError("cli_check_failed", "The Alibaba Cloud CLI plugin manifest is too large.")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BridgeError("cli_check_failed", "The Alibaba Cloud CLI plugin manifest is invalid.") from exc
    plugins = manifest.get("plugins") if isinstance(manifest, dict) else None
    plugin = plugins.get("aliyun-cli-ros") if isinstance(plugins, dict) else None
    if not isinstance(plugin, dict):
        return {"installed": False, "ready": False}

    commands = plugin.get("cmdNames")
    command_names = {value for value in commands if isinstance(value, str)} if isinstance(commands, list) else set()
    raw_path = plugin.get("path")
    executable_exists = False
    if isinstance(raw_path, str) and raw_path:
        plugin_root = pathlib.Path(os.path.expanduser(raw_path))
        candidates = (plugin_root / "aliyun-cli-ros", plugin_root / "aliyun-cli-ros.exe")
        executable_exists = any(
            candidate.is_file() and (os.name == "nt" or os.access(str(candidate), os.X_OK)) for candidate in candidates
        )
    result: Dict[str, Any] = {
        "installed": True,
        "ready": executable_exists and ROS_PLUGIN_COMMANDS.issubset(command_names),
    }
    version = plugin.get("version")
    if isinstance(version, str) and version:
        result["version"] = sanitize_text(version, 80)
    return result


def _selected_cli_profile_record(profile: Optional[str]) -> Dict[str, Any]:
    value = _read_cli_configuration()
    profile_name = profile or _first_nonempty_env(PROFILE_ENV_NAMES) or value.get("current")
    if not isinstance(profile_name, str) or not profile_name:
        raise BridgeError("credential_failed", "The selected Alibaba Cloud CLI Profile is not configured.")
    selected = next(
        (item for item in value["profiles"] if isinstance(item, dict) and item.get("name") == profile_name),
        None,
    )
    mode = selected.get("mode") if isinstance(selected, dict) else None
    if not isinstance(mode, str) or not mode:
        raise BridgeError("credential_failed", "The selected Alibaba Cloud CLI Profile is not configured.")
    assert isinstance(selected, dict)
    result: Dict[str, Any] = {"name": profile_name, "mode": mode}
    region_id = selected.get("region_id")
    if isinstance(region_id, str) and re.fullmatch(r"[A-Za-z0-9-]+", region_id):
        result["regionId"] = region_id
    language = selected.get("language")
    if isinstance(language, str) and language:
        result["language"] = sanitize_text(language, 50)
    result["autoPluginInstall"] = bool(selected.get("auto_plugin_install")) or (
        os.environ.get("ALIBABA_CLOUD_CLI_PLUGIN_AUTO_INSTALL") == "true"
    )
    return result


def _resolve_start_identity(args: argparse.Namespace) -> None:
    if (
        args.transport == "aliyun_cli"
        and getattr(args, "aliyun_cli_execution_mode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE) == "remote"
    ):
        args.profile = None
        args.credential_source = "remote"
        return
    profile = None  # type: Optional[Dict[str, Any]]
    if args.transport == "code" and not getattr(args, "profile_pinned", False):
        args.profile = None
        args.credential_source = None
    else:
        profile = _selected_cli_profile_record(args.profile)
        args.profile = profile["name"]
        args.credential_source = "profile"

    if not args.region_id:
        args.region_id = _environment_region()
    if not args.region_id and profile is not None:
        args.region_id = profile.get("regionId")
    if not args.region_id:
        args.region_id = "cn-hangzhou"


def _code_credentials(
    sdk: Dict[str, Any],
    aliyun_path: str,
    profile: Optional[str],
    region_id: Optional[str],
    credential_source: Optional[str] = None,
) -> Tuple[str, str, Optional[str]]:
    if credential_source not in {None, "profile"}:
        raise BridgeError("credential_failed", "The managed Alibaba Cloud credential source is invalid.")
    if credential_source == "profile":
        selected = _selected_cli_profile_record(profile)
        provider = sdk["CLIProfileCredentialsProvider"](profile_name=selected["name"])
        client = sdk["CredentialClient"](provider=provider)
    else:
        client = sdk["CredentialClient"]()
    credential = client.get_credential()
    access_key_id = credential.access_key_id
    access_key_secret = credential.access_key_secret
    security_token = credential.security_token
    if not access_key_id or not access_key_secret:
        raise ValueError("empty credentials")
    return access_key_id, access_key_secret, security_token or None


def _canonical_query_string(parameters: Dict[str, str]) -> str:
    return "&".join(
        "{}={}".format(name, urllib.parse.quote(value, safe="~", encoding="utf-8"))
        for name, value in sorted(parameters.items())
    )


def _build_v3_request(
    sdk: Dict[str, Any],
    operation: str,
    parameters: Dict[str, str],
    endpoint: str,
    credentials: Tuple[str, str, Optional[str]],
) -> Tuple[str, Dict[str, str]]:
    access_key_id, access_key_secret, security_token = credentials
    signature_algorithm = "ACS3-HMAC-SHA256"
    utils = sdk["OpenApiUtils"]
    payload_hash = utils.hash(b"", signature_algorithm).hex()
    headers = {
        "accept": "text/event-stream" if operation == "StartChat" else "application/json",
        "accept-encoding": "identity",
        "host": endpoint,
        "user-agent": USER_AGENT,
        "x-acs-action": operation,
        "x-acs-content-sha256": payload_hash,
        "x-acs-date": utils.get_timestamp(),
        "x-acs-signature-nonce": utils.get_nonce(),
        "x-acs-version": "2019-09-10",
    }
    if security_token:
        headers["x-acs-accesskey-id"] = access_key_id
        headers["x-acs-security-token"] = security_token

    request = sdk["DaraRequest"]()
    request.protocol = "https"
    request.method = "POST"
    request.pathname = "/"
    request.query = dict(parameters)
    request.headers = headers
    headers["Authorization"] = utils.get_authorization(
        request,
        signature_algorithm,
        payload_hash,
        access_key_id,
        access_key_secret,
    )
    query = _canonical_query_string(parameters)
    return "https://{}/{}".format(endpoint, "?{}".format(query) if query else ""), headers


class _CodeHttpResponse:
    def __init__(self, response: Any, session: Any):
        self._response = response
        self._session = session
        self.headers = response.headers

    def __iter__(self) -> Iterator[bytes]:
        # A connection-close SSE response can otherwise buffer complete events
        # until the requested chunk fills or the stream ends.
        for line in self._response.iter_lines(chunk_size=1, decode_unicode=False):
            yield line + b"\n"

    def read(self, maximum: int) -> bytes:
        return self._response.raw.read(maximum, decode_content=True)

    def close(self) -> None:
        self._response.close()
        self._session.close()


def _open_code_request(
    operation: str,
    parameters: Dict[str, str],
    endpoint: str,
    profile: Optional[str],
    region_id: Optional[str],
    aliyun_path: str,
    connect_timeout: int,
    read_timeout: int,
    credential_source: Optional[str] = None,
    error_code: str = "start_chat_failed",
) -> Any:
    sdk = _load_code_sdk()
    try:
        credentials = _code_credentials(sdk, aliyun_path, profile, region_id, credential_source)
        url, headers = _build_v3_request(sdk, operation, parameters, endpoint, credentials)
    except BridgeError:
        raise
    except Exception as exc:
        raise BridgeError(
            "credential_failed",
            "Alibaba Cloud SDK could not load or refresh the selected CLI Profile.",
            True,
        ) from exc

    session = sdk["requests"].Session()
    try:
        response = session.request(
            method="POST",
            url=url,
            data=None,
            headers=headers,
            timeout=(connect_timeout, read_timeout),
            allow_redirects=False,
            verify=_endpoint_kind(endpoint) != "loopback",
            stream=True,
        )
    except Exception as exc:
        session.close()
        raise BridgeError(error_code, "Alibaba Cloud ROS {} could not be reached.".format(operation), True) from exc

    wrapped = _CodeHttpResponse(response, session)
    if 400 <= response.status_code < 600:
        raw = wrapped.read(MAX_DIAGNOSTIC_BYTES + 1)
        wrapped.close()
        message = "Alibaba Cloud ROS rejected the request."
        if len(raw) <= MAX_DIAGNOSTIC_BYTES:
            with contextlib.suppress(UnicodeError, ValueError):
                value = json.loads(raw.decode("utf-8"))
                if isinstance(value, dict):
                    code = value.get("Code", value.get("code"))
                    detail = value.get("Message", value.get("message"))
                    if isinstance(code, str) or isinstance(detail, str):
                        message = "{}: {}".format(code or "{}Failed".format(operation), detail or "Request failed")
        raise BridgeError(error_code, sanitize_text(message, 2000), response.status_code >= 500)
    return wrapped


def _response_text_lines(response: Any) -> Iterator[str]:
    for raw_line in response:
        if len(raw_line) > MAX_SSE_LINE_BYTES:
            raise BridgeError("stream_failed", "A StartChat SSE line exceeded the bridge limit.")
        yield raw_line.decode("utf-8", "replace")


def iter_sse_payloads(lines: Iterable[str]) -> Iterator[Tuple[Optional[Dict[str, Any]], str]]:
    data_lines = []  # type: List[str]
    raw_lines = []  # type: List[str]
    event_bytes = 0

    def decode(data: List[str], raw: List[str]) -> Tuple[Optional[Dict[str, Any]], str]:
        payload_text = "\n".join(data).strip() if data else "\n".join(raw).strip()
        if len(payload_text.encode("utf-8")) > MAX_SSE_EVENT_BYTES:
            raise BridgeError("stream_failed", "A StartChat SSE event exceeded the bridge limit.")
        try:
            value = json.loads(payload_text)
        except ValueError:
            return None, payload_text
        return (value if isinstance(value, dict) else None), payload_text

    for raw_line in lines:
        event_bytes += len(raw_line.encode("utf-8"))
        if event_bytes > MAX_SSE_EVENT_BYTES:
            raise BridgeError("stream_failed", "A StartChat SSE event exceeded the bridge limit.")
        line = raw_line.rstrip("\r\n")
        if not line:
            if data_lines or raw_lines:
                yield decode(data_lines, raw_lines)
                data_lines = []
                raw_lines = []
            event_bytes = 0
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif not data_lines:
            raw_lines.append(line)
    if data_lines or raw_lines:
        yield decode(data_lines, raw_lines)


def _cli_plugin_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def iter_cli_plugin_payloads(lines: Iterable[str]) -> Iterator[Tuple[Optional[Dict[str, Any]], str]]:
    for raw_line in lines:
        if len(raw_line.encode("utf-8")) > MAX_SSE_LINE_BYTES:
            raise BridgeError("stream_failed", "A StartChat CLI output line exceeded the bridge limit.")
        payload_text = raw_line.strip()
        if not payload_text:
            continue
        try:
            value = json.loads(payload_text)
        except ValueError:
            yield None, payload_text
            continue
        if not isinstance(value, dict):
            yield None, payload_text
            continue
        yield _cli_plugin_payload(value), payload_text


def _event_payload(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    for key in ("statusUpdate", "artifactUpdate"):
        value = result.get(key)
        if isinstance(value, dict):
            return value
    return result


def _result(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = payload.get("result")
    return result if isinstance(result, dict) else payload


def _normalize_state(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized.startswith("task_state_"):
        normalized = normalized[len("task_state_") :]
    return normalized.replace("_", "-")


def _state_from_result(result: Dict[str, Any]) -> Tuple[str, str]:
    event = _event_payload(result)
    candidates = [event]
    if isinstance(event, dict) and isinstance(event.get("task"), dict):
        candidates.append(event["task"])
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        status = candidate.get("status") or candidate.get("Status")
        if isinstance(status, dict):
            state = status.get("state") or status.get("State")
            if isinstance(state, str):
                return _normalize_state(state), state
        state = candidate.get("state") or candidate.get("State")
        if isinstance(state, str) and state.upper().startswith("TASK_STATE_"):
            return _normalize_state(state), state
    return "", ""


def _find_first(value: Any, *keys: str) -> Any:
    if isinstance(value, dict):
        for key in keys:
            if value.get(key) not in (None, ""):
                return value[key]
        for item in value.values():
            found = _find_first(item, *keys)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_first(item, *keys)
            if found not in (None, ""):
                return found
    return None


def _metadata_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    event = _event_payload(result)
    candidates = []
    if isinstance(event, dict):
        candidates.append(event.get("metadata"))
        status = event.get("status")
        if isinstance(status, dict):
            candidates.append(status.get("metadata"))
        task = event.get("task")
        if isinstance(task, dict):
            candidates.append(task.get("metadata"))
    for value in candidates:
        if isinstance(value, dict) and isinstance(value.get("iac_code"), dict):
            return value["iac_code"]
    return {}


def _message_text_from_result(result: Dict[str, Any]) -> str:
    event = _event_payload(result)
    candidates = []
    if isinstance(event, dict):
        status = event.get("status")
        if isinstance(status, dict):
            candidates.append(status.get("message"))
        candidates.append(event.get("message"))
        task = event.get("task")
        if isinstance(task, dict) and isinstance(task.get("status"), dict):
            candidates.append(task["status"].get("message"))
    for message in candidates:
        if not isinstance(message, dict) or not isinstance(message.get("parts"), list):
            continue
        pieces = [
            part.get("text")
            for part in message["parts"]
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        if pieces:
            return "".join(pieces)
    return ""


def _permission_ack_from_result(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    metadata_ack = _metadata_from_result(result).get("permissionAck")
    event = _event_payload(result)
    candidates = [metadata_ack, event]
    if isinstance(event, dict):
        candidates.append(event.get("message"))
        status = event.get("status")
        if isinstance(status, dict):
            candidates.append(status.get("message"))
    for candidate in candidates:
        data_values = [candidate]
        if isinstance(candidate, dict) and isinstance(candidate.get("parts"), list):
            data_values.extend(part.get("data") for part in candidate["parts"] if isinstance(part, dict))
        for data in data_values:
            if not isinstance(data, dict) or data.get("kind") != "permission_ack":
                continue
            projected = {
                key: data[key]
                for key in ("schemaVersion", "kind", "inputId", "toolUseId", "decision", "accepted")
                if key in data
            }
            if projected.get("schemaVersion") != 1 or projected.get("accepted") is not True:
                continue
            if projected.get("decision") not in PERMISSION_DECISIONS:
                continue
            return projected
    return None


def _permission_is_acknowledged(permission: Any, acknowledgement: Any) -> bool:
    return (
        isinstance(permission, dict)
        and isinstance(acknowledgement, dict)
        and acknowledgement.get("accepted") is True
        and isinstance(permission.get("inputId"), str)
        and permission.get("inputId") == acknowledgement.get("inputId")
    )


def _permission_response_is_acknowledged(response: Any, acknowledgement: Any) -> bool:
    if not isinstance(response, dict) or not isinstance(acknowledgement, dict):
        return False
    if acknowledgement.get("accepted") is not True or acknowledgement.get("schemaVersion") != 1:
        return False
    return all(response.get(key) == acknowledgement.get(key) for key in ("inputId", "toolUseId", "decision"))


def _safe_deployment_summary(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    result = {}
    fields = (
        ("candidateName", 200),
        ("action", 80),
        ("region", 120),
        ("stackName", 200),
        ("template", 300),
        ("totalMonthlyCost", 300),
    )
    for key, maximum in fields:
        if key in value:
            result[key] = sanitize_text(value.get(key), maximum)
    resources = value.get("resources")
    if isinstance(resources, list):
        result["resources"] = [
            {
                key: sanitize_text(item.get(key), maximum)
                for key, maximum in (("name", 200), ("spec", 300), ("monthlyCost", 300))
                if key in item
            }
            for item in resources[:12]
            if isinstance(item, dict)
        ]
    return result or None


def _safe_input(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    allowed = {"schemaVersion", "kind", "requestTaskId", "contextId", "inputId", "prompt", "options", "required"}
    if kind == "permission":
        allowed.update(
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
        allowed.update({"allowFreeText", "freeTextPrompt"})
    elif kind != "candidate_selection":
        return None
    result = {key: value[key] for key in allowed if key in value}
    text_fields = (
        ("prompt", 1000),
        ("freeTextPrompt", 600),
        ("safeSummary", 1200),
        ("title", 300),
        ("purpose", 600),
        ("effect", 120),
        ("target", 600),
        ("toolName", 120),
        ("language", 12),
    )
    for key, maximum in text_fields:
        if key in result:
            result[key] = sanitize_text(result[key], maximum)
    if "isReadOnly" in result:
        result["isReadOnly"] = result["isReadOnly"] is True
    if "allowFreeText" in result:
        result["allowFreeText"] = result["allowFreeText"] is True
    if "deploymentSummary" in result:
        result["deploymentSummary"] = _safe_deployment_summary(result["deploymentSummary"])
    options = value.get("options")
    if isinstance(options, list):
        safe_options = []
        for item in options[:20]:
            if not isinstance(item, dict):
                continue
            safe_item = {}
            option_fields = (
                ("id", 120),
                ("label", 240),
                ("summary", 800),
                ("architectureDiagram", 2400),
                ("totalMonthlyCost", 300),
            )
            for key, maximum in option_fields:
                if key in item:
                    safe_item[key] = sanitize_text(item.get(key), maximum, key == "architectureDiagram")
            costs = item.get("costItems")
            if isinstance(costs, list):
                safe_item["costItems"] = [
                    {
                        key: sanitize_text(cost.get(key), maximum)
                        for key, maximum in (("name", 200), ("spec", 300), ("monthlyCost", 300))
                        if key in cost
                    }
                    for cost in costs[:12]
                    if isinstance(cost, dict)
                ]
            if safe_item:
                safe_options.append(safe_item)
        result["options"] = safe_options
    return result


def _pipeline_events(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    batch = metadata.get("pipelineBatch")
    if isinstance(batch, dict) and isinstance(batch.get("events"), list):
        return [item for item in batch["events"] if isinstance(item, dict)]
    event = metadata.get("pipeline")
    return [event] if isinstance(event, dict) else []


def _input_from_metadata(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    direct = _safe_input(metadata.get("input"))
    if direct is not None:
        return direct

    def find(value: Any) -> Optional[Dict[str, Any]]:
        projected = _safe_input(value)
        if projected is not None:
            return projected
        if isinstance(value, dict):
            for item in value.values():
                projected = find(item)
                if projected is not None:
                    return projected
        elif isinstance(value, list):
            for item in value:
                projected = find(item)
                if projected is not None:
                    return projected
        return None

    return find(_pipeline_events(metadata))


def _pending_permissions_from_metadata(metadata: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    pending = metadata.get("pendingPermissions")
    if not isinstance(pending, list):
        return None
    result = []
    for value in pending:
        projected = _safe_input(value)
        if projected is not None and projected.get("kind") == "permission":
            result.append(projected)
    return result


def _safe_permission_wait(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    value = metadata.get("permissionWait")
    if not isinstance(value, dict):
        return None
    status = value.get("status")
    if not isinstance(status, str) or status not in {"waiting", "grace", "suspended"}:
        return None
    result = {"status": status}
    if "resumable" in value:
        result["resumable"] = value.get("resumable") is True
    return result


def _safe_permission_recovered(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    value = metadata.get("permissionRecovered")
    if not isinstance(value, dict):
        return None
    result = {}
    for key in ("inputId", "toolUseId"):
        item = value.get(key)
        if isinstance(item, str) and item:
            result[key] = sanitize_text(item, 240)
    return result or None


def _is_sideband_permission(metadata: Dict[str, Any], input_value: Dict[str, Any]) -> bool:
    if input_value.get("kind") != "permission":
        return False
    return any(
        event.get("eventType") == "permission_requested" and event.get("status") == "working"
        for event in _pipeline_events(metadata)
    )


def _permission_class(value: Dict[str, Any], *, mode: str, sideband: bool) -> Dict[str, Any]:
    if value.get("kind") != "permission":
        return value
    result = _permission_with_ref(value)
    result["permissionClass"] = "sub_pipeline" if sideband else ("pipeline" if mode == "pipeline" else "normal")
    return result


def _permission_ref(value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return None
    input_id = value.get("inputId")
    if not isinstance(input_id, str) or not input_id:
        return None
    digest = hashlib.sha256(input_id.encode("utf-8")).hexdigest()[:10]
    return "p-{}".format(digest)


def _permission_with_ref(value: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(value)
    if result.get("kind") == "permission":
        permission_ref = _permission_ref(result)
        if permission_ref is not None:
            result["permissionRef"] = permission_ref
    return result


def _safe_pipeline_result(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    result = {}
    for key, maximum in (("status", 80), ("stack_id", 240), ("error", 1000)):
        item = value.get(key)
        if isinstance(item, str) and item:
            result[key] = sanitize_text(item, maximum)
    resources = value.get("resources_created")
    if isinstance(resources, list):
        result["resources_created"] = [
            sanitize_text(item, 240) for item in resources[:24] if isinstance(item, str) and item
        ]
    outputs = value.get("outputs")
    if isinstance(outputs, dict):
        result["outputs"] = {
            sanitize_text(str(key), 120): sanitize_text(str(item), 300)
            for key, item in list(outputs.items())[:24]
            if isinstance(key, str) and isinstance(item, (str, int, float, bool))
        }
    return result or None


def _safe_intent_conclusion(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    result = {}
    for source, target, maximum in (
        ("user_message_summary", "requirementSummary", 360),
        ("cloud_platform", "cloudPlatform", 80),
        ("business_type", "businessType", 120),
    ):
        item = value.get(source)
        if isinstance(item, str) and item:
            result[target] = sanitize_text(item, maximum)
    non_functional = value.get("non_functional")
    if isinstance(non_functional, dict) and isinstance(non_functional.get("region_preference"), str):
        result["region"] = sanitize_text(non_functional["region_preference"], 120)
    resources = []
    for item in value.get("resource_intents", [])[:10] if isinstance(value.get("resource_intents"), list) else []:
        if not isinstance(item, dict):
            continue
        projected = {
            key: sanitize_text(item.get(key), maximum)
            for key, maximum in (("product", 100), ("action", 40), ("role", 100))
            if isinstance(item.get(key), str) and item.get(key)
        }
        if projected:
            resources.append(projected)
    if resources:
        result["resources"] = resources
    while len(_json_bytes(result)) > MAX_STEP_CONCLUSION_BYTES:
        if resources and len(resources) > 1:
            resources.pop()
        elif isinstance(result.get("requirementSummary"), str) and len(result["requirementSummary"]) > 120:
            result["requirementSummary"] = _truncate_utf8(result["requirementSummary"], 120)
        elif "businessType" in result:
            result.pop("businessType")
        elif "cloudPlatform" in result:
            result.pop("cloudPlatform")
        else:
            break
    return result or None


def _safe_architecture_conclusion(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict) or not isinstance(value.get("candidates"), list):
        return None
    raw_candidates = value["candidates"]
    candidates = []
    for item in raw_candidates[:4]:
        if not isinstance(item, dict):
            continue
        projected = {}
        for source, target, maximum in (
            ("name", "name", 160),
            ("topology", "topology", 300),
            ("monthly_estimate", "monthlyEstimate", 160),
        ):
            candidate = item.get(source)
            if isinstance(candidate, str) and candidate:
                projected[target] = sanitize_text(candidate, maximum)
        if projected:
            candidates.append(projected)
    result = {"candidateCount": len(raw_candidates), "candidates": candidates}
    while len(_json_bytes(result)) > MAX_STEP_CONCLUSION_BYTES and candidates:
        if len(candidates) > 2:
            candidates.pop()
            continue
        changed = False
        for candidate in reversed(candidates):
            topology = candidate.get("topology")
            if isinstance(topology, str) and len(topology) > 100:
                candidate["topology"] = _truncate_utf8(topology, 100)
                changed = True
                break
        if not changed:
            candidates.pop()
    return result if candidates else None


def _safe_step_conclusion(step_id: Any, conclusion_field: Any, value: Any) -> Optional[Dict[str, Any]]:
    if step_id == "intent_parsing" or conclusion_field == "intent":
        return _safe_intent_conclusion(value)
    if step_id == "architecture_planning" or conclusion_field == "architecture":
        return _safe_architecture_conclusion(value)
    return None


def _safe_milestone(value: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event_type = value.get("eventType") or value.get("event_type")
    if event_type not in PIPELINE_EVENT_TYPES:
        return None
    result = {"eventType": event_type}
    for key in ("status", "sequence", "scope"):
        item = value.get(key)
        if isinstance(item, (str, int)):
            result[key] = item
    for key in ("step", "parentStep", "candidate", "candidateStep"):
        item = value.get(key)
        if isinstance(item, dict):
            result[key] = {
                field: item[field]
                for field in ("id", "name", "index", "total")
                if isinstance(item.get(field), (str, int))
            }
    data = value.get("data")
    if isinstance(data, dict):
        message = data.get("message") or data.get("summary") or data.get("description")
        if isinstance(message, str):
            result["message"] = sanitize_text(message, 500)
        if event_type == "step_completed":
            step = value.get("step")
            step_id = step.get("id") if isinstance(step, dict) else None
            conclusion = _safe_step_conclusion(step_id, data.get("conclusionField"), data.get("conclusion"))
            if conclusion is not None:
                result["conclusionSummary"] = conclusion
    return result


def _normal_handoff_ready(value: Dict[str, Any]) -> bool:
    if value.get("eventType") != "pipeline_handoff_ready" or value.get("visibility") not in {None, "committed"}:
        return False
    data = value.get("data")
    return isinstance(data, dict) and data.get("action") == "switch_to_normal" and data.get("targetMode") == "normal"


def _safe_artifact(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event = _event_payload(result)
    artifact = event.get("artifact") if isinstance(event, dict) else None
    if not isinstance(artifact, dict):
        return None
    parts = artifact.get("parts")
    first = parts[0] if isinstance(parts, list) and parts and isinstance(parts[0], dict) else {}
    uri = first.get("url")
    if not isinstance(uri, str):
        return None
    metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
    projected = {
        "id": sanitize_text(str(artifact.get("artifactId") or ""), 128),
        "name": sanitize_text(artifact.get("name") or first.get("filename"), 240),
        "uri": sanitize_text(uri, 1200, True),
    }
    for key in ("mediaType", "sha256", "sourcePath"):
        if isinstance(metadata.get(key), str):
            projected[key] = sanitize_text(metadata[key], 1000, True)
    if isinstance(metadata.get("byteSize"), int):
        projected["byteSize"] = metadata["byteSize"]
    return projected


class StreamSummary:
    def __init__(self, initial_session_id: Optional[str] = None, mode: str = "normal") -> None:
        self.session_id = initial_session_id
        self.mode = mode
        self.task_id = None  # type: Optional[str]
        self.iac_code_session_id = None  # type: Optional[str]
        self.request_id = None  # type: Optional[str]
        self.state = ""
        self.wire_state = ""
        self.input_required = None  # type: Optional[Dict[str, Any]]
        self.input_required_from_pending = False
        self.pending_permissions = []  # type: List[Dict[str, Any]]
        self.permission_ack = None  # type: Optional[Dict[str, Any]]
        self.permission_wait = None  # type: Optional[Dict[str, Any]]
        self.permission_recovered = None  # type: Optional[Dict[str, Any]]
        self.sideband_input_ids = set()  # type: set
        self.resolved_sideband_input_ids = set()  # type: set
        self.text_parts = []  # type: List[str]
        self.text_bytes = 0
        self.text_truncated = False
        self.assistant_final = False
        self.milestones = []  # type: List[Dict[str, Any]]
        self.artifacts = []  # type: List[Dict[str, Any]]
        self.pipeline_result = None  # type: Optional[Dict[str, Any]]
        self.normal_handoff_ready = False
        self.event_count = 0
        self.heartbeat_count = 0
        self.malformed_event_count = 0
        self.error = None  # type: Optional[Dict[str, Any]]

    def _append_text(self, value: str) -> None:
        value = sanitize_text(value, MAX_FINAL_TEXT_BYTES, True)
        if not value:
            return
        remaining = MAX_FINAL_TEXT_BYTES - self.text_bytes
        if remaining <= 0:
            self.text_truncated = True
            return
        bounded = _truncate_utf8(value, remaining)
        self.text_parts.append(bounded)
        self.text_bytes += len(bounded.encode("utf-8"))
        if bounded != value:
            self.text_truncated = True

    def _replace_text(self, value: str) -> None:
        """Use the authoritative final snapshot instead of duplicating prior deltas."""
        raw_size = len(value.encode("utf-8"))
        value = sanitize_text(value, MAX_FINAL_TEXT_BYTES, True)
        self.text_parts = [value] if value else []
        self.text_bytes = len(value.encode("utf-8"))
        self.text_truncated = raw_size > MAX_FINAL_TEXT_BYTES

    def apply(self, payload: Dict[str, Any]) -> None:
        self.event_count += 1
        if str(payload.get("object", "")).lower() in {"heartbeat", "keepalive"}:
            self.heartbeat_count += 1
            return
        result = _result(payload)
        session_id = _find_first(payload, "contextId", "context_id", "SessionId")
        task_id = _find_first(payload, "taskId", "task_id")
        iac_session_id = _find_first(payload, "iacCodeSessionId", "iac_code_session_id")
        request_id = _find_first(payload, "requestId", "request_id", "RequestId")
        if isinstance(session_id, str):
            self.session_id = session_id
        if isinstance(task_id, str):
            self.task_id = task_id
        if isinstance(iac_session_id, str):
            self.iac_code_session_id = iac_session_id
        if isinstance(request_id, str):
            self.request_id = request_id
        state, wire_state = _state_from_result(result)
        # A few StartChat gateways emit a trailing WORKING status after the
        # authoritative terminal event. Keep the terminal state monotonic so
        # the managed job can expose Pipeline handoff instead of becoming an
        # ownerless working job when the CLI process exits.
        if state and (self.state not in TERMINAL_STATES or state in TERMINAL_STATES):
            self.state = state
            self.wire_state = wire_state
        metadata = _metadata_from_result(result)
        terminal_state_seen = self.state in TERMINAL_STATES
        if terminal_state_seen:
            # Terminal ownership also closes every waiting boundary. A stale
            # trailing status may still contribute artifacts, Pipeline
            # results, handoff metadata, text, or a real error below, but it
            # cannot reopen user input or permission-wait state.
            self.input_required = None
            self.input_required_from_pending = False
            self.pending_permissions = []
            self.permission_wait = None
        permission_wait = None if terminal_state_seen else _safe_permission_wait(metadata)
        if permission_wait is not None:
            self.permission_wait = permission_wait
        permission_recovered = None if terminal_state_seen else _safe_permission_recovered(metadata)
        if permission_recovered is not None:
            self.permission_recovered = permission_recovered
            self.permission_wait = None
            recovered_input_id = permission_recovered.get("inputId")
            if isinstance(self.input_required, dict) and self.input_required.get("inputId") == recovered_input_id:
                self.input_required = None
                self.input_required_from_pending = False
            self.pending_permissions = [
                value for value in self.pending_permissions if value.get("inputId") != recovered_input_id
            ]
        input_required = None if terminal_state_seen else _input_from_metadata(metadata)
        pending_permissions = None if terminal_state_seen else _pending_permissions_from_metadata(metadata)
        pending_input_ids = {value.get("inputId") for value in pending_permissions or [] if isinstance(value, dict)}
        if pending_permissions is not None:
            self.resolved_sideband_input_ids.update(self.sideband_input_ids - pending_input_ids)
        previous_sideband_input_id = (
            self.input_required.get("inputId")
            if isinstance(self.input_required, dict) and self.input_required.get("permissionClass") == "sub_pipeline"
            else None
        )
        sideband_input = input_required is not None and (
            _is_sideband_permission(metadata, input_required)
            or input_required.get("inputId") in pending_input_ids
            or input_required.get("inputId") in self.sideband_input_ids
            or input_required.get("inputId") == previous_sideband_input_id
        )
        if sideband_input and isinstance(input_required.get("inputId"), str):
            self.sideband_input_ids.add(input_required["inputId"])
        stale_resolved_sideband = (
            input_required is not None and input_required.get("inputId") in self.resolved_sideband_input_ids
        )
        if input_required is not None and not stale_resolved_sideband:
            self.input_required = _permission_class(input_required, mode=self.mode, sideband=sideband_input)
            self.input_required_from_pending = sideband_input
        if pending_permissions is None and sideband_input and isinstance(self.input_required, dict):
            pending_permissions = [self.input_required]
        if pending_permissions is not None:
            self.pending_permissions = [
                _permission_class(value, mode=self.mode, sideband=True) for value in pending_permissions
            ]
            direct_input_id = self.input_required.get("inputId") if isinstance(self.input_required, dict) else None
            matching_pending = next(
                (value for value in self.pending_permissions if value.get("inputId") == direct_input_id),
                None,
            )
            if matching_pending is not None:
                self.input_required = matching_pending
                self.input_required_from_pending = True
            elif self.pending_permissions and (self.input_required is None or self.input_required_from_pending):
                self.input_required = self.pending_permissions[0]
                self.input_required_from_pending = True
            elif not self.pending_permissions and self.input_required_from_pending:
                self.input_required = None
                self.input_required_from_pending = False
        text = _message_text_from_result(result)
        permission_ack = _permission_ack_from_result(result)
        if permission_ack is not None:
            self.permission_ack = permission_ack
        if _permission_is_acknowledged(self.input_required, self.permission_ack):
            acknowledged_input_id = self.permission_ack.get("inputId")
            self.input_required = None
            self.input_required_from_pending = False
            self.pending_permissions = [
                value for value in self.pending_permissions if value.get("inputId") != acknowledged_input_id
            ]
            if self.pending_permissions:
                self.input_required = self.pending_permissions[0]
                self.input_required_from_pending = True
        assistant_final = metadata.get("assistantFinal")
        is_assistant_final = isinstance(assistant_final, dict) and assistant_final.get("complete") is True
        if (is_assistant_final or self.state in TERMINAL_STATES) and self.input_required_from_pending:
            self.input_required = None
            self.input_required_from_pending = False
            self.pending_permissions = []
        if text:
            if is_assistant_final:
                self._replace_text(text)
            else:
                self._append_text(text)
        if is_assistant_final:
            self.assistant_final = True
        for item in _pipeline_events(metadata):
            if _normal_handoff_ready(item):
                self.normal_handoff_ready = True
            milestone = _safe_milestone(item)
            if milestone is not None and milestone not in self.milestones:
                self.milestones.append(milestone)
                self.milestones = self.milestones[-40:]
            data = item.get("data")
            if (
                item.get("eventType") == "step_completed"
                and isinstance(data, dict)
                and data.get("conclusionField") == "deployment"
            ):
                pipeline_result = _safe_pipeline_result(data.get("conclusion"))
                if pipeline_result is not None:
                    self.pipeline_result = pipeline_result
        artifact = _safe_artifact(result)
        if artifact is not None and artifact not in self.artifacts:
            self.artifacts.append(artifact)
            self.artifacts = self.artifacts[-24:]
        raw_error = payload.get("error")
        if not isinstance(raw_error, dict):
            raw_error = result.get("error") if isinstance(result.get("error"), dict) else None
        if isinstance(raw_error, dict):
            code = raw_error.get("code") or raw_error.get("Code") or "StartChatFailed"
            message = raw_error.get("message") or raw_error.get("Message") or "StartChat returned an error."
            self.error = {"code": sanitize_text(str(code), 160), "message": sanitize_text(str(message), 2000)}
        if str(payload.get("object", "")).lower() == "response" and str(payload.get("status", "")).lower() == "failed":
            self.state = "failed"

    def to_result(self, return_code: int, stderr_text: str) -> Dict[str, Any]:
        failed = return_code != 0 or self.state == "failed" or self.error is not None
        if failed:
            state = "failed"
        elif self.input_required is not None:
            state = "input-required"
        elif self.state in TERMINAL_STATES:
            state = "turn-completed" if self.mode == "normal" and self.state == "completed" else self.state
        elif self.assistant_final or (self.mode == "normal" and self.state == "input-required"):
            state = "turn-completed"
        elif self.permission_ack is not None:
            state = "permission-responded"
        else:
            state = self.state or "stream-ended"
        result = {
            "ok": not failed,
            "state": state,
            "presentationRequired": True,
            "eventCount": self.event_count,
            "heartbeatCount": self.heartbeat_count,
            "malformedEventCount": self.malformed_event_count,
        }  # type: Dict[str, Any]
        identities = (
            ("sessionId", self.session_id),
            ("taskId", self.task_id),
            ("iacCodeSessionId", self.iac_code_session_id),
            ("requestId", self.request_id),
            ("wireState", self.wire_state),
        )
        for key, value in identities:
            if value:
                result[key] = value
        text = "".join(self.text_parts)
        if state == "turn-completed":
            result["finalText"] = text
            result["finalTextComplete"] = not self.text_truncated
        elif text:
            result["latestText"] = _truncate_utf8(text, 16000)
        if self.input_required is not None:
            result["inputRequired"] = self.input_required
        if self.pending_permissions:
            result["pendingPermissions"] = self.pending_permissions
        if self.permission_ack is not None:
            result["permissionAck"] = self.permission_ack
        if self.permission_wait is not None:
            result["permissionWait"] = self.permission_wait
        if self.permission_recovered is not None:
            result["permissionRecovered"] = self.permission_recovered
        if self.milestones:
            result["milestones"] = self.milestones
        if self.artifacts:
            result["artifacts"] = self.artifacts
        if self.pipeline_result is not None:
            result["pipelineResult"] = self.pipeline_result
        if self.normal_handoff_ready:
            result["normalHandoffReady"] = True
            result["conversationMode"] = "normal"
        if self.error is not None:
            result["error"] = self.error
        elif return_code != 0:
            result["error"] = {
                "code": "aliyun_cli_failed",
                "message": sanitize_text(stderr_text, 3000)
                or "Alibaba Cloud CLI exited with status {}.".format(return_code),
            }
        elif self.event_count == 0:
            result["ok"] = False
            result["state"] = "failed"
            result["error"] = {"code": "empty_stream", "message": "StartChat ended without an SSE event."}
        return _bound_result(result)


def _bound_result(result: Dict[str, Any]) -> Dict[str, Any]:
    def size() -> int:
        return len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    while size() > MAX_RESULT_BYTES and result.get("milestones"):
        result["milestones"].pop(0)
    while size() > MAX_RESULT_BYTES and result.get("artifacts"):
        result["artifacts"].pop(0)
    if size() > MAX_RESULT_BYTES and isinstance(result.get("finalText"), str):
        result["finalText"] = _truncate_utf8(result["finalText"], MAX_RESULT_BYTES // 2)
        result["finalTextComplete"] = False
    return result


def _bound_projection(projection: Dict[str, Any]) -> Dict[str, Any]:
    bounded = dict(projection)
    input_value = bounded.get("inputRequired")
    maximum = MAX_INPUT_PROJECTION_BYTES if isinstance(input_value, dict) else MAX_PROJECTION_BYTES
    if len(_json_bytes(bounded)) <= maximum:
        return bounded
    if isinstance(input_value, dict):
        envelope = dict(input_value)
        bounded["inputRequired"] = envelope
        options = envelope.get("options")
        if isinstance(options, list):
            envelope["options"] = [dict(item) for item in options if isinstance(item, dict)]
        while len(_json_bytes(bounded)) > maximum:
            changed = False
            for key, minimum in (
                ("safeSummary", 160),
                ("purpose", 100),
                ("target", 80),
                ("prompt", 120),
                ("freeTextPrompt", 80),
            ):
                value = envelope.get(key)
                if isinstance(value, str) and len(value) > minimum:
                    envelope[key] = value[: max(minimum, len(value) // 2)]
                    changed = True
            for option in envelope.get("options", []):
                if not isinstance(option, dict):
                    continue
                for key, minimum in (("summary", 100), ("architectureDiagram", 240), ("totalMonthlyCost", 20)):
                    value = option.get(key)
                    if isinstance(value, str) and len(value) > minimum:
                        option[key] = value[: max(minimum, len(value) // 2)]
                        changed = True
                costs = option.get("costItems")
                if isinstance(costs, list) and len(costs) > 6:
                    del costs[6:]
                    changed = True
            if not changed:
                break
        if len(_json_bytes(bounded)) > maximum:
            raise BridgeError("stream_failed", "A StartChat input boundary exceeded the bounded bridge protocol.")
        bounded["trimmed"] = True
        return bounded
    milestones = bounded.get("milestones")
    while len(_json_bytes(bounded)) > maximum and isinstance(milestones, list) and len(milestones) > 1:
        milestones.pop(0)
    bounded.pop("latestText", None)
    if len(_json_bytes(bounded)) > maximum:
        bounded = {
            key: bounded[key]
            for key in ("type", "state", "sessionId", "taskId", "requestSeq", "error")
            if key in bounded
        }
        bounded["trimmed"] = True
    return bounded


def _project_stream_event(
    payload: Dict[str, Any],
    mode: str,
    request_seq: int,
    worker_role: str = "primary",
    worker_token: Optional[str] = None,
) -> Dict[str, Any]:
    result = _result(payload)
    state, wire_state = _state_from_result(result)
    metadata = _metadata_from_result(result)
    projection = {"type": "status", "requestSeq": request_seq, "time": int(time.time())}  # type: Dict[str, Any]
    if worker_role == "sideband":
        projection["workerRole"] = "sideband"
        if isinstance(worker_token, str) and worker_token:
            projection["workerToken"] = worker_token
    if state:
        projection["state"] = state
    if wire_state:
        projection["wireState"] = wire_state
    for key, value in (
        ("sessionId", _find_first(payload, "contextId", "context_id", "SessionId")),
        ("taskId", _find_first(payload, "taskId", "task_id")),
        ("iacCodeSessionId", _find_first(payload, "iacCodeSessionId", "iac_code_session_id")),
        ("requestId", _find_first(payload, "requestId", "request_id", "RequestId")),
    ):
        if isinstance(value, str) and value:
            projection[key] = sanitize_text(value, 240)

    input_required = _input_from_metadata(metadata)
    pending_permissions = _pending_permissions_from_metadata(metadata)
    if pending_permissions is not None:
        projection["pendingPermissions"] = [
            _permission_class(value, mode=mode, sideband=True) for value in pending_permissions
        ]
    if input_required is not None:
        sideband_ids = {
            value.get("inputId") for value in projection.get("pendingPermissions", []) if isinstance(value, dict)
        }
        sideband_input = input_required.get("inputId") in sideband_ids or _is_sideband_permission(
            metadata, input_required
        )
        projected_input = _permission_class(
            input_required,
            mode=mode,
            sideband=sideband_input,
        )
        projection["inputRequired"] = projected_input
        if sideband_input and "pendingPermissions" not in projection:
            projection["pendingPermissions"] = [projected_input]
        projection["type"] = "input-required"

    permission_wait = _safe_permission_wait(metadata)
    if permission_wait is not None:
        projection["permissionWait"] = permission_wait
        if projection["type"] == "status":
            projection["type"] = "permission-wait"

    permission_recovered = _safe_permission_recovered(metadata)
    if permission_recovered is not None:
        projection["permissionRecovered"] = permission_recovered
        if projection["type"] == "status":
            projection["type"] = "permission-recovered"

    milestones = []
    for item in _pipeline_events(metadata):
        if _normal_handoff_ready(item):
            projection["normalHandoffReady"] = True
        milestone = _safe_milestone(item)
        if milestone is not None and milestone not in milestones:
            milestones.append(milestone)
    if milestones:
        projection["milestones"] = milestones
        if projection["type"] == "status":
            projection["type"] = "milestone"

    permission_ack = _permission_ack_from_result(result)
    if permission_ack is not None:
        projection["permissionAck"] = permission_ack
        if projection["type"] == "status":
            projection["type"] = "permission-ack"

    artifact = _safe_artifact(result)
    if artifact is not None:
        projection["artifact"] = artifact
        if projection["type"] == "status":
            projection["type"] = "artifact"

    text = _message_text_from_result(result)
    assistant_final = metadata.get("assistantFinal")
    if text and isinstance(assistant_final, dict) and assistant_final.get("complete") is True:
        projection["type"] = "assistant-final"
        projection["finalText"] = sanitize_text(text, MAX_FINAL_TEXT_BYTES, True)
        projection["finalTextComplete"] = len(text.encode("utf-8")) <= MAX_FINAL_TEXT_BYTES
    elif text:
        # Store only a small snapshot in job state. Token deltas are not spooled
        # or returned to the outer Agent as individual events.
        projection["latestText"] = sanitize_text(text, 1000, True)

    raw_error = payload.get("error")
    if not isinstance(raw_error, dict):
        raw_error = result.get("error") if isinstance(result.get("error"), dict) else None
    if isinstance(raw_error, dict):
        projection["type"] = "failed"
        projection["state"] = "failed"
        projection["error"] = {
            "code": sanitize_text(str(raw_error.get("code") or raw_error.get("Code") or "StartChatFailed"), 160),
            "message": sanitize_text(
                str(raw_error.get("message") or raw_error.get("Message") or "StartChat failed."), 2000
            ),
        }
    elif state in TERMINAL_STATES:
        projection["type"] = "terminal"

    return _bound_projection(projection)


def _without_wait_boundaries(projection: Dict[str, Any]) -> Dict[str, Any]:
    projection = dict(projection)
    for key in ("inputRequired", "pendingPermissions", "permissionWait", "permissionRecovered"):
        projection.pop(key, None)
    if projection.get("type") in {"input-required", "permission-wait", "permission-recovered"}:
        projection["type"] = "status"
    return projection


def _project_managed_stream_event(
    payload: Dict[str, Any],
    summary: StreamSummary,
    mode: str,
    request_seq: int,
    worker_role: str,
    worker_token: Optional[str],
) -> Dict[str, Any]:
    projection = _project_stream_event(payload, mode, request_seq, worker_role, worker_token)
    if summary.state in TERMINAL_STATES:
        projection = _without_wait_boundaries(projection)
    return projection


def _append_projection(job_id: str, projection: Dict[str, Any]) -> None:
    root, job_path, spool = _job_paths(job_id)
    _secure_directory(root)
    projection = _bound_projection(projection)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        request_seq = projection.get("requestSeq")
        if isinstance(request_seq, int) and request_seq != job.get("activeRequestSeq"):
            return
        worker_role = projection.get("workerRole")
        worker_token = projection.get("workerToken")
        if worker_role == "sideband" and worker_token != job.get("sidebandWorkerToken"):
            return
        primary_terminal = job.get("primaryStreamTerminalSeen") is True or job.get("state") in TERMINAL_STATES
        if primary_terminal:
            projection = _without_wait_boundaries(projection)
        if projection.get("type") == "terminal" and worker_role != "sideband":
            # Do not publish an incomplete final result before EOF, but close
            # the primary stream's user-input ownership immediately. The
            # internal marker also prevents a concurrent sideband worker from
            # reopening the parent Pipeline while the primary worker exits.
            projection = _without_wait_boundaries(projection)
            job["primaryStreamTerminalSeen"] = True
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
            job.pop("permissionWait", None)
        identity_changed = False
        for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
            value = projection.get(key)
            if isinstance(value, str) and value and job.get(key) != value:
                job[key] = value
                identity_changed = True
        latest_text = projection.get("latestText")
        if isinstance(latest_text, str) and latest_text:
            job["latestText"] = latest_text
        projected_ack = projection.get("permissionAck")
        effective_ack = projected_ack if isinstance(projected_ack, dict) else job.get("permissionAck")
        in_flight_input_id = job.get("sidebandResponseInputId")
        acknowledged_input_ids = {value for value in job.get("acknowledgedPermissionIds", []) if isinstance(value, str)}
        if isinstance(effective_ack, dict) and isinstance(effective_ack.get("inputId"), str):
            acknowledged_input_ids.add(effective_ack["inputId"])
        seen_sideband_input_ids = {
            value for value in job.get("seenSidebandPermissionIds", []) if isinstance(value, str)
        }
        resolved_sideband_input_ids = {
            value for value in job.get("resolvedSidebandPermissionIds", []) if isinstance(value, str)
        }
        resolved_sideband_input_ids.update(acknowledged_input_ids)
        if isinstance(projection.get("pendingPermissions"), list):
            projected_pending_ids = {
                value.get("inputId")
                for value in projection["pendingPermissions"]
                if isinstance(value, dict) and isinstance(value.get("inputId"), str)
            }
            resolved_sideband_input_ids.update(seen_sideband_input_ids - projected_pending_ids)
            seen_sideband_input_ids.update(projected_pending_ids)
            job["seenSidebandPermissionIds"] = list(seen_sideband_input_ids)[-64:]
            job["resolvedSidebandPermissionIds"] = list(resolved_sideband_input_ids)[-64:]
            pending = [
                value
                for value in projection["pendingPermissions"]
                if not _permission_is_acknowledged(value, effective_ack)
                and value.get("inputId") != in_flight_input_id
                and value.get("inputId") not in acknowledged_input_ids
                and value.get("inputId") not in resolved_sideband_input_ids
            ]
            projection["pendingPermissions"] = pending
            if pending:
                job["pendingPermissions"] = pending
                current = job.get("inputRequired")
                pending_ids = {value.get("inputId") for value in pending if isinstance(value, dict)}
                if not isinstance(current, dict) or current.get("inputId") not in pending_ids:
                    job["inputRequired"] = pending[0]
            else:
                job.pop("pendingPermissions", None)
                current = job.get("inputRequired")
                if isinstance(current, dict) and current.get("permissionClass") == "sub_pipeline":
                    job.pop("inputRequired", None)
        input_required = projection.get("inputRequired")
        current_input = job.get("inputRequired")
        if (
            isinstance(input_required, dict)
            and isinstance(current_input, dict)
            and input_required.get("inputId") == current_input.get("inputId")
            and current_input.get("permissionClass") == "sub_pipeline"
        ):
            input_required = dict(input_required)
            input_required["permissionClass"] = "sub_pipeline"
            projection["inputRequired"] = input_required
        if isinstance(input_required, dict) and input_required.get("inputId") in resolved_sideband_input_ids:
            projection.pop("inputRequired", None)
            if projection.get("type") == "input-required":
                projection["type"] = "status"
        elif isinstance(input_required, dict) and input_required.get("inputId") == in_flight_input_id:
            projection.pop("inputRequired", None)
            if projection.get("type") == "input-required":
                projection["type"] = "status"
        elif _permission_is_acknowledged(input_required, effective_ack) or (
            isinstance(input_required, dict) and input_required.get("inputId") in acknowledged_input_ids
        ):
            projection.pop("inputRequired", None)
            if projection.get("type") == "input-required":
                projection["type"] = "permission-ack" if isinstance(projected_ack, dict) else "status"
        elif isinstance(input_required, dict):
            job["inputRequired"] = input_required
            job["state"] = "input-required"
        permission_wait = projection.get("permissionWait")
        if isinstance(permission_wait, dict):
            job["permissionWait"] = permission_wait
        permission_recovered = projection.get("permissionRecovered")
        if isinstance(permission_recovered, dict):
            job["permissionRecovered"] = permission_recovered
            job.pop("permissionWait", None)
            recovered_input_id = permission_recovered.get("inputId")
            current = job.get("inputRequired")
            if isinstance(current, dict) and current.get("inputId") == recovered_input_id:
                job.pop("inputRequired", None)
            remaining = [
                value
                for value in job.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") != recovered_input_id
            ]
            if remaining:
                job["pendingPermissions"] = remaining
            else:
                job.pop("pendingPermissions", None)
            if job.get("state") == "input-required" and not isinstance(job.get("inputRequired"), dict):
                job["state"] = "working"
        permission_ack = projection.get("permissionAck")
        if isinstance(permission_ack, dict):
            job["permissionAck"] = permission_ack
            input_id = permission_ack.get("inputId")
            if isinstance(input_id, str):
                history = job.setdefault("acknowledgedPermissionIds", [])
                if input_id not in history:
                    history.append(input_id)
                    del history[:-64]
            remaining = [
                value
                for value in job.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") != input_id
            ]
            if remaining:
                job["pendingPermissions"] = remaining
                job["inputRequired"] = remaining[0]
                job["state"] = "input-required"
            else:
                job.pop("pendingPermissions", None)
                current = job.get("inputRequired")
                if isinstance(current, dict) and current.get("inputId") == input_id:
                    job.pop("inputRequired", None)
                if worker_role == "sideband" and job.get("state") not in TERMINAL_STATES:
                    job["state"] = "working"
        artifact = projection.get("artifact")
        if isinstance(artifact, dict):
            artifacts = job.setdefault("artifacts", [])
            if artifact not in artifacts:
                artifacts.append(artifact)
                del artifacts[:-24]
        if projection.get("type") == "assistant-final" and isinstance(projection.get("finalText"), str):
            job["assistantFinal"] = projection["finalText"]
            job["assistantFinalComplete"] = projection.get("finalTextComplete") is True
        if projection.get("type") == "failed" and worker_role == "sideband":
            job["sidebandError"] = projection.get("error")
        elif projection.get("type") == "failed":
            job["state"] = "failed"
            job["error"] = projection.get("error")
        if projection.get("normalHandoffReady") is True and job.get("mode") == "pipeline":
            job["normalHandoffReady"] = True
            job["conversationMode"] = "normal"

        wire_projection = dict(projection)
        wire_projection.pop("latestText", None)
        wire_projection.pop("workerRole", None)
        wire_projection.pop("workerToken", None)
        meaningful = wire_projection.get("type") != "status" or identity_changed
        if meaningful:
            data = _json_bytes(wire_projection) + b"\n"
            current_size = spool.stat().st_size if spool.exists() else 0
            if current_size + len(data) > MAX_SPOOL_BYTES:
                raise BridgeError("stream_failed", "The bounded ROS Agent event spool is full.")
            with spool.open("ab") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if os.name != "nt":
                os.chmod(str(spool), 0o600)
        _atomic_json(job_path, job)


def _finish_job(
    job_id: str,
    request_seq: int,
    result: Dict[str, Any],
    worker_pid: int,
    expected_worker_pid: Optional[int] = None,
) -> bool:
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        if job.get("activeRequestSeq") != request_seq:
            return False
        if expected_worker_pid is not None:
            current_worker_pid = job.get("workerPid")
            worker_matches = (
                not isinstance(current_worker_pid, int)
                if expected_worker_pid == 0
                else current_worker_pid == expected_worker_pid
            )
            if (
                not worker_matches
                or job.get("state") in TERMINAL_STATES | {"turn-completed", "failed"}
                or isinstance(job.get("inputRequired"), dict)
            ):
                return False
        for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
            value = result.get(key)
            if isinstance(value, str) and value:
                job[key] = value
        state = result.get("state") if isinstance(result.get("state"), str) else "stream-ended"
        if state == "input-required":
            input_required = result.get("inputRequired")
            acknowledged_input_ids = {
                value for value in job.get("acknowledgedPermissionIds", []) if isinstance(value, str)
            }
            pending_permissions = [
                value
                for value in result.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") not in acknowledged_input_ids
            ]
            stale_sideband_input = (
                isinstance(input_required, dict)
                and input_required.get("permissionClass") == "sub_pipeline"
                and input_required.get("inputId") in acknowledged_input_ids
            )
            if isinstance(input_required, dict) and not stale_sideband_input:
                job["inputRequired"] = input_required
            elif pending_permissions:
                job["inputRequired"] = pending_permissions[0]
            else:
                job.pop("inputRequired", None)
            if pending_permissions:
                job["pendingPermissions"] = pending_permissions
            else:
                job.pop("pendingPermissions", None)
            if stale_sideband_input and not pending_permissions:
                state = "failed"
                job["error"] = {
                    "code": "stream_detached",
                    "message": "The parent Pipeline StartChat stream ended without a terminal result.",
                    "retryable": True,
                }
        elif state == "turn-completed":
            job["finalText"] = result.get("finalText", "")
            job["finalTextComplete"] = result.get("finalTextComplete") is True
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
        elif state in TERMINAL_STATES:
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
        if isinstance(result.get("pipelineResult"), dict):
            job["pipelineResult"] = result["pipelineResult"]
        if result.get("normalHandoffReady") is True and job.get("mode") == "pipeline":
            job["normalHandoffReady"] = True
            job["conversationMode"] = "normal"
        if isinstance(result.get("permissionAck"), dict):
            job["permissionAck"] = result["permissionAck"]
        if isinstance(result.get("permissionWait"), dict):
            job["permissionWait"] = result["permissionWait"]
        if isinstance(result.get("permissionRecovered"), dict):
            job["permissionRecovered"] = result["permissionRecovered"]
            job.pop("permissionWait", None)
        if isinstance(result.get("error"), dict):
            job["error"] = result["error"]
        elif state == "failed" and not isinstance(job.get("error"), dict):
            failure_text = result.get("latestText") or job.get("latestText")
            job["error"] = {
                "code": "remote_task_failed",
                "message": sanitize_text(failure_text, 2000)
                if isinstance(failure_text, str) and failure_text
                else "The remote StartChat task failed without a structured error.",
            }
        if isinstance(result.get("artifacts"), list):
            artifacts = job.setdefault("artifacts", [])
            for artifact in result["artifacts"]:
                if isinstance(artifact, dict) and artifact not in artifacts:
                    artifacts.append(artifact)
            del artifacts[:-24]
        job["state"] = state
        job.pop("primaryStreamTerminalSeen", None)
        if state == "completed" and job.get("mode") == "pipeline":
            # Selling Pipeline publishes a normal-chat handoff before its
            # terminal event. Preserve a conservative fallback for gateways
            # that coalesce that event out of the final SSE projection.
            job["normalHandoffReady"] = True
            job["conversationMode"] = "normal"
        job["workerExitedAt"] = int(time.time())
        if job.get("workerPid") == worker_pid:
            job.pop("workerPid", None)
        boundary = {
            "type": "result-boundary",
            "requestSeq": request_seq,
            "state": state,
            "time": int(time.time()),
        }
        for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
            if isinstance(job.get(key), str):
                boundary[key] = job[key]
        data = _json_bytes(boundary) + b"\n"
        current_size = spool.stat().st_size if spool.exists() else 0
        if current_size + len(data) <= MAX_SPOOL_BYTES:
            with spool.open("ab") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        _atomic_json(job_path, job)
    _touch_manager_activity()
    return True


def _finish_sideband_job(
    job_id: str,
    request_seq: int,
    worker_token: str,
    result: Dict[str, Any],
    worker_pid: int,
) -> None:
    root, job_path, _spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        if job.get("activeRequestSeq") != request_seq or job.get("sidebandWorkerToken") != worker_token:
            return
        for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
            value = result.get(key)
            if isinstance(value, str) and value:
                job[key] = value

        expected_permission = job.get("sidebandResponse")
        expected_response = job.get("lastPermissionResponse")
        acknowledgement = result.get("permissionAck")
        acknowledged = (
            isinstance(expected_response, dict)
            and isinstance(acknowledgement, dict)
            and _permission_response_is_acknowledged(expected_response, acknowledgement)
        )
        if acknowledged:
            job["permissionAck"] = acknowledgement
            acknowledged_input_id = acknowledgement.get("inputId")
            if isinstance(acknowledged_input_id, str):
                history = job.setdefault("acknowledgedPermissionIds", [])
                if acknowledged_input_id not in history:
                    history.append(acknowledged_input_id)
                    del history[:-64]
                resolved = job.setdefault("resolvedSidebandPermissionIds", [])
                if acknowledged_input_id not in resolved:
                    resolved.append(acknowledged_input_id)
                    del resolved[:-64]

        parent_terminal = job.get("state") in TERMINAL_STATES or job.get("primaryStreamTerminalSeen") is True
        if acknowledged and not parent_terminal:
            input_id = acknowledgement.get("inputId")
            remaining = [
                value
                for value in job.get("pendingPermissions", [])
                if isinstance(value, dict) and value.get("inputId") != input_id
            ]
            if remaining:
                job["pendingPermissions"] = remaining
                job["inputRequired"] = remaining[0]
                job["state"] = "input-required"
            else:
                job.pop("pendingPermissions", None)
                current = job.get("inputRequired")
                if isinstance(current, dict) and current.get("inputId") == input_id:
                    job.pop("inputRequired", None)
                if job.get("state") not in TERMINAL_STATES:
                    job["state"] = "working"
            job.pop("sidebandError", None)
        elif not acknowledged and not parent_terminal:
            if isinstance(expected_permission, dict):
                pending = [value for value in job.get("pendingPermissions", []) if isinstance(value, dict)]
                expected_input_id = expected_permission.get("inputId")
                if not any(value.get("inputId") == expected_input_id for value in pending):
                    pending.insert(0, expected_permission)
                job["pendingPermissions"] = pending
                job["inputRequired"] = expected_permission
                job["state"] = "input-required"
            raw_error = result.get("error")
            job["sidebandError"] = (
                raw_error
                if isinstance(raw_error, dict)
                else {
                    "code": "permission_not_acknowledged",
                    "message": "The Pipeline permission response ended without an accepted acknowledgement.",
                    "retryable": True,
                }
            )
        elif acknowledged:
            job.pop("sidebandError", None)

        result_state = result.get("state") if isinstance(result.get("state"), str) else None
        if (
            acknowledged
            and isinstance(expected_permission, dict)
            and expected_permission.get("permissionClass") == "pipeline"
            and not parent_terminal
            and result_state in TERMINAL_STATES | {"turn-completed"}
        ):
            # A top-level Pipeline permission response can carry the Pipeline's
            # terminal result on the sideband StartChat stream. Persist that
            # result so follow does not wait forever after both workers exit.
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
            job["state"] = result_state
            if result_state == "turn-completed":
                job["finalText"] = result.get("finalText", "")
                job["finalTextComplete"] = result.get("finalTextComplete") is True
            if isinstance(result.get("pipelineResult"), dict):
                job["pipelineResult"] = result["pipelineResult"]
            if result.get("normalHandoffReady") is True or (
                result_state == "completed" and job.get("mode") == "pipeline"
            ):
                job["normalHandoffReady"] = True
                job["conversationMode"] = "normal"
            if isinstance(result.get("error"), dict):
                job["error"] = result["error"]
            if isinstance(result.get("artifacts"), list):
                artifacts = job.setdefault("artifacts", [])
                for artifact in result["artifacts"]:
                    if isinstance(artifact, dict) and artifact not in artifacts:
                        artifacts.append(artifact)
                del artifacts[:-24]

        job["sidebandWorkerExitedAt"] = int(time.time())
        if job.get("sidebandWorkerPid") == worker_pid:
            job.pop("sidebandWorkerPid", None)
        job.pop("sidebandWorkerToken", None)
        job.pop("sidebandResponseInputId", None)
        job.pop("sidebandResponse", None)
        _atomic_json(job_path, job)
    _touch_manager_activity()


def _fail_job(
    job_id: str,
    request_seq: int,
    error: BridgeError,
    worker_pid: int,
    expected_worker_pid: Optional[int] = None,
) -> bool:
    result = {
        "ok": False,
        "state": "failed",
        "error": {
            "code": error.code,
            "message": sanitize_text(error.message, 3000),
            "retryable": error.retryable,
        },
    }
    return _finish_job(job_id, request_seq, result, worker_pid, expected_worker_pid)


def _fail_sideband_job(
    job_id: str,
    request_seq: int,
    worker_token: str,
    error: BridgeError,
    worker_pid: int,
) -> None:
    result = {
        "ok": False,
        "state": "failed",
        "error": {
            "code": error.code,
            "message": sanitize_text(error.message, 3000),
            "retryable": error.retryable,
        },
    }
    _finish_sideband_job(job_id, request_seq, worker_token, result, worker_pid)


def _read_spool(spool: pathlib.Path) -> List[Dict[str, Any]]:
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


def _follow_timeout_result(job_id: str, start_cursor: int) -> Optional[Dict[str, Any]]:
    """Persist and snapshot the bounded observation returned by a timed-out follow call.

    The marker is local bridge state, not a StartChat query or a remote progress
    event.  Recording it gives each visible heartbeat a distinct spool cursor,
    so an outer headless Agent can continue observing a long-running Pipeline
    without issuing an identical tool call indefinitely.  The result snapshot
    stays under the same job lock so it cannot combine this cursor with a newer
    terminal or input boundary while omitting intervening step events.
    """

    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        values = _read_spool(spool)
        if job.get("state") in TERMINAL_STATES | {"turn-completed", "failed"} or isinstance(
            job.get("inputRequired"), dict
        ):
            return None
        if any(
            isinstance(milestone, dict) and milestone.get("eventType") in STEP_BOUNDARY_EVENT_TYPES
            for item in values[max(0, int(start_cursor)) :]
            for milestone in item.get("milestones", [])
        ):
            return None
        marker = {
            "type": "follow-heartbeat",
            "requestSeq": job.get("activeRequestSeq"),
            "time": int(time.time()),
        }
        data = _json_bytes(marker) + b"\n"
        current_size = spool.stat().st_size if spool.exists() else 0
        if current_size + len(data) > MAX_SPOOL_BYTES:
            raise BridgeError("stream_failed", "The bounded ROS Agent event spool is full.")
        with spool.open("ab") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            os.chmod(str(spool), 0o600)
        return _job_result(
            job_id,
            start_cursor,
            len(values) + 1,
            boundary_reached=False,
            timed_out=True,
        )


def _coordinate_label(milestone: Dict[str, Any]) -> str:
    event_type = str(milestone.get("eventType") or "")
    if event_type.startswith("candidate_step_"):
        candidate = milestone.get("candidate")
        step = milestone.get("candidateStep") or milestone.get("step")
        candidate_name = ""
        if isinstance(candidate, dict):
            candidate_name = sanitize_text(candidate.get("name") or candidate.get("id"), 100)
        step_label = ""
        if isinstance(step, dict):
            step_label = sanitize_text(step.get("name") or step.get("id"), 100)
            index = step.get("index")
            total = step.get("total")
            if isinstance(index, int) and isinstance(total, int):
                step_label = "{}/{} {}".format(index, total, step_label).strip()
        if candidate_name and step_label:
            return "{} · {}".format(candidate_name, step_label)
        if candidate_name or step_label:
            return candidate_name or step_label
    for key in ("candidateStep", "step", "parentStep", "candidate"):
        value = milestone.get(key)
        if not isinstance(value, dict):
            continue
        name = sanitize_text(value.get("name") or value.get("id"), 120)
        index = value.get("index")
        total = value.get("total")
        if isinstance(index, int) and isinstance(total, int):
            return "{}/{} {}".format(index, total, name).strip()
        if name:
            return name
    return ""


def _format_conclusion(summary: Any, language: str) -> str:
    if not isinstance(summary, dict):
        return ""
    parts = []
    requirement = sanitize_text(summary.get("requirementSummary"), 180)
    region = sanitize_text(summary.get("region"), 80)
    if requirement:
        parts.append(requirement)
    if region:
        parts.append(("\u5730\u57df " if language == "zh" else "region ") + region)
    resources = summary.get("resources")
    if isinstance(resources, list):
        names = []
        for item in resources[:6]:
            if not isinstance(item, dict):
                continue
            product = sanitize_text(item.get("product"), 60)
            action = sanitize_text(item.get("action"), 32)
            if language == "zh":
                action = {
                    "create": "\u65b0\u5efa",
                    "use_existing": "\u590d\u7528",
                    "reference": "\u5f15\u7528",
                    "forbid": "\u7981\u6b62",
                }.get(action, action)
            if product:
                names.append("{} ({})".format(product, action) if action else product)
        if names:
            parts.append(("\u8d44\u6e90 " if language == "zh" else "resources ") + "\u3001".join(names))
    candidates = summary.get("candidates")
    if isinstance(candidates, list):
        names = []
        for item in candidates[:4]:
            if not isinstance(item, dict):
                continue
            name = sanitize_text(item.get("name"), 80)
            estimate = sanitize_text(item.get("monthlyEstimate"), 80)
            if name:
                names.append("{} ({})".format(name, estimate) if estimate else name)
        if names:
            count = summary.get("candidateCount")
            prefix = (
                "{} \u4e2a\u5019\u9009\u65b9\u6848 ".format(count)
                if language == "zh"
                else "{} candidates ".format(count)
            )
            parts.append(prefix + "\u3001".join(names))
    return sanitize_text(("\uff1b" if language == "zh" else "; ").join(parts), 520)


def _format_user_update(milestone: Dict[str, Any], language: str) -> str:
    event_type = milestone.get("eventType")
    detail = _coordinate_label(milestone) or sanitize_text(milestone.get("message"), 240)
    labels = {
        "zh": {
            "step_started": "\u6b65\u9aa4\u5f00\u59cb",
            "step_completed": "\u6b65\u9aa4\u5b8c\u6210",
            "step_failed": "\u6b65\u9aa4\u5931\u8d25",
            "candidate_step_started": "\u5019\u9009\u6b65\u9aa4\u5f00\u59cb",
            "candidate_step_completed": "\u5019\u9009\u6b65\u9aa4\u5b8c\u6210",
            "candidate_step_failed": "\u5019\u9009\u6b65\u9aa4\u5931\u8d25",
        },
        "en": {
            "step_started": "Step started",
            "step_completed": "Step completed",
            "step_failed": "Step failed",
            "candidate_step_started": "Candidate step started",
            "candidate_step_completed": "Candidate step completed",
            "candidate_step_failed": "Candidate step failed",
        },
    }
    label = labels.get(language, labels["en"]).get(str(event_type), sanitize_text(str(event_type), 80))
    separator = "\uff1a" if language == "zh" else ": "
    conclusion = _format_conclusion(milestone.get("conclusionSummary"), language)
    if conclusion:
        detail = "{}{}{}".format(
            detail,
            "\uff1b\u7ed3\u8bba\uff1a" if language == "zh" else "; conclusion: ",
            conclusion,
        )
    return sanitize_text(label + (separator + detail if detail else ""), 720)


def _bound_follow_result(result: Dict[str, Any]) -> Dict[str, Any]:
    while len(_json_bytes(result)) > MAX_FOLLOW_BYTES:
        milestones = result.get("milestones")
        artifacts = result.get("artifacts")
        if isinstance(milestones, list) and len(milestones) > 1:
            milestones.pop(0)
        elif isinstance(artifacts, list) and len(artifacts) > 1:
            artifacts.pop(0)
        elif isinstance(result.get("latestText"), str):
            result["latestText"] = _truncate_utf8(result["latestText"], 300)
        elif isinstance(result.get("finalText"), str) and len(result["finalText"].encode("utf-8")) > 2000:
            result["finalText"] = _truncate_utf8(result["finalText"], 2000)
            result["finalTextComplete"] = False
        else:
            raise BridgeError("stream_failed", "The ROS Agent follow result exceeded its bounded protocol.")
    return result


def _job_result(
    job_id: str,
    start_cursor: int,
    end_cursor: Optional[int] = None,
    boundary_reached: bool = False,
    timed_out: bool = False,
) -> Dict[str, Any]:
    _root, job_path, spool = _job_paths(job_id)
    job = _load_state_json(job_path)
    values = _read_spool(spool)
    start = max(0, int(start_cursor))
    end = len(values) if end_cursor is None else min(len(values), max(start, int(end_cursor)))
    unseen = values[start:end]
    milestones = []
    folded = {}  # type: Dict[str, int]
    seen = set()
    for item in unseen:
        item_seq = item.get("requestSeq")
        if isinstance(item_seq, int) and item_seq != job.get("activeRequestSeq"):
            folded["stale_request_event"] = folded.get("stale_request_event", 0) + 1
            continue
        for milestone in item.get("milestones", []):
            if not isinstance(milestone, dict):
                continue
            signature = _json_bytes(milestone)
            if signature in seen:
                folded["duplicate_milestone"] = folded.get("duplicate_milestone", 0) + 1
                continue
            seen.add(signature)
            milestones.append(milestone)
    job_state = str(job.get("state") or "unknown")
    has_result_gate = job_state in TERMINAL_STATES | {"turn-completed", "failed"} or isinstance(
        job.get("inputRequired"), dict
    )
    state = job_state if has_result_gate else ("working" if boundary_reached else job_state)
    result = {
        "ok": state != "failed" and not isinstance(job.get("sidebandError"), dict),
        "jobId": job_id,
        "state": state,
        "mode": job.get("mode"),
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "cursor": end,
        "turn": int(job.get("turn") or 1),
        "milestones": milestones[-MAX_FOLLOW_EVENTS:],
        "folded": folded,
    }  # type: Dict[str, Any]
    for key in ("sessionId", "taskId", "iacCodeSessionId", "requestId", "wireState"):
        if isinstance(job.get(key), str):
            result[key] = job[key]
    if job.get("conversationMode") in SUPPORTED_AGENT_MODES:
        result["conversationMode"] = job["conversationMode"]
    if job.get("normalHandoffReady") is True:
        result["normalHandoffReady"] = True
    if isinstance(job.get("permissionWait"), dict):
        result["permissionWait"] = job["permissionWait"]
        result["presentationRequired"] = True
    if isinstance(job.get("permissionRecovered"), dict):
        result["permissionRecovered"] = job["permissionRecovered"]
        result["presentationRequired"] = True
    if boundary_reached:
        updates = [
            _format_user_update(value, result["preferredLanguage"])
            for value in result["milestones"]
            if value.get("eventType") in STEP_BOUNDARY_EVENT_TYPES
        ]
        if updates:
            result["boundaryReached"] = True
            result["presentationRequired"] = True
            result["userUpdates"] = updates
    artifacts = list(job.get("artifacts") or [])[-MAX_FOLLOW_EVENTS:]
    if artifacts and not timed_out and (not boundary_reached or has_result_gate):
        result["artifacts"] = artifacts
    if isinstance(job.get("inputRequired"), dict):
        result["inputRequired"] = _permission_with_ref(job["inputRequired"])
        if isinstance(job.get("pendingPermissions"), list):
            result["pendingPermissions"] = [
                _permission_with_ref(value) for value in job["pendingPermissions"] if isinstance(value, dict)
            ]
        result["presentationRequired"] = True
    if state == "turn-completed":
        result["finalText"] = job.get("finalText", "")
        result["finalTextComplete"] = job.get("finalTextComplete") is True
        result["presentationRequired"] = True
    if state in TERMINAL_STATES and isinstance(job.get("pipelineResult"), dict):
        result["pipelineResult"] = job["pipelineResult"]
        result["presentationRequired"] = True
    if state == "failed" and isinstance(job.get("error"), dict):
        result["error"] = job["error"]
        result["presentationRequired"] = True
    elif isinstance(job.get("sidebandError"), dict):
        result["error"] = job["sidebandError"]
        result["presentationRequired"] = True
    if isinstance(job.get("permissionAck"), dict):
        result["permissionAck"] = job["permissionAck"]
        if state == "permission-responded":
            result["presentationRequired"] = True
    if timed_out:
        elapsed = max(0, int(time.time()) - int(job.get("turnStartedAt") or job.get("createdAt") or time.time()))
        result["followTimedOut"] = True
        result["heartbeat"] = (
            "ROS Agent \u4ecd\u5728\u5904\u7406\u4e2d\uff08{} \u79d2\uff09\u3002".format(elapsed)
            if result["preferredLanguage"] == "zh"
            else "ROS Agent is still working ({}s).".format(elapsed)
        )
        result["presentationRequired"] = True
        if isinstance(job.get("latestText"), str):
            result["latestText"] = job["latestText"]
    return _bound_follow_result(result)


def _follow_ready_result(job_id: str, start_cursor: int) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        values = _read_spool(spool)
        job = _load_state_json(job_path)
        has_step_boundary = any(
            isinstance(milestone, dict) and milestone.get("eventType") in STEP_BOUNDARY_EVENT_TYPES
            for item in values[start_cursor:]
            for milestone in item.get("milestones", [])
        )
        state = job.get("state")
        if (
            has_step_boundary
            or state in TERMINAL_STATES | {"turn-completed", "failed"}
            or isinstance(job.get("inputRequired"), dict)
            or isinstance(job.get("sidebandError"), dict)
        ):
            return (
                _job_result(
                    job_id,
                    start_cursor,
                    len(values),
                    boundary_reached=has_step_boundary,
                ),
                job,
            )
        if state == "permission-responded" and job.get("pendingPermissions"):
            return _job_result(job_id, start_cursor, len(values)), job
        return None, job


def _follow_job_local(job_id: str, cursor: int, wait_seconds: float) -> Dict[str, Any]:
    root = _job_paths(job_id)[0]
    _secure_directory(root)
    wait_seconds = max(0.0, min(float(wait_seconds), MAX_FOLLOW_SECONDS))
    deadline = time.monotonic() + wait_seconds
    start_cursor = max(0, int(cursor))
    while True:
        ready_result, job = _follow_ready_result(job_id, start_cursor)
        if ready_result is not None:
            return ready_result
        state = job.get("state")
        sideband_worker_pid = job.get("sidebandWorkerPid")
        sideband_worker_token = job.get("sidebandWorkerToken")
        if (
            isinstance(sideband_worker_pid, int)
            and isinstance(sideband_worker_token, str)
            and not _pid_alive(sideband_worker_pid)
        ):
            error = BridgeError(
                "worker_exited", "The Pipeline permission response worker exited before acknowledgement.", True
            )
            _fail_sideband_job(
                job_id,
                int(job.get("activeRequestSeq") or 0),
                sideband_worker_token,
                error,
                sideband_worker_pid,
            )
            continue
        worker_pid = job.get("workerPid")
        if isinstance(worker_pid, int) and not _pid_alive(worker_pid):
            error = BridgeError("worker_exited", "The StartChat worker exited before reaching a boundary.", True)
            _fail_job(
                job_id,
                int(job.get("activeRequestSeq") or 0),
                error,
                worker_pid,
                expected_worker_pid=worker_pid,
            )
            continue
        if state == "permission-responded" and not isinstance(worker_pid, int):
            error = BridgeError(
                "stream_detached",
                "Permission was accepted, but the StartChat stream ended before the next Pipeline boundary.",
                True,
            )
            _fail_job(
                job_id,
                int(job.get("activeRequestSeq") or 0),
                error,
                0,
                expected_worker_pid=0,
            )
            continue
        if time.monotonic() >= deadline:
            timeout_result = _follow_timeout_result(job_id, start_cursor)
            if timeout_result is None:
                continue
            return timeout_result
        time.sleep(0.1)


def _run_start_chat(
    args: argparse.Namespace,
    workspace: pathlib.Path,
    prompt: str,
    client_context: Optional[str],
    attachments: List[Dict[str, str]],
) -> Dict[str, Any]:
    return _consume_start_chat(args, workspace, prompt, client_context, attachments)


def _consume_start_chat(
    args: argparse.Namespace,
    workspace: pathlib.Path,
    prompt: str,
    client_context: Optional[str],
    attachments: List[Dict[str, str]],
    *,
    summary_mode: Optional[str] = None,
    on_payload: Optional[Any] = None,
) -> Dict[str, Any]:
    summary = StreamSummary(args.session_id, mode=summary_mode or args.mode)
    diagnostics = []  # type: List[str]

    if getattr(args, "transport", "aliyun_cli") == "code":
        response = _open_code_request(
            "StartChat",
            build_start_chat_parameters(args, prompt, client_context, attachments),
            str(args.endpoint),
            args.profile,
            args.region_id,
            args.aliyun_path,
            int(args.connect_timeout),
            int(args.read_timeout),
            credential_source=getattr(args, "credential_source", None),
        )
        try:
            content_type = str(response.headers.get("Content-Type", "")).lower()
            if "text/event-stream" not in content_type:
                raw = response.read(MAX_DIAGNOSTIC_BYTES + 1)
                detail = sanitize_text(raw.decode("utf-8", "replace"), 2000)
                raise BridgeError(
                    "stream_failed",
                    detail or "Alibaba Cloud ROS StartChat did not return an SSE stream.",
                    True,
                )
            for payload, raw in iter_sse_payloads(_response_text_lines(response)):
                if payload is None:
                    summary.malformed_event_count += 1
                    if raw:
                        diagnostics.append(raw)
                    continue
                summary.apply(payload)
                if on_payload is not None:
                    on_payload(payload, summary)
        except BridgeError:
            raise
        except Exception as exc:
            raise BridgeError(
                "stream_failed",
                "Alibaba Cloud ROS StartChat stream ended unexpectedly.",
                True,
            ) from exc
        finally:
            response.close()
        return summary.to_result(0, "\n".join(diagnostics))

    command = build_command(args, prompt, client_context, attachments)
    with tempfile.TemporaryFile(mode="w+b") as stderr_file:
        try:
            process = subprocess.Popen(
                command,
                cwd=str(workspace),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=stderr_file,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            raise BridgeError("cli_start_failed", "Alibaba Cloud CLI could not be started.", True) from exc
        assert process.stdout is not None
        try:
            for payload, raw in iter_cli_plugin_payloads(process.stdout):
                if payload is None:
                    summary.malformed_event_count += 1
                    if raw:
                        diagnostics.append(raw)
                else:
                    summary.apply(payload)
                    if on_payload is not None:
                        on_payload(payload, summary)
            return_code = process.wait()
        except KeyboardInterrupt as exc:
            _stop_process(process)
            raise BridgeError(
                "interrupted",
                "StartChat was interrupted locally; remote cancellation is not confirmed.",
            ) from exc
        except BaseException:
            _stop_process(process)
            raise
        finally:
            process.stdout.close()
        stderr_file.seek(0)
        stderr_text = stderr_file.read(MAX_DIAGNOSTIC_BYTES).decode("utf-8", "replace")
    if diagnostics and not stderr_text:
        stderr_text = "\n".join(diagnostics)
    return summary.to_result(return_code, stderr_text)


def run_chat(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = _workspace(args.cwd)
    prompt = read_prompt(workspace, args.prompt_file)
    client_context = load_client_context(workspace, args.client_context_file)
    attachments = load_attachments(workspace, args.attachments_file)
    return _run_start_chat(args, workspace, prompt, client_context, attachments)


def run_respond(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = _workspace(args.cwd)
    query, response = load_permission_query(
        workspace,
        args.input_file,
        args.decision,
        args.session_id,
        args.mode,
    )
    # Keep the Query as the sole control payload. ClientContext and attachments
    # would cause the ROS gateway to wrap or augment the text before A2A delivery.
    result = _run_start_chat(args, workspace, query, None, [])
    result["permissionResponse"] = response
    return _bound_result(result)


def _stop_process(process: Any) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _spawn_worker(job_id: str, request: Dict[str, Any]) -> int:
    root, job_path, _spool = _job_paths(job_id)
    request_token = uuid.uuid4().hex
    request_path = root / ("request-{}.json".format(request_token))
    _atomic_json(request_path, request)
    canonical_job_id = uuid.UUID(job_id).hex
    command = [
        sys.executable,
        str(pathlib.Path(__file__).resolve()),
        "_worker",
        "--job-id",
        canonical_job_id,
        "--request-token",
        request_token,
    ]
    log_path = root / "worker.log"
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    if log_path.exists() and log_path.stat().st_size > MAX_DIAGNOSTIC_BYTES:
        with log_path.open("wb"):
            pass
    try:
        with log_path.open("ab", buffering=0) as log:
            if os.name != "nt":
                os.chmod(str(log_path), 0o600)
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=os.name != "nt",
                creationflags=creationflags,
            )
    except OSError as exc:
        with contextlib.suppress(OSError):
            request_path.unlink()
        request_seq = int(request.get("requestSeq") or 0)
        error = BridgeError("worker_start_failed", "The StartChat worker could not be started.", True)
        worker_token = request.get("workerToken")
        if request.get("workerRole") == "sideband" and isinstance(worker_token, str):
            _fail_sideband_job(job_id, request_seq, worker_token, error, 0)
        else:
            _fail_job(job_id, request_seq, error, 0)
        raise BridgeError("worker_start_failed", "The StartChat worker could not be started.", True) from exc
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        if request.get("workerRole") == "sideband":
            job["sidebandWorkerPid"] = process.pid
            job["sidebandWorkerStartedAt"] = int(time.time())
        else:
            job["workerPid"] = process.pid
            job["workerStartedAt"] = int(time.time())
        _atomic_json(job_path, job)
    return process.pid


def _request_from_job(job: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    return {
        "requestSeq": job["activeRequestSeq"],
        "workspace": job["workspace"],
        "prompt": prompt,
        "mode": job["mode"],
        "summaryMode": job.get("conversationMode") or job["mode"],
        "endpoint": job["endpoint"],
        # Jobs created before transport selection existed used the native CLI.
        "transport": job.get("transport", "aliyun_cli"),
        "aliyunCLIExecutionMode": job.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE),
        "sessionId": job.get("sessionId"),
        "regionId": job.get("regionId"),
        "profile": job.get("profile"),
        "credentialSource": job.get("credentialSource"),
        "noThinking": job.get("noThinking") is True,
        "connectTimeout": job.get("connectTimeout", 10),
        "readTimeout": job.get("readTimeout", DEFAULT_READ_TIMEOUT_SECONDS),
        "aliyunPath": job.get("aliyunPath", "aliyun"),
        "clientContext": None,
        "attachments": [],
    }


def _start_job_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _trusted_manager_workspace(str(payload.get("workspace") or ""))
    prompt = payload.get("prompt")
    mode = payload.get("mode")
    endpoint = payload.get("endpoint")
    transport = payload.get("transport", DEFAULT_TRANSPORT)
    cli_execution_mode = payload.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE)
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise BridgeError("invalid_input", "The StartChat prompt is empty or too large.")
    if mode not in SUPPORTED_AGENT_MODES:
        raise BridgeError("invalid_input", "The ROS Agent mode is invalid.")
    if not isinstance(endpoint, str):
        raise BridgeError("invalid_input", "The ROS endpoint is invalid.")
    _endpoint_kind(endpoint)
    if transport not in SUPPORTED_TRANSPORTS:
        raise BridgeError("invalid_input", "The ROS transport is invalid.")
    if cli_execution_mode not in SUPPORTED_ALIYUN_CLI_EXECUTION_MODES:
        raise BridgeError("invalid_input", "The aliyun CLI execution mode is invalid.")
    if transport != "aliyun_cli" and cli_execution_mode != DEFAULT_ALIYUN_CLI_EXECUTION_MODE:
        raise BridgeError("invalid_input", "The aliyun CLI execution mode requires the aliyun_cli transport.")
    if transport == "aliyun_cli" and cli_execution_mode == "remote":
        if _endpoint_kind(endpoint) != "aliyun":
            raise BridgeError("invalid_input", "Remote aliyun CLI execution requires a public aliyuncs.com endpoint.")
        if payload.get("profile"):
            raise BridgeError("invalid_input", "Remote aliyun CLI execution does not accept a local Profile.")
        if payload.get("clientContext") is not None:
            raise BridgeError("unsupported_input", "The ROS CLI plugin does not support ClientContext.")
    aliyun_path = str(payload.get("aliyunPath") or "aliyun")
    if transport == "aliyun_cli":
        resolve_aliyun(aliyun_path)
    else:
        _load_code_sdk()
    job_id = uuid.uuid4().hex
    root, job_path, spool = _job_paths(job_id)
    _secure_directory(root)
    spool.touch()
    if os.name != "nt":
        os.chmod(str(spool), 0o600)
    job = {
        "schemaVersion": JOB_SCHEMA_VERSION,
        "jobId": job_id,
        "workspace": str(workspace),
        "mode": mode,
        "endpoint": endpoint,
        "transport": transport,
        "aliyunCLIExecutionMode": cli_execution_mode,
        "regionId": payload.get("regionId"),
        "profile": payload.get("profile"),
        "credentialSource": payload.get("credentialSource"),
        "noThinking": payload.get("noThinking") is True,
        "connectTimeout": int(payload.get("connectTimeout") or 10),
        "readTimeout": int(payload.get("readTimeout") or DEFAULT_READ_TIMEOUT_SECONDS),
        "aliyunPath": aliyun_path,
        "preferredLanguage": _preferred_language(prompt),
        "state": "submitted",
        "turn": 1,
        "activeRequestSeq": 1,
        "createdAt": int(time.time()),
        "turnStartedAt": int(time.time()),
        "artifacts": [],
    }  # type: Dict[str, Any]
    _atomic_json(job_path, job)
    request = _request_from_job(job, prompt)
    request["clientContext"] = payload.get("clientContext")
    request["attachments"] = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
    worker_pid = _spawn_worker(job_id, request)
    return {
        "ok": True,
        "jobId": job_id,
        "state": "submitted",
        "mode": mode,
        "preferredLanguage": job["preferredLanguage"],
        "cursor": 0,
        "turn": 1,
        "workerPid": worker_pid,
    }


def _continue_job_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(payload.get("jobId") or "")
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        prompt = payload.get("prompt")
        if not isinstance(prompt, str):
            prompt_file = payload.get("promptFile")
            if not isinstance(prompt_file, str):
                raise BridgeError("invalid_input", "continue requires a prompt file.")
            prompt = read_prompt(pathlib.Path(job["workspace"]), prompt_file)
        if not prompt.strip() or len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise BridgeError("invalid_input", "The continuation prompt is empty or too large.")
        if isinstance(job.get("workerPid"), int) and _pid_alive(job["workerPid"]):
            raise BridgeError("job_busy", "The current StartChat request is still running.", True)
        session_id = job.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            raise BridgeError("job_not_ready", "The ROS Agent job has not received a SessionId yet.", True)
        pending = job.get("inputRequired")
        if isinstance(pending, dict) and pending.get("kind") == "permission":
            raise BridgeError("input_response_mismatch", "A permission must be answered with respond, not continue.")
        pipeline_handoff = (
            job.get("mode") == "pipeline"
            and job.get("state") == "completed"
            and (job.get("normalHandoffReady") is True or job.get("conversationMode") == "normal")
        )
        if not isinstance(pending, dict) and job.get("state") != "turn-completed" and not pipeline_handoff:
            raise BridgeError(
                "input_response_mismatch", "The ROS Agent job is not waiting for a natural-language message."
            )
        cursor = len(_read_spool(spool))
        if job.get("state") == "turn-completed" or pipeline_handoff:
            job["turn"] = int(job.get("turn") or 1) + 1
            job["turnStartedAt"] = int(time.time())
            job.pop("finalText", None)
            job.pop("finalTextComplete", None)
        if pipeline_handoff:
            previous_task_id = job.pop("taskId", None)
            if isinstance(previous_task_id, str):
                history = job.setdefault("taskHistory", [])
                if previous_task_id not in history:
                    history.append(previous_task_id)
            job["conversationMode"] = "normal"
            job.pop("pipelineResult", None)
        job["activeRequestSeq"] = int(job.get("activeRequestSeq") or 0) + 1
        job["state"] = "submitted"
        job.pop("inputRequired", None)
        job.pop("error", None)
        job.pop("permissionAck", None)
        _atomic_json(job_path, job)
    worker_pid = _spawn_worker(job_id, _request_from_job(job, prompt))
    return {
        "ok": True,
        "jobId": job_id,
        "state": "submitted",
        "mode": job["mode"],
        "conversationMode": job.get("conversationMode") or job["mode"],
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "cursor": cursor,
        "turn": int(job.get("turn") or 1),
        "sessionId": job["sessionId"],
        "workerPid": worker_pid,
    }


def _managed_permission_candidates(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = []  # type: List[Dict[str, Any]]
    seen_input_ids = set()  # type: set
    values = [job.get("inputRequired")]
    pending_permissions = job.get("pendingPermissions")
    if isinstance(pending_permissions, list):
        values.extend(pending_permissions)
    for value in values:
        if not isinstance(value, dict) or value.get("kind") != "permission":
            continue
        input_id = value.get("inputId")
        if not isinstance(input_id, str) or not input_id or input_id in seen_input_ids:
            continue
        seen_input_ids.add(input_id)
        candidates.append(value)
    return candidates


def _select_managed_permission(job: Dict[str, Any], permission_ref: Any) -> Optional[Dict[str, Any]]:
    candidates = _managed_permission_candidates(job)
    if permission_ref is None:
        if len(candidates) > 1:
            raise BridgeError(
                "permission_selection_required",
                "Multiple permissions are waiting; respond with the permissionRef shown for the selected action.",
            )
        return candidates[0] if candidates else None
    if not isinstance(permission_ref, str) or not permission_ref:
        raise BridgeError("invalid_input", "permissionRef must be a non-empty string.")
    matches = [value for value in candidates if _permission_ref(value) == permission_ref]
    if len(matches) != 1:
        raise BridgeError("input_response_mismatch", "permissionRef does not match a pending permission.")
    return matches[0]


def _respond_job_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(payload.get("jobId") or "")
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        session_id = job.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            raise BridgeError("job_not_ready", "The ROS Agent job has no SessionId.")
        decision = payload.get("decision")
        if not isinstance(decision, str) or decision not in PERMISSION_DECISIONS:
            raise BridgeError("invalid_input", "respond requires allow_once or deny.")
        response_mode = job.get("conversationMode") or job["mode"]
        pending = job.get("inputRequired")
        input_file = payload.get("inputFile")
        if isinstance(input_file, str):
            workspace = pathlib.Path(job["workspace"])
            query, response = load_permission_query(workspace, input_file, decision, session_id, response_mode)
        else:
            pending = _select_managed_permission(job, payload.get("permissionRef"))
            if pending is None:
                last_response = job.get("lastPermissionResponse")
                acknowledgement = job.get("permissionAck")
                if isinstance(last_response, dict) and decision == last_response.get("decision"):
                    if _permission_response_is_acknowledged(last_response, acknowledgement):
                        return {
                            "ok": True,
                            "jobId": job_id,
                            "state": "permission-responded",
                            "mode": job["mode"],
                            "preferredLanguage": job.get("preferredLanguage", "en"),
                            "cursor": len(_read_spool(spool)),
                            "turn": int(job.get("turn") or 1),
                            "sessionId": session_id,
                            "permissionResponse": last_response,
                            "permissionAck": acknowledgement,
                            "duplicate": True,
                        }
                    raise BridgeError("job_busy", "The permission response is already running.", True)
                if isinstance(last_response, dict):
                    raise BridgeError(
                        "input_response_mismatch",
                        "The permission response conflicts with the stored decision.",
                    )
                raise BridgeError("input_response_mismatch", "The ROS Agent job is not waiting for permission.")
            query, response = build_permission_query(pending, decision, session_id, response_mode)
        if not isinstance(pending, dict) or pending.get("kind") != "permission":
            last_response = job.get("lastPermissionResponse")
            acknowledgement = job.get("permissionAck")
            if response == last_response and _permission_response_is_acknowledged(response, acknowledgement):
                return {
                    "ok": True,
                    "jobId": job_id,
                    "state": "permission-responded",
                    "mode": job["mode"],
                    "preferredLanguage": job.get("preferredLanguage", "en"),
                    "cursor": len(_read_spool(spool)),
                    "turn": int(job.get("turn") or 1),
                    "sessionId": session_id,
                    "permissionResponse": response,
                    "permissionAck": acknowledgement,
                    "duplicate": True,
                }
            if isinstance(last_response, dict) and all(
                response.get(key) == last_response.get(key)
                for key in ("requestTaskId", "contextId", "inputId", "toolUseId")
            ):
                raise BridgeError(
                    "input_response_mismatch",
                    "The permission response conflicts with the stored decision.",
                )
            raise BridgeError("input_response_mismatch", "The ROS Agent job is not waiting for permission.")
        for key in ("requestTaskId", "contextId", "inputId", "toolUseId"):
            if response.get(key) != pending.get(key):
                raise BridgeError(
                    "input_response_mismatch", "The permission response does not match the pending input."
                )
        cursor = len(_read_spool(spool))
        primary_worker_alive = isinstance(job.get("workerPid"), int) and _pid_alive(job["workerPid"])
        sub_pipeline = pending.get("permissionClass") == "sub_pipeline"
        sideband = sub_pipeline
        worker_token = None  # type: Optional[str]
        if sideband:
            if job.get("mode") != "pipeline":
                raise BridgeError("input_response_mismatch", "A Sub Pipeline permission requires Pipeline mode.")
            if sub_pipeline and not primary_worker_alive:
                raise BridgeError(
                    "stream_detached",
                    "The parent Pipeline StartChat stream ended before its Sub Pipeline permission was answered.",
                    True,
                )
            if isinstance(job.get("sidebandWorkerToken"), str):
                raise BridgeError("job_busy", "A Pipeline permission response is already running.", True)
            worker_token = uuid.uuid4().hex
            job["sidebandWorkerToken"] = worker_token
            job["sidebandResponseInputId"] = response.get("inputId")
            job["sidebandResponse"] = pending
            job["state"] = "working"
        else:
            if primary_worker_alive:
                raise BridgeError("job_busy", "The current StartChat request is still running.", True)
            job["activeRequestSeq"] = int(job.get("activeRequestSeq") or 0) + 1
            job["state"] = "submitted"
        job["lastPermissionResponse"] = response
        remaining = [
            value
            for value in job.get("pendingPermissions", [])
            if isinstance(value, dict) and value.get("inputId") != response.get("inputId")
        ]
        job.pop("inputRequired", None)
        if remaining:
            job["pendingPermissions"] = remaining
            job["inputRequired"] = remaining[0]
        else:
            job.pop("pendingPermissions", None)
        job.pop("permissionAck", None)
        job.pop("sidebandError", None)
        job.pop("error", None)
        _atomic_json(job_path, job)
    request = _request_from_job(job, query)
    request["permissionResponse"] = response
    if sideband:
        request["workerRole"] = "sideband"
        request["workerToken"] = worker_token
    worker_pid = _spawn_worker(job_id, request)
    return {
        "ok": True,
        "jobId": job_id,
        "state": "submitted",
        "mode": job["mode"],
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "cursor": cursor,
        "turn": int(job.get("turn") or 1),
        "sessionId": session_id,
        "workerPid": worker_pid,
        "permissionResponse": response,
    }


def _run_stop_chat(job: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    if job.get("transport", "aliyun_cli") == "code":
        response = _open_code_request(
            "StopChat",
            {"AgentVersion": "V2", "SessionId": session_id},
            str(job.get("endpoint") or ""),
            job.get("profile") if isinstance(job.get("profile"), str) else None,
            job.get("regionId") if isinstance(job.get("regionId"), str) else None,
            str(job.get("aliyunPath") or "aliyun"),
            max(1, min(int(job.get("connectTimeout") or 10), 30)),
            int(STOP_REQUEST_TIMEOUT_SECONDS),
            credential_source=(
                job.get("credentialSource") if job.get("credentialSource") == "profile" else None
            ),
            error_code="stop_chat_failed",
        )
        try:
            raw = response.read(MAX_DIAGNOSTIC_BYTES + 1)
        finally:
            response.close()
        if len(raw) > MAX_DIAGNOSTIC_BYTES:
            raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat response was too large.", True)
        stdout = raw.decode("utf-8", "replace")
    else:
        command = build_stop_command(job, session_id)
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=STOP_REQUEST_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BridgeError("stop_chat_failed", "Alibaba Cloud CLI could not complete StopChat.", True) from exc
        stdout = (completed.stdout or b"").decode("utf-8", "replace")
        stderr = (completed.stderr or b"").decode("utf-8", "replace")
        if completed.returncode != 0:
            raise BridgeError(
                "stop_chat_failed",
                sanitize_text(stderr, 2000) or "Alibaba Cloud ROS StopChat failed.",
                True,
            )
    try:
        value = json.loads(stdout)
    except ValueError as exc:
        raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat returned invalid JSON.", True) from exc
    if not isinstance(value, dict):
        raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat returned invalid JSON.", True)
    status = value.get("Status", value.get("status"))
    returned_session_id = value.get("SessionId", value.get("sessionId", value.get("session_id")))
    if status not in {"Stopped", "Stopping", "NoActiveStream", "Failed"}:
        raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat returned an unknown status.", True)
    if returned_session_id not in (None, session_id):
        raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat returned a different SessionId.")
    result = {"status": status, "sessionId": session_id}
    request_id = value.get("RequestId", value.get("requestId", value.get("request_id")))
    if isinstance(request_id, str) and request_id:
        result["requestId"] = request_id
    return result


def _cancel_job_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(payload.get("jobId") or "")
    root, job_path, spool = _job_paths(job_id)
    deadline = time.monotonic() + STOP_SESSION_WAIT_SECONDS
    while True:
        job = _load_state_json(job_path)
        session_id = job.get("sessionId")
        if isinstance(session_id, str) and session_id:
            break
        if time.monotonic() >= deadline:
            raise BridgeError("job_not_ready", "The ROS Agent job has not received a SessionId yet.", True)
        time.sleep(0.1)

    stopped = _run_stop_chat(job, session_id)
    stop_status = stopped["status"]
    with StateLock(root / ".job.lock"):
        latest = _load_state_json(job_path)
        latest["stopStatus"] = stop_status
        latest["stopRequestedAt"] = int(time.time())
        if stop_status == "Stopped":
            latest["state"] = "canceled"
            latest.pop("inputRequired", None)
            latest.pop("pendingPermissions", None)
        _atomic_json(job_path, latest)
    state_by_status = {
        "Stopped": "canceled",
        "Stopping": "canceling",
        "NoActiveStream": "not-active",
        "Failed": "cancel-failed",
    }
    result = {
        "ok": stop_status != "Failed",
        "jobId": job_id,
        "state": state_by_status[stop_status],
        "stopStatus": stop_status,
        "mode": latest.get("mode"),
        "preferredLanguage": latest.get("preferredLanguage", "en"),
        "cursor": len(_read_spool(spool)),
        "turn": int(latest.get("turn") or 1),
        "sessionId": session_id,
        "presentationRequired": True,
    }  # type: Dict[str, Any]
    if latest.get("conversationMode") in SUPPORTED_AGENT_MODES:
        result["conversationMode"] = latest["conversationMode"]
    if isinstance(stopped.get("requestId"), str):
        result["requestId"] = stopped["requestId"]
    if stop_status == "Failed":
        result["error"] = {
            "code": "stop_chat_failed",
            "message": "Alibaba Cloud ROS could not stop the active chat.",
            "retryable": True,
        }
    return result


def run_worker(job_id: str, request_token: str) -> int:
    try:
        canonical_job_id = uuid.UUID(job_id).hex
        canonical_request_token = uuid.UUID(request_token).hex
    except (AttributeError, ValueError) as exc:
        raise BridgeError("invalid_input", "The worker launch capability is invalid.") from exc
    if canonical_job_id != job_id or canonical_request_token != request_token:
        raise BridgeError("invalid_input", "The worker launch capability is invalid.")
    root, _job_path, _spool = _job_paths(canonical_job_id)
    request_path = root / ("request-{}.json".format(canonical_request_token))
    request = _load_state_json(request_path, "invalid_input")
    with contextlib.suppress(OSError):
        request_path.unlink()
    request_seq = int(request.get("requestSeq") or 0)
    worker_pid = os.getpid()
    worker_role = request.get("workerRole")
    worker_token = request.get("workerToken")

    def fail_worker(error: BridgeError) -> None:
        if worker_role == "sideband" and isinstance(worker_token, str):
            _fail_sideband_job(job_id, request_seq, worker_token, error, worker_pid)
        else:
            _fail_job(job_id, request_seq, error, worker_pid)

    args = argparse.Namespace(
        aliyun_path=request.get("aliyunPath", "aliyun"),
        transport=request.get("transport", "aliyun_cli"),
        aliyun_cli_execution_mode=request.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE),
        endpoint=request.get("endpoint"),
        connect_timeout=int(request.get("connectTimeout") or 10),
        read_timeout=int(request.get("readTimeout") or DEFAULT_READ_TIMEOUT_SECONDS),
        profile=request.get("profile"),
        credential_source=request.get("credentialSource"),
        region_id=request.get("regionId"),
        no_thinking=request.get("noThinking") is True,
        mode=request.get("mode"),
        session_id=request.get("sessionId"),
    )
    prompt = request.get("prompt")
    if not isinstance(prompt, str):
        fail_worker(BridgeError("invalid_input", "The worker prompt is invalid."))
        return 1
    workspace = _trusted_manager_workspace(str(request.get("workspace") or ""))
    client_context = request.get("clientContext") if isinstance(request.get("clientContext"), str) else None
    attachments = request.get("attachments") if isinstance(request.get("attachments"), list) else []
    summary_mode = request.get("summaryMode") if request.get("summaryMode") in SUPPORTED_AGENT_MODES else args.mode

    def project(payload: Dict[str, Any], summary: StreamSummary) -> None:
        _append_projection(
            job_id,
            _project_managed_stream_event(
                payload,
                summary,
                summary_mode,
                request_seq,
                str(worker_role or "primary"),
                worker_token,
            ),
        )

    try:
        result = _consume_start_chat(
            args,
            workspace,
            prompt,
            client_context,
            attachments,
            summary_mode=summary_mode,
            on_payload=project,
        )
    except BaseException as exc:
        error = exc if isinstance(exc, BridgeError) else BridgeError("stream_failed", str(exc), True)
        fail_worker(error)
        return 1
    permission_response = request.get("permissionResponse")
    if isinstance(permission_response, dict):
        result["permissionResponse"] = permission_response
    if worker_role == "sideband" and isinstance(worker_token, str):
        _finish_sideband_job(job_id, request_seq, worker_token, result, worker_pid)
    else:
        _finish_job(job_id, request_seq, result, worker_pid)
    return 0 if result.get("ok") is True else 1


def _manager_record_path() -> pathlib.Path:
    return _state_root() / "manager" / "manager.json"


def _manager_activity_path() -> pathlib.Path:
    return _state_root() / "manager" / "activity"


def _touch_manager_activity() -> None:
    path = _manager_activity_path()
    with contextlib.suppress(OSError):
        _secure_directory(path.parent)
        path.touch()


def _manager_request(
    record: Dict[str, Any],
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    url = "http://127.0.0.1:{}{}".format(record.get("port"), path)
    data = _json_bytes(payload) if payload is not None else None
    headers = {"Accept": "application/json", "Authorization": "Bearer " + str(record.get("token") or "")}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_MANAGER_REQUEST_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_MANAGER_REQUEST_BYTES + 1)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError):
            value = {}
        error = value.get("error") if isinstance(value, dict) else None
        if isinstance(error, dict):
            raise BridgeError(
                str(error.get("code") or "manager_failed"),
                sanitize_text(str(error.get("message") or "The local ROS Agent manager rejected the request."), 3000),
                error.get("retryable") is True,
            ) from exc
        raise BridgeError("manager_failed", "The local ROS Agent manager rejected the request.", True) from exc
    except (OSError, urllib.error.URLError) as exc:
        raise BridgeError("manager_unavailable", "The local ROS Agent manager did not respond.", True) from exc
    if len(raw) > MAX_MANAGER_REQUEST_BYTES:
        raise BridgeError("manager_failed", "The local ROS Agent manager response exceeded its limit.")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BridgeError("manager_failed", "The local ROS Agent manager returned invalid JSON.") from exc
    if not isinstance(value, dict):
        raise BridgeError("manager_failed", "The local ROS Agent manager returned invalid JSON.")
    return value


def _manager_matches(record: Dict[str, Any]) -> bool:
    if (
        record.get("schemaVersion") != MANAGER_SCHEMA_VERSION
        or record.get("scriptPath") != str(pathlib.Path(__file__).resolve())
        or not _pid_alive(record.get("pid"))
        or not isinstance(record.get("token"), str)
        or not isinstance(record.get("generation"), str)
        or not isinstance(record.get("port"), int)
    ):
        return False
    try:
        health = _manager_request(record, "/health", timeout=2)
    except BridgeError:
        return False
    return (
        health.get("ok") is True
        and health.get("generation") == record.get("generation")
        and health.get("schemaVersion") == MANAGER_SCHEMA_VERSION
    )


def _stop_spawned_process(process: Any) -> None:
    if process.poll() is not None:
        return
    with contextlib.suppress(OSError):
        process.terminate()
    try:
        process.wait(timeout=5)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    with contextlib.suppress(OSError):
        process.kill()


def _normalized_manager_idle_seconds(value: Optional[float]) -> float:
    idle_seconds = MANAGER_IDLE_SECONDS if value is None else value
    if (
        isinstance(idle_seconds, bool)
        or not isinstance(idle_seconds, (int, float))
        or idle_seconds != idle_seconds
        or idle_seconds <= 0
        or idle_seconds > MAX_MANAGER_IDLE_SECONDS
    ):
        raise BridgeError("invalid_config", "The manager idle timeout is invalid.")
    return float(idle_seconds)


def ensure_manager(idle_seconds: Optional[float] = None) -> Dict[str, Any]:
    desired_idle_seconds = _normalized_manager_idle_seconds(idle_seconds)
    record_path = _manager_record_path()
    root = record_path.parent
    _secure_directory(root)
    with StateLock(root / ".manager.lock"):
        if record_path.is_file():
            with contextlib.suppress(BridgeError):
                current = _load_state_json(record_path, "manager_unavailable")
                if _manager_matches(current):
                    if current.get("idleSeconds") != desired_idle_seconds:
                        current["idleSeconds"] = desired_idle_seconds
                        _atomic_json(record_path, current)
                    return current
        record = {
            "schemaVersion": MANAGER_SCHEMA_VERSION,
            "scriptPath": str(pathlib.Path(__file__).resolve()),
            "generation": uuid.uuid4().hex,
            "port": _free_port(),
            "token": secrets.token_urlsafe(32),
            "pid": 0,
            "startedAt": int(time.time()),
            "idleSeconds": desired_idle_seconds,
        }  # type: Dict[str, Any]
        _atomic_json(record_path, record)
        command = [
            sys.executable,
            str(pathlib.Path(__file__).resolve()),
            "_server",
            "--record-file",
            str(record_path),
        ]
        log_path = root / "manager.log"
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        process = None
        ready = False
        try:
            with log_path.open("ab", buffering=0) as log:
                process = subprocess.Popen(
                    command,
                    cwd=str(root),
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=os.name != "nt",
                    creationflags=creationflags,
                )
            record["pid"] = process.pid
            record["logPath"] = str(log_path)
            _atomic_json(record_path, record)
            deadline = time.monotonic() + MANAGER_START_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                if _manager_matches(record):
                    ready = True
                    return record
                time.sleep(0.1)
            raise BridgeError("manager_start_failed", "The local ROS Agent manager failed its health check.", True)
        finally:
            if process is not None and not ready:
                _stop_spawned_process(process)
                with contextlib.suppress(OSError):
                    record_path.unlink()


def _active_worker_exists() -> bool:
    jobs_root = _state_root() / "jobs"
    if not jobs_root.is_dir():
        return False
    for path in jobs_root.glob("*/job.json"):
        with contextlib.suppress(BridgeError):
            job = _load_state_json(path)
            if _pid_alive(job.get("workerPid")) or _pid_alive(job.get("sidebandWorkerPid")):
                return True
    return False


class _ManagerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: Tuple[str, int], record: Dict[str, Any]) -> None:
        super().__init__(address, _ManagerHandler)
        self.record = record
        self.last_activity = time.monotonic()
        self.activity_mtime_ns = 0
        self.startup_deadline = self.last_activity + MANAGER_START_TIMEOUT_SECONDS
        self.startup_health_checked = False


class _ManagerHandler(BaseHTTPRequestHandler):
    server: _ManagerServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *args: Any) -> None:
        return

    def _authorized(self) -> bool:
        expected = "Bearer " + str(self.server.record.get("token") or "")
        supplied = self.headers.get("Authorization", "")
        return bool(expected) and secrets.compare_digest(supplied, expected)

    def _write(self, status: int, value: Dict[str, Any]) -> None:
        data = _json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.wfile.flush()
        self.server.last_activity = time.monotonic()
        self.close_connection = True

    def do_GET(self) -> None:
        if not self._authorized():
            self._write(401, {"ok": False, "error": {"code": "unauthorized", "message": "Unauthorized."}})
            return
        self.server.last_activity = time.monotonic()
        if self.path != "/health":
            self._write(404, {"ok": False, "error": {"code": "not_found", "message": "Not found."}})
            return
        self._write(
            200,
            {
                "ok": True,
                "schemaVersion": MANAGER_SCHEMA_VERSION,
                "generation": self.server.record.get("generation"),
                "pid": os.getpid(),
            },
        )
        self.server.startup_health_checked = True

    def do_POST(self) -> None:
        if not self._authorized():
            self._write(401, {"ok": False, "error": {"code": "unauthorized", "message": "Unauthorized."}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_MANAGER_REQUEST_BYTES:
                raise BridgeError("invalid_input", "The manager request size is invalid.")
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(value, dict):
                raise BridgeError("invalid_input", "The manager request must be a JSON object.")
            self.server.last_activity = time.monotonic()
            if self.path == "/start":
                result = _start_job_local(value)
            elif self.path == "/continue":
                result = _continue_job_local(value)
            elif self.path == "/respond":
                result = _respond_job_local(value)
            elif self.path == "/cancel":
                result = _cancel_job_local(value)
            elif self.path == "/follow":
                result = _follow_job_local(
                    str(value.get("jobId") or ""),
                    int(value.get("cursor") or 0),
                    float(value.get("waitSeconds") or 0),
                )
            else:
                self._write(404, {"ok": False, "error": {"code": "not_found", "message": "Not found."}})
                return
        except BridgeError as exc:
            self._write(
                400,
                {
                    "ok": False,
                    "state": "failed",
                    "error": {
                        "code": exc.code,
                        "message": sanitize_text(exc.message, 3000),
                        "retryable": exc.retryable,
                    },
                },
            )
            return
        except (TypeError, ValueError, UnicodeError) as exc:
            self._write(
                400,
                {
                    "ok": False,
                    "state": "failed",
                    "error": {"code": "invalid_input", "message": sanitize_text(str(exc), 1000)},
                },
            )
            return
        self._write(200, result)


def run_manager_server(record_file: str) -> int:
    record_path = pathlib.Path(record_file).resolve()
    record = _load_state_json(record_path, "manager_start_failed")
    if record.get("scriptPath") != str(pathlib.Path(__file__).resolve()):
        raise BridgeError("manager_start_failed", "The manager script identity does not match.")
    server = _ManagerServer(("127.0.0.1", int(record["port"])), record)
    activity_path = _manager_activity_path()
    _touch_manager_activity()
    with contextlib.suppress(OSError):
        server.activity_mtime_ns = activity_path.stat().st_mtime_ns
    server.timeout = 0.5
    try:
        while True:
            server.handle_request()
            with contextlib.suppress(OSError):
                activity_mtime_ns = activity_path.stat().st_mtime_ns
                if activity_mtime_ns > server.activity_mtime_ns:
                    server.activity_mtime_ns = activity_mtime_ns
                    server.last_activity = time.monotonic()
            if not server.startup_health_checked:
                if time.monotonic() >= server.startup_deadline:
                    break
                continue
            if _active_worker_exists():
                server.last_activity = time.monotonic()
                continue
            idle_seconds = float(record.get("idleSeconds") or MANAGER_IDLE_SECONDS)
            with contextlib.suppress(BridgeError):
                latest_record = _load_state_json(record_path, "manager_unavailable")
                if latest_record.get("generation") == record.get("generation"):
                    idle_seconds = _normalized_manager_idle_seconds(latest_record.get("idleSeconds"))
            if time.monotonic() - server.last_activity >= idle_seconds:
                break
    finally:
        server.server_close()
    return 0


def _run_check_command(command: List[str], required: bool = False) -> Optional[subprocess.CompletedProcess]:
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if required:
            raise BridgeError("cli_check_failed", "Alibaba Cloud CLI could not be checked.", True) from exc
        return None
    if result.returncode != 0:
        if required:
            error = (result.stderr or b"").decode("utf-8", "replace")
            raise BridgeError("cli_check_failed", sanitize_text(error, 1000) or "Alibaba Cloud CLI check failed.", True)
        return None
    return result


def _parse_profile_fields(output: bytes) -> Dict[str, str]:
    values = {}  # type: Dict[str, str]
    for raw_line in output.decode("utf-8", "replace").splitlines():
        key, separator, raw_value = raw_line.partition("=")
        if not separator or key not in {"profile", "mode", "language"}:
            continue
        value = sanitize_text(raw_value, 200)
        if value:
            values[key] = value
    return values


def run_check(args: argparse.Namespace) -> Dict[str, Any]:
    sdk = None  # type: Optional[Dict[str, Any]]
    cli_execution_mode = getattr(args, "aliyun_cli_execution_mode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE)
    if args.transport == "code":
        sdk = _load_code_sdk()

    plugin_status = None  # type: Optional[Dict[str, Any]]
    plugin_auto_install = None  # type: Optional[bool]
    if args.transport == "aliyun_cli" and cli_execution_mode == "remote":
        resolve_aliyun(args.aliyun_path)
        current_profile = {"configured": True, "mode": "RemoteSandbox"}
        cli = "aliyun"
        version = None
    elif args.transport == "code" and not args.profile_pinned:
        assert sdk is not None
        region_id = _environment_region() or "cn-hangzhou"
        try:
            _code_credentials(sdk, args.aliyun_path, None, region_id, None)
        except BridgeError:
            raise
        except Exception as exc:
            raise BridgeError(
                "credential_failed",
                "Alibaba Cloud SDK default credential chain could not resolve credentials.",
                True,
            ) from exc
        current_profile = {
            "configured": True,
            "mode": "DefaultCredentialChain",
            "regionId": region_id,
        }  # type: Dict[str, Any]
        cli = None
        version = None
    else:
        selected = _selected_cli_profile_record(args.profile)
        region_id = _environment_region() or selected.get("regionId") or "cn-hangzhou"
        current_profile = {"configured": True, "name": selected["name"], "mode": selected["mode"]}
        if selected.get("language"):
            current_profile["language"] = selected["language"]
        current_profile["regionId"] = region_id
        if args.transport == "code":
            assert sdk is not None
            try:
                _code_credentials(sdk, args.aliyun_path, selected["name"], region_id, "profile")
            except BridgeError:
                raise
            except Exception as exc:
                raise BridgeError(
                    "credential_failed",
                    "Alibaba Cloud SDK could not load or refresh the selected CLI Profile.",
                    True,
                ) from exc
            cli = None
            version = None
        else:
            aliyun = resolve_aliyun(args.aliyun_path)
            version_result = _run_check_command([aliyun, "version"], required=True)
            assert version_result is not None
            cli = "aliyun"
            version = sanitize_text((version_result.stdout or b"").decode("utf-8", "replace"), 200)
            plugin_status = _local_ros_plugin_status()
            plugin_auto_install = bool(selected.get("autoPluginInstall"))

    result = {
        "ok": True,
        "cli": cli,
        "version": version,
        "transport": args.transport,
        "aliyunCLIExecutionMode": cli_execution_mode,
        "endpoint": args.endpoint,
        "allowedAgentModes": args.allowed_agent_modes,
        "managerIdleSeconds": args.manager_idle_seconds,
        "enableThinking": args.enable_thinking,
        "aliyunCLIProfile": args.aliyun_cli_profile,
        "currentProfile": current_profile,
    }  # type: Dict[str, Any]
    if plugin_status is not None:
        result["rosPluginReady"] = plugin_status["ready"]
        result["pluginAutoInstallEnabled"] = plugin_auto_install
        result["pluginInstallRequired"] = bool(plugin_status["installed"] and not plugin_status["ready"]) or bool(
            not plugin_status["installed"] and not plugin_auto_install
        )
        if plugin_status.get("version"):
            result["rosPluginVersion"] = plugin_status["version"]
    return result


def _follow_after_command(args: argparse.Namespace, result: Dict[str, Any]) -> Dict[str, Any]:
    if not getattr(args, "follow", False):
        return result
    followed = run_follow_job(
        argparse.Namespace(
            job_id=result["jobId"],
            cursor=result["cursor"],
            wait_seconds=getattr(args, "follow_seconds", DEFAULT_FOLLOW_SECONDS),
            manager_idle_seconds=getattr(args, "manager_idle_seconds", MANAGER_IDLE_SECONDS),
        )
    )
    followed["workerPid"] = result.get("workerPid")
    return _bound_follow_result(followed)


def run_start_job(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = _workspace()
    prompt = read_prompt(workspace, args.prompt_file)
    client_context = load_client_context(workspace, args.client_context_file)
    attachments = load_attachments(workspace, args.attachments_file)
    _resolve_start_identity(args)
    record = ensure_manager(args.manager_idle_seconds)
    result = _manager_request(
        record,
        "/start",
        {
            "workspace": str(workspace),
            "prompt": prompt,
            "mode": args.mode,
            "transport": args.transport,
            "aliyunCLIExecutionMode": args.aliyun_cli_execution_mode,
            "endpoint": args.endpoint,
            "regionId": args.region_id,
            "profile": args.profile,
            "credentialSource": args.credential_source,
            "noThinking": args.no_thinking,
            "connectTimeout": args.connect_timeout,
            "readTimeout": args.read_timeout,
            "aliyunPath": args.aliyun_path,
            "clientContext": client_context,
            "attachments": attachments,
        },
        timeout=15,
    )
    return _follow_after_command(args, result)


def run_follow_job(args: argparse.Namespace) -> Dict[str, Any]:
    wait_seconds = max(0.0, min(float(args.wait_seconds), MAX_FOLLOW_SECONDS))
    record = ensure_manager(args.manager_idle_seconds)
    return _manager_request(
        record,
        "/follow",
        {"jobId": args.job_id, "cursor": int(args.cursor), "waitSeconds": wait_seconds},
        timeout=wait_seconds + 15,
    )


def run_continue_job(args: argparse.Namespace) -> Dict[str, Any]:
    record = ensure_manager(args.manager_idle_seconds)
    result = _manager_request(
        record,
        "/continue",
        {"jobId": args.job_id, "promptFile": str(pathlib.Path(args.prompt_file).expanduser().resolve())},
        timeout=15,
    )
    return _follow_after_command(args, result)


def run_respond_job(args: argparse.Namespace) -> Dict[str, Any]:
    record = ensure_manager(args.manager_idle_seconds)
    result = _manager_request(
        record,
        "/respond",
        {
            "jobId": args.job_id,
            "inputFile": (
                str(pathlib.Path(args.input_file).expanduser().resolve()) if args.input_file is not None else None
            ),
            "permissionRef": args.permission_ref,
            "decision": args.decision,
        },
        timeout=15,
    )
    return _follow_after_command(args, result)


def run_cancel_job(args: argparse.Namespace) -> Dict[str, Any]:
    record = ensure_manager(args.manager_idle_seconds)
    return _manager_request(
        record,
        "/cancel",
        {"jobId": args.job_id},
        timeout=STOP_REQUEST_TIMEOUT_SECONDS + 15,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use Alibaba Cloud ROS Agent through Alibaba Cloud CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Check Alibaba Cloud CLI without calling StartChat.")
    check.add_argument("--aliyun-path", default="aliyun")

    start = subparsers.add_parser("start", help="Start a managed StartChat job.")
    start.add_argument("--prompt-file", required=True)
    start.add_argument("--mode", choices=("normal", "pipeline"), default="normal")
    start.add_argument("--region-id")
    start.add_argument("--endpoint")
    start.add_argument("--profile")
    start.add_argument("--client-context-file")
    start.add_argument("--attachments-file")
    start.add_argument("--no-thinking", action="store_true")
    start.add_argument("--connect-timeout", type=int, default=10)
    start.add_argument("--read-timeout", type=int, default=DEFAULT_READ_TIMEOUT_SECONDS)
    start.add_argument("--aliyun-path", default="aliyun")
    start.add_argument("--follow", action="store_true")
    start.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)

    follow = subparsers.add_parser("follow", help="Wait for the next managed StartChat boundary.")
    follow.add_argument("--job-id", required=True)
    follow.add_argument("--cursor", type=int, default=0)
    follow.add_argument("--wait-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)

    continued = subparsers.add_parser("continue", help="Send a natural-language continuation for a managed job.")
    continued.add_argument("--job-id", required=True)
    continued.add_argument("--prompt-file", required=True)
    continued.add_argument("--follow", action="store_true")
    continued.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)

    respond = subparsers.add_parser("respond", help="Approve or deny a managed StartChat permission.")
    respond.add_argument("--job-id", required=True)
    respond.add_argument("--permission-ref")
    respond.add_argument("--input-file", help=argparse.SUPPRESS)
    respond.add_argument("--decision", choices=("allow_once", "deny"), required=True)
    respond.add_argument("--follow", action="store_true")
    respond.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)

    cancel = subparsers.add_parser("cancel", help="Stop the remote chat for a managed job.")
    cancel.add_argument("--job-id", required=True)

    server = subparsers.add_parser("_server", help=argparse.SUPPRESS)
    server.add_argument("--record-file", required=True)
    worker = subparsers.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("--job-id", required=True)
    worker.add_argument("--request-token", required=True)
    return parser


def _print_json(value: Dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "_server":
            return run_manager_server(args.record_file)
        if args.command == "_worker":
            return run_worker(args.job_id, args.request_token)
        apply_skill_config(args, load_skill_config())
        if args.command == "check":
            result = run_check(args)
        elif args.command == "start":
            if args.connect_timeout <= 0 or args.read_timeout <= 0:
                raise BridgeError("invalid_input", "Timeout values must be positive integers.")
            result = run_start_job(args)
        elif args.command == "follow":
            result = run_follow_job(args)
        elif args.command == "continue":
            result = run_continue_job(args)
        elif args.command == "cancel":
            result = run_cancel_job(args)
        else:
            result = run_respond_job(args)
    except BridgeError as exc:
        failure = {
            "ok": False,
            "state": "failed",
            "error": {
                "code": exc.code,
                "message": sanitize_text(exc.message, 3000),
                "retryable": exc.retryable,
            },
        }
        if args.command != "check":
            failure["presentationRequired"] = True
        _print_json(failure)
        return 1
    _print_json(result)
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    sys.exit(main())
