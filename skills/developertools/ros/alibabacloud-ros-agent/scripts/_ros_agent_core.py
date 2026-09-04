# Core state, policy, transport, and stream parsing source shard.
# Loaded by ros_agent.py into its shared module namespace; do not execute directly.
# ruff: noqa: F821 -- names are provided by the shared ros_agent.py namespace.

class BridgeError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def _session_backup_not_ready_error(value: Any) -> Optional[BridgeError]:
    if not isinstance(value, dict):
        return None
    raw_error = value.get("error") if isinstance(value.get("error"), dict) else value
    data = raw_error.get("data") if isinstance(raw_error.get("data"), dict) else {}
    code = data.get("code") or raw_error.get("code") or raw_error.get("Code")
    if code != SESSION_BACKUP_NOT_READY_CODE:
        return None
    message = raw_error.get("message") or raw_error.get("Message")
    if not isinstance(message, str) or not message:
        message = "Session backup is still synchronizing. Retry after 3 seconds."
    return BridgeError(SESSION_BACKUP_NOT_READY_CODE, sanitize_text(message, 2000), True)


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
        "aliyunCLIForwardEnv",
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

    if "aliyunCLIForwardEnv" in value:
        result["aliyunCLIForwardEnv"] = _validate_remote_cli_forward_env_names(
            value["aliyunCLIForwardEnv"],
            "invalid_config",
        )

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
    if "aliyunCLIForwardEnv" in result and not (transport == "aliyun_cli" and execution_mode == "remote"):
        raise BridgeError(
            "invalid_config",
            "aliyunCLIForwardEnv may be configured only for remote aliyun CLI execution.",
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
    forwarded_environment = config.get("aliyunCLIForwardEnv", list(DEFAULT_REMOTE_CLI_FORWARD_ENV))
    args.manager_idle_seconds = config.get("managerIdleSeconds", MANAGER_IDLE_SECONDS)
    args.enable_thinking = enable_thinking
    args.aliyun_cli_profile = configured_profile
    args.aliyun_cli_execution_mode = cli_execution_mode
    args.aliyun_cli_forward_env = (
        list(forwarded_environment) if transport == "aliyun_cli" and cli_execution_mode == "remote" else []
    )
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


def _validate_remote_cli_forward_env_names(value: Any, error_code: str = "invalid_input") -> List[str]:
    if not isinstance(value, (list, tuple)) or len(value) > MAX_REMOTE_CLI_FORWARD_ENV_NAMES:
        raise BridgeError(
            error_code,
            "aliyunCLIForwardEnv must be an array of at most {} environment variable names.".format(
                MAX_REMOTE_CLI_FORWARD_ENV_NAMES
            ),
        )
    result = []  # type: List[str]
    for item in value:
        if not isinstance(item, str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", item) is None:
            raise BridgeError(error_code, "aliyunCLIForwardEnv contains an invalid environment variable name.")
        normalized = re.sub(r"[^a-z0-9]", "", item.lower())
        if any(part in normalized for part in SENSITIVE_ENV_NAME_PARTS):
            raise BridgeError(error_code, "aliyunCLIForwardEnv must not include credential or secret variables.")
        if item in result:
            raise BridgeError(error_code, "aliyunCLIForwardEnv must not contain duplicates.")
        result.append(item)
    return result


def _capture_remote_cli_environment(names: Iterable[str]) -> Dict[str, str]:
    result = {}  # type: Dict[str, str]
    total = 0
    for name in _validate_remote_cli_forward_env_names(list(names)):
        value = os.environ.get(name)
        if value is None:
            continue
        size = len(value.encode("utf-8"))
        if "\0" in value or size > MAX_REMOTE_CLI_ENV_VALUE_BYTES:
            raise BridgeError("invalid_input", "A forwarded remote CLI environment value is invalid or too large.")
        total += size
        if total > MAX_REMOTE_CLI_ENV_BYTES:
            raise BridgeError("invalid_input", "The forwarded remote CLI environment is too large.")
        result[name] = value
    return result


def _remote_cli_environment_from_payload(job: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, str]:
    legacy_default = (
        list(DEFAULT_REMOTE_CLI_FORWARD_ENV)
        if job.get("transport", "aliyun_cli") == "aliyun_cli"
        and job.get("aliyunCLIExecutionMode") == "remote"
        else []
    )
    allowed = _validate_remote_cli_forward_env_names(job.get("aliyunCLIForwardEnv", legacy_default))
    value = payload.get("transientEnvironment", {})
    if not isinstance(value, dict):
        raise BridgeError("invalid_input", "The transient remote CLI environment is invalid.")
    if set(value) - set(allowed):
        raise BridgeError("invalid_input", "The transient remote CLI environment contains an unapproved name.")
    result = {}  # type: Dict[str, str]
    total = 0
    for name, item in value.items():
        if not isinstance(item, str) or "\0" in item:
            raise BridgeError("invalid_input", "A transient remote CLI environment value is invalid.")
        size = len(item.encode("utf-8"))
        if size > MAX_REMOTE_CLI_ENV_VALUE_BYTES:
            raise BridgeError("invalid_input", "A transient remote CLI environment value is too large.")
        total += size
        if total > MAX_REMOTE_CLI_ENV_BYTES:
            raise BridgeError("invalid_input", "The transient remote CLI environment is too large.")
        result[name] = item
    return result


def _remote_cli_subprocess_environment(names: Iterable[str], values: Dict[str, str]) -> Dict[str, str]:
    environment = dict(os.environ)
    for name in _validate_remote_cli_forward_env_names(list(names)):
        environment.pop(name, None)
    environment.update(values)
    return environment


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
                    backup_not_ready = _session_backup_not_ready_error(value)
                    if backup_not_ready is not None:
                        raise backup_not_ready
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
    decoder = json.JSONDecoder()
    buffer = ""

    def projected(value: Any, raw: str) -> Iterator[Tuple[Optional[Dict[str, Any]], str]]:
        if isinstance(value, list):
            for item in value:
                item_raw = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                yield (_cli_plugin_payload(item) if isinstance(item, dict) else None), item_raw
            return
        yield (_cli_plugin_payload(value) if isinstance(value, dict) else None), raw

    for raw_line in lines:
        if len(raw_line.encode("utf-8")) > MAX_SSE_LINE_BYTES:
            raise BridgeError("stream_failed", "A StartChat CLI output line exceeded the bridge limit.")
        buffer += raw_line
        if len(buffer.encode("utf-8")) > MAX_SSE_EVENT_BYTES:
            raise BridgeError("stream_failed", "Buffered StartChat CLI output exceeded the bridge limit.")
        while buffer.strip():
            leading = len(buffer) - len(buffer.lstrip())
            try:
                value, end = decoder.raw_decode(buffer, leading)
            except ValueError:
                first_line, separator, remainder = buffer.partition("\n")
                if not separator or not first_line.strip() or not remainder.strip():
                    break
                remainder_start = len(remainder) - len(remainder.lstrip())
                try:
                    _remainder_value, remainder_end = decoder.raw_decode(remainder, remainder_start)
                except ValueError:
                    break
                if remainder[remainder_end:].strip():
                    break
                yield None, first_line.strip()
                buffer = remainder
                continue
            raw = buffer[leading:end]
            yield from projected(value, raw)
            buffer = buffer[end:]
    if buffer.strip():
        yield None, buffer.strip()
