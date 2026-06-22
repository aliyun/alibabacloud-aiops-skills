#!/usr/bin/env python3
"""Call the Alibaba Cloud STAROps Agent OpenAPI from an official-style Skill."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional
from urllib.parse import quote, quote_plus, urlencode

import requests

try:
    from alibabacloud_credentials.client import Client as CredentialClient
except Exception:  # pragma: no cover - exercised only when dependency is missing.
    CredentialClient = None


API_VERSION = "2026-04-28"
ALGORITHM = "ACS3-HMAC-SHA256"
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
DEFAULT_ENDPOINT = "starops.cn-beijing.aliyuncs.com"
CONFIG_DIR = ".starops"
CONFIG_FILE_NAME = "config.json"
CONFIG_PATH_ENV = "STAROPS_AGENT_CONFIG"
DEFAULT_TIMEOUT_SECONDS = 1800
DEFAULT_IDLE_TIMEOUT_SECONDS = 60
STAROPS_CONSOLE_CHAT_URL = "https://starops.console.aliyun.com/chat"
TEXT_TOOL_NAMES = {"generate_diagnosis_report"}
SESSION_ID_ENV = "SKILL_SESSION_ID"
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/alibabacloud-starops-chat/{session_id}"


class OutputMode(str, Enum):
    CLI = "cli"
    JSON = "json"
    PIPE = "pipe"


class ConfigError(RuntimeError):
    """The STAROps Skill configuration is missing or invalid."""


class CredentialError(RuntimeError):
    """Alibaba Cloud credentials could not be loaded from the default chain."""


class StarOpsHTTPError(RuntimeError):
    """STAROps OpenAPI returned a non-success status code."""


class StarOpsTimeoutError(RuntimeError):
    """STAROps Agent streaming timed out."""


@dataclass(frozen=True)
class StarOpsConfig:
    employee: str
    workspace: str
    uid: str
    endpoint: str
    timeout_seconds: float
    idle_timeout_seconds: float
    assistant_id: str
    project: Optional[str] = None


@dataclass
class AskResult:
    thread_id: str
    trace_id: Optional[str]
    status: Optional[str]
    messages: list[str]


@dataclass(frozen=True)
class ToolRecord:
    name: str
    tool_id: str
    tool_call_id: str
    status: str
    contents: list[str]


class SignatureRequest:
    def __init__(
        self,
        method: str,
        path: str,
        query: Optional[Mapping[str, Any]],
        host: str,
        action: str,
        version: str,
        user_agent: str,
        body: bytes = b"",
    ):
        self.method = method.upper()
        self.path = path
        self.query = OrderedDict((query or {}).items())
        self.host = host
        self.action = action
        self.version = version
        self.body = body or b""
        self.headers = OrderedDict(
            [
                ("host", host),
                ("content-type", JSON_CONTENT_TYPE),
                ("x-acs-action", action),
                ("x-acs-version", version),
                ("x-acs-date", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
                ("x-acs-signature-nonce", str(uuid.uuid4())),
                ("x-acs-content-sha256", sha256_hex(self.body)),
                ("user-agent", user_agent),
            ]
        )


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def percent_encode(value: str) -> str:
    return value.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")


def flatten_params(result: dict[str, str], prefix: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value, start=1):
            flatten_params(result, f"{prefix}.{index}", item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            flatten_params(result, f"{prefix}.{key}", item)
        return
    key = prefix.lstrip(".")
    result[key] = value.decode("utf-8") if isinstance(value, bytes) else str(value)


def canonicalize_query(query: Mapping[str, Any]) -> str:
    flattened: dict[str, str] = {}
    flatten_params(flattened, "", dict(query))
    return "&".join(
        f"{percent_encode(quote_plus(key))}={percent_encode(quote_plus(str(flattened[key])))}"
        for key in sorted(flattened)
    )


def normalize_header_value(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def build_canonical_request(request: SignatureRequest) -> tuple[str, str]:
    signed_header_map: OrderedDict[str, str] = OrderedDict()
    for key in sorted(request.headers, key=lambda item: item.lower()):
        lower_key = key.lower()
        if lower_key == "authorization":
            continue
        if lower_key.startswith("x-acs-") or lower_key in {"host", "content-type"}:
            signed_header_map[lower_key] = normalize_header_value(request.headers[key])

    canonical_headers = "\n".join(f"{key}:{value}" for key, value in signed_header_map.items()) + "\n"
    signed_headers = ";".join(signed_header_map.keys())
    hashed_payload = sha256_hex(request.body)
    canonical_request = "\n".join(
        [
            request.method,
            request.path,
            canonicalize_query(request.query),
            canonical_headers,
            signed_headers,
            hashed_payload,
        ]
    )
    return canonical_request, signed_headers


def response_body(payload: Any) -> Any:
    if isinstance(payload, dict) and isinstance(payload.get("body"), dict):
        return payload["body"]
    return payload


def quoted_path_part(value: str) -> str:
    return quote(str(value), safe="")


def build_starops_console_url(thread_id: str, assistant_id: str) -> str:
    return f"{STAROPS_CONSOLE_CHAT_URL}?{urlencode({'threadId': thread_id, 'assistantId': assistant_id})}"


def resolve_session_id() -> str:
    session_id = os.environ.get(SESSION_ID_ENV, "").strip()
    if session_id:
        if not re.fullmatch(r"[0-9a-fA-F]{32}", session_id):
            raise ConfigError(f"{SESSION_ID_ENV} must be a 32-character hexadecimal string.")
        return session_id.lower()

    session_id = uuid.uuid4().hex
    os.environ[SESSION_ID_ENV] = session_id
    return session_id


def build_user_agent(session_id: str) -> str:
    return USER_AGENT_TEMPLATE.format(session_id=session_id)


def user_config_path() -> Path:
    return Path.home() / CONFIG_DIR / CONFIG_FILE_NAME


def project_config_path() -> Path:
    return Path(CONFIG_DIR) / CONFIG_FILE_NAME


def read_json_config_file(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ConfigError(f"STAROps config file does not exist: {config_path}")
    if not config_path.is_file():
        raise ConfigError(f"STAROps config path is not a file: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"STAROps config file is not valid JSON: {config_path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Failed to read STAROps config file {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"STAROps config file must contain a JSON object: {config_path}")
    return payload


def config_value_is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def config_path_key(config_path: Path) -> str:
    try:
        return str(config_path.resolve())
    except OSError:
        return str(config_path)


def config_file_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()

    def add_existing(config_path: Path) -> None:
        if not config_path.exists():
            return
        key = config_path_key(config_path)
        if key in seen:
            return
        seen.add(key)
        paths.append(config_path)

    add_existing(user_config_path())
    add_existing(project_config_path())

    explicit_path = getattr(args, "config", None) or os.environ.get(CONFIG_PATH_ENV)
    if explicit_path:
        config_path = Path(explicit_path).expanduser()
        key = config_path_key(config_path)
        if key not in seen:
            seen.add(key)
            paths.append(config_path)
    return paths


def read_file_config(args: argparse.Namespace) -> dict[str, Any]:
    merged_config: dict[str, Any] = {}
    for config_path in config_file_paths(args):
        merged_config.update(read_json_config_file(config_path))
    return merged_config


def config_text_value(config: Mapping[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = config.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def resolve_text_value(
    env_name: str,
    config: Mapping[str, Any],
    *config_keys: str,
    default: Optional[str] = None,
) -> Optional[str]:
    env_value = os.environ.get(env_name)
    if env_value is not None:
        env_text = env_value.strip()
        if env_text:
            return env_text
    return config_text_value(config, *config_keys) or default


def resolve_float_value(
    cli_value: Optional[float],
    env_name: str,
    config: Mapping[str, Any],
    config_keys: tuple[str, ...],
    default: float,
) -> float:
    value: Any = cli_value
    if value is None:
        value = os.environ.get(env_name)
    if not config_value_is_present(value):
        value = config_text_value(config, *config_keys)
    if not config_value_is_present(value):
        return float(default)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{env_name} must be a number of seconds.") from exc
    if result <= 0:
        raise ConfigError(f"{env_name} must be greater than 0.")
    return result


def build_starops_config(args: argparse.Namespace) -> StarOpsConfig:
    file_config = read_file_config(args)
    required = {
        "employeeId": resolve_text_value(
            "STAROPS_AGENT_EMPLOYEE",
            file_config,
            "employeeId",
        ),
        "workspace": resolve_text_value(
            "STAROPS_AGENT_WORKSPACE",
            file_config,
            "workspace",
        ),
        "uid": resolve_text_value(
            "STAROPS_AGENT_UID",
            file_config,
            "uid",
        ),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ConfigError(
            "Missing required STAROps configuration values: "
            + ", ".join(missing)
            + ". Set STAROPS_AGENT_EMPLOYEE, STAROPS_AGENT_WORKSPACE, and STAROPS_AGENT_UID, "
            + "or provide employeeId/workspace/uid in a config file."
        )

    endpoint = resolve_text_value("STAROPS_AGENT_ENDPOINT", file_config, "endpoint", default=DEFAULT_ENDPOINT)
    timeout_seconds = resolve_float_value(
        getattr(args, "timeout", None),
        "STAROPS_AGENT_TIMEOUT",
        file_config,
        ("timeout",),
        DEFAULT_TIMEOUT_SECONDS,
    )
    raw_idle_timeout = resolve_float_value(
        getattr(args, "idle_timeout", None),
        "STAROPS_AGENT_IDLE_TIMEOUT",
        file_config,
        ("idleTimeout",),
        DEFAULT_IDLE_TIMEOUT_SECONDS,
    )
    project = getattr(args, "project", None) or resolve_text_value("STAROPS_AGENT_PROJECT", file_config, "project")
    idle_timeout_seconds = max(1.0, min(raw_idle_timeout, timeout_seconds))
    assistant_id = required["employeeId"]

    return StarOpsConfig(
        employee=required["employeeId"],
        workspace=required["workspace"],
        uid=required["uid"],
        endpoint=endpoint,
        timeout_seconds=timeout_seconds,
        idle_timeout_seconds=idle_timeout_seconds,
        assistant_id=assistant_id,
        project=project,
    )


class StarOpsAgentClient:
    def __init__(
        self,
        config: StarOpsConfig,
        credential_provider: Any = None,
        transport: Optional[Callable[..., Any]] = None,
        out: Any = None,
        err: Any = None,
    ):
        self.config = config
        self.host = config.endpoint
        self.session_id = resolve_session_id()
        self.user_agent = build_user_agent(self.session_id)
        self.credential_provider = credential_provider if credential_provider is not None else self._default_credentials()
        self.transport = transport or requests.request
        self.out = out if out is not None else sys.stdout
        self.err = err if err is not None else sys.stderr
        self._seen_message_keys: set[str] = set()
        self._seen_tool_status_keys: set[str] = set()

    def _default_credentials(self) -> Any:
        if CredentialClient is None:
            raise CredentialError(
                "Alibaba Cloud Credentials SDK is not installed. "
                "Run `pip3 install -r scripts/requirements.txt` from the skill root directory."
            )
        try:
            return CredentialClient()
        except Exception as exc:
            raise CredentialError(f"Failed to initialize Alibaba Cloud Credentials default chain: {exc}") from exc

    def _get_current_credential(self) -> Any:
        try:
            credential = self.credential_provider.get_credential()
        except Exception as exc:
            raise CredentialError(f"Failed to load Alibaba Cloud Credentials from the default chain: {exc}") from exc

        access_key_id = call_or_none(credential, "get_access_key_id")
        access_key_secret = call_or_none(credential, "get_access_key_secret")
        if not access_key_id or not access_key_secret:
            raise CredentialError(
                "Alibaba Cloud Credentials default chain did not return an AccessKey ID and secret. "
                "Configure a supported credentials source, such as environment variables, profile, "
                "RAM role, or STS credentials."
            )
        return credential

    def sign_request(self, request: SignatureRequest) -> SignatureRequest:
        credential = self._get_current_credential()
        access_key_id = call_or_none(credential, "get_access_key_id")
        access_key_secret = call_or_none(credential, "get_access_key_secret")
        security_token = call_or_none(credential, "get_security_token")
        if security_token:
            request.headers["x-acs-security-token"] = security_token

        canonical_request, signed_headers = build_canonical_request(request)
        hashed_canonical_request = sha256_hex(canonical_request.encode("utf-8"))
        string_to_sign = f"{ALGORITHM}\n{hashed_canonical_request}"
        signature = hmac.new(
            str(access_key_secret).encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().lower()
        request.headers["Authorization"] = (
            f"{ALGORITHM} Credential={access_key_id},"
            f"SignedHeaders={signed_headers},Signature={signature}"
        )
        return request

    def _request(
        self,
        method: str,
        path: str,
        action: str,
        query: Optional[Mapping[str, Any]] = None,
        body: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        body_bytes = json.dumps(body or {}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = SignatureRequest(
            method=method,
            path=path,
            query=query or {},
            host=self.host,
            action=action,
            version=API_VERSION,
            user_agent=self.user_agent,
            body=body_bytes if method.upper() != "GET" else b"",
        )
        self.sign_request(request)
        query_string = canonicalize_query(request.query)
        url = f"https://{self.host}{path}" + (f"?{query_string}" if query_string else "")
        try:
            response = self.transport(
                request.method,
                url,
                headers=dict(request.headers),
                data=request.body if request.method != "GET" else None,
                timeout=30,
            )
        except Exception as exc:
            if isinstance(exc, StarOpsTimeoutError):
                raise
            raise StarOpsHTTPError(f"{action} request failed before receiving a response: {exc}") from exc

        status_code = int(getattr(response, "status_code", 0) or 0)
        if status_code < 200 or status_code >= 300:
            response_text = getattr(response, "text", "")
            raise StarOpsHTTPError(f"{action} failed with HTTP {status_code}: {response_text}")

        text = getattr(response, "text", "")
        if not text:
            return {}
        try:
            payload = response.json()
        except Exception as exc:
            raise StarOpsHTTPError(f"{action} returned non-JSON response: {text[:500]}") from exc
        if isinstance(payload, dict):
            return payload
        return {"data": payload}

    def _stream_request(
        self,
        method: str,
        path: str,
        action: str,
        body: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[dict[str, Any]]:
        body_bytes = json.dumps(body or {}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = SignatureRequest(
            method=method,
            path=path,
            query={},
            host=self.host,
            action=action,
            version=API_VERSION,
            user_agent=self.user_agent,
            body=body_bytes,
        )
        self.sign_request(request)
        url = f"https://{self.host}{path}"
        try:
            try:
                response = self.transport(
                    request.method,
                    url,
                    headers=dict(request.headers),
                    data=request.body,
                    timeout=self._request_timeout(),
                    stream=True,
                )
            except TypeError:
                response = self.transport(
                    request.method,
                    url,
                    headers=dict(request.headers),
                    data=request.body,
                    timeout=self._request_timeout(),
                )
            except requests.exceptions.ReadTimeout as exc:
                raise self._stream_idle_timeout_error(action) from exc
        except Exception as exc:
            if isinstance(exc, StarOpsTimeoutError):
                raise
            raise StarOpsHTTPError(f"{action} request failed before receiving a response: {exc}") from exc

        status_code = int(getattr(response, "status_code", 0) or 0)
        if status_code < 200 or status_code >= 300:
            response_text = getattr(response, "text", "")
            raise StarOpsHTTPError(f"{action} failed with HTTP {status_code}: {response_text}")

        try:
            try:
                yield from iter_sse_payloads(response)
            except requests.exceptions.ReadTimeout as exc:
                raise self._stream_idle_timeout_error(action) from exc
        finally:
            close_response = getattr(response, "close", None)
            if callable(close_response):
                close_response()

    def _request_timeout(self) -> tuple[float, float]:
        idle_timeout = max(1.0, min(self.config.idle_timeout_seconds, self.config.timeout_seconds))
        connect_timeout = max(1.0, min(30.0, idle_timeout))
        return (connect_timeout, idle_timeout)

    def _stream_idle_timeout_error(self, action: str) -> StarOpsTimeoutError:
        seconds = format_seconds(self.config.idle_timeout_seconds)
        return StarOpsTimeoutError(
            f"No {action} stream data was received for {seconds} seconds. "
            "The STAROps stream may be stalled; retry with --thread if a THREAD line was printed, "
            "or increase --idle-timeout for intentionally quiet long-running investigations."
        )

    def variables(self) -> dict[str, str]:
        variables = {
            "workspace": self.config.workspace,
        }
        if self.config.project:
            variables["project"] = self.config.project
        return variables

    def create_thread(self, question: str) -> str:
        idempotency_key = sha256_hex(
            f"{self.config.employee}|{self.config.workspace}|{compact_title(question)}".encode("utf-8")
        )
        body = {
            "title": compact_title(question),
            "idempotencyKey": idempotency_key,
            "variables": self.variables(),
            "attributes": {
                "source": "alibabacloud-starops-chat",
            },
        }
        payload = response_body(
            self._request(
                "POST",
                f"/digitalEmployee/{quoted_path_part(self.config.employee)}/thread",
                "CreateThread",
                body=body,
            )
        )
        thread_id = payload.get("threadId") if isinstance(payload, dict) else None
        if not thread_id:
            raise StarOpsHTTPError(f"CreateThread succeeded but no threadId was returned: {payload}")
        return str(thread_id)

    def stream_chat(self, thread_id: str, question: str) -> Iterable[dict[str, Any]]:
        body = {
            "action": "create",
            "digitalEmployeeName": self.config.employee,
            "threadId": thread_id,
            "messages": [
                {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "contents": [
                        {
                            "type": "text",
                            "value": question,
                        }
                    ],
                }
            ],
            "variables": self.variables(),
        }
        return self._stream_request("POST", "/chat", "CreateChat", body=body)

    def ask(self, question: str, thread_id: Optional[str] = None, mode: OutputMode = OutputMode.CLI) -> AskResult:
        if not question or not question.strip():
            raise ConfigError("--question cannot be empty.")
        if thread_id:
            validate_thread_id(thread_id)

        self._seen_message_keys.clear()
        self._seen_tool_status_keys.clear()
        effective_thread_id = thread_id or self.create_thread(question)
        self._emit_thread(effective_thread_id, mode)
        request_start_ms = int(time.time() * 1000)
        answers, last_status, trace_id = self._consume_chat_stream(effective_thread_id, question, request_start_ms, mode)
        self._emit_done(effective_thread_id, last_status, answers, mode)
        return AskResult(effective_thread_id, trace_id, last_status, answers)

    def _consume_chat_stream(
        self,
        effective_thread_id: str,
        question: str,
        request_start_ms: int,
        mode: OutputMode,
    ) -> tuple[list[str], Optional[str], Optional[str]]:
        deadline = time.monotonic() + self.config.timeout_seconds
        answers: list[str] = []
        trace_id: Optional[str] = None
        for payload in self.stream_chat(effective_thread_id, question):
            if time.monotonic() > deadline:
                raise StarOpsTimeoutError(
                    f"Timed out waiting for STAROps Agent thread {effective_thread_id} after "
                    f"{int(self.config.timeout_seconds)} seconds."
                )
            if isinstance(payload, dict) and payload.get("traceId"):
                trace_id = optional_str(payload.get("traceId"))
            stream_finished = False
            for message in extract_messages(payload):
                if is_done_message(message) or has_task_finished_event(message):
                    stream_finished = True
                if is_historical_message(message, request_start_ms):
                    continue
                self._emit_tool_updates(message, mode)
                content = extract_assistant_text(message)
                if not content:
                    continue
                key = message_key(message, content)
                if key in self._seen_message_keys:
                    continue
                self._seen_message_keys.add(key)
                answers.append(content)
                self._emit_message(content, mode)
            if stream_finished:
                return answers, "completed", trace_id
        return answers, "completed", trace_id

    def _emit(self, text: str = "", *, end: str = "\n") -> None:
        print(text, end=end, file=self.out, flush=True)

    def _emit_err(self, text: str = "", *, end: str = "\n") -> None:
        print(text, end=end, file=self.err, flush=True)

    def _emit_json(self, payload: Mapping[str, Any]) -> None:
        self._emit(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    def _emit_thread(self, thread_id: str, mode: OutputMode) -> None:
        starops_url = build_starops_console_url(thread_id, self.config.assistant_id)
        if mode == OutputMode.JSON:
            self._emit_json({"type": "thread", "thread_id": thread_id, "starops_url": starops_url})
        elif mode == OutputMode.PIPE:
            self._emit(f"THREAD: {thread_id}")
            self._emit(f"STAROPS_URL: {starops_url}")
        else:
            self._emit(f"[Thread: {thread_id}]")
            self._emit(f"[STAROps: {starops_url}]")

    def _emit_message(self, content: str, mode: OutputMode) -> None:
        if mode == OutputMode.JSON:
            self._emit_json({"type": "message", "role": "assistant", "content": content})
        elif mode == OutputMode.CLI:
            self._emit(content)

    def _emit_done(self, thread_id: str, status: Optional[str], answers: list[str], mode: OutputMode) -> None:
        if mode == OutputMode.JSON:
            self._emit_json({"type": "done", "thread_id": thread_id, "status": status})
        elif mode == OutputMode.PIPE:
            answer_text = "\n\n".join(answer for answer in answers if answer.strip()).strip()
            self._emit("=== STAROPS ANSWER BEGIN ===")
            self._emit(answer_text or "(No assistant answer was returned.)")
            self._emit("=== STAROPS ANSWER END ===")

    def _progress(self, text: str, mode: OutputMode) -> None:
        if mode == OutputMode.JSON:
            self._emit_json({"type": "progress", "message": text})
        elif mode == OutputMode.CLI:
            self._emit_err(text)
        elif mode == OutputMode.PIPE:
            self._emit_err(text)

    def _emit_tool_updates(self, message: Mapping[str, Any], mode: OutputMode) -> None:
        for tool in extract_tool_records(message):
            if tool.status:
                status_key = "|".join(
                    [
                        tool.tool_call_id,
                        tool.tool_id,
                        tool.name,
                        tool.status,
                    ]
                )
                if status_key not in self._seen_tool_status_keys:
                    self._seen_tool_status_keys.add(status_key)
                    self._emit_tool_status(tool, mode)

            if tool.name in TEXT_TOOL_NAMES and tool.contents and mode == OutputMode.PIPE:
                self._emit_err("\n".join(tool.contents))

    def _emit_tool_status(self, tool: ToolRecord, mode: OutputMode) -> None:
        if mode == OutputMode.JSON:
            self._emit_json({"type": "tool", "name": tool.name, "status": tool.status})
            return

        if mode in {OutputMode.CLI, OutputMode.PIPE}:
            self._emit_err(format_tool_status(tool))


def call_or_none(obj: Any, method_name: str) -> Any:
    method = getattr(obj, method_name, None)
    if method is None:
        return None
    return method()


def compact_title(question: str, limit: int = 80) -> str:
    normalized = re.sub(r"\s+", " ", question.strip())
    return normalized[:limit] or "STAROps question"


def optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def format_seconds(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def validate_thread_id(thread_id: str) -> None:
    if not re.match(r"^[A-Za-z0-9_.:-]+$", thread_id):
        raise ConfigError("--thread contains unsupported characters.")


def iter_sse_payloads(response: Any) -> Iterable[dict[str, Any]]:
    data_lines: list[str] = []

    def flush() -> Optional[dict[str, Any]]:
        if not data_lines:
            return None
        raw = "\n".join(data_lines).strip()
        data_lines.clear()
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"messages": [{"role": "assistant", "content": raw}]}
        return payload if isinstance(payload, dict) else {"data": payload}

    if hasattr(response, "iter_lines"):
        # Server-sent events are UTF-8. Decode bytes ourselves so requests does
        # not fall back to ISO-8859-1 when the response omits a charset.
        lines = response.iter_lines(decode_unicode=False)
    else:
        lines = str(getattr(response, "text", "") or "").splitlines()

    for raw_line in lines:
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else str(raw_line)
        line = line.rstrip("\r")
        if not line:
            payload = flush()
            if payload is not None:
                yield payload
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
            continue
        if line.startswith("event:") or line.startswith("id:") or line.startswith("retry:"):
            continue
        if line.lstrip().startswith("{"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                yield payload

    payload = flush()
    if payload is not None:
        yield payload


def normalize_epoch_ms(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = int(float(text))
    except ValueError:
        return None
    if number > 10**16:
        return number // 1_000_000
    if number > 10**14:
        return number // 1_000
    if number < 10**11:
        return number * 1_000
    return number


def is_historical_message(message: Mapping[str, Any], request_start_ms: int) -> bool:
    timestamp_ms = normalize_epoch_ms(message.get("timestamp"))
    if timestamp_ms is None:
        return False
    return timestamp_ms < request_start_ms


def extract_messages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    body = response_body(payload)
    if not isinstance(body, dict):
        return []
    candidates = body.get("messages")
    if candidates is None and isinstance(body.get("data"), dict):
        candidates = body["data"].get("messages")
    if candidates is None and isinstance(body.get("items"), list):
        candidates = body.get("items")
    if not isinstance(candidates, list):
        return []
    return [message for message in candidates if isinstance(message, dict)]


def role_is_assistant(role: Any) -> bool:
    normalized = str(role or "").strip().lower()
    return normalized in {"assistant", "agent", "system", "ai", "数字员工", "助手"}


def extract_assistant_text(message: Mapping[str, Any]) -> str:
    if not role_is_assistant(message.get("role")):
        return ""
    parts: list[str] = []
    for field in ("content", "text", "value", "answer"):
        value = message.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    items = message.get("items")
    if isinstance(items, list):
        parts.extend(extract_text_parts(items))
    contents = message.get("contents")
    if isinstance(contents, list):
        parts.extend(extract_text_parts(contents))
    tools = message.get("tools")
    if isinstance(tools, list):
        parts.extend(extract_text_tool_parts(tools))
    return "\n".join(dedupe_preserve_order(parts)).strip()


def extract_tool_records(message: Mapping[str, Any]) -> list[ToolRecord]:
    raw_tools: list[Any] = []
    tools = message.get("tools")
    if isinstance(tools, list):
        raw_tools.extend(tools)

    items = message.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("tools"), list):
                raw_tools.extend(item["tools"])

    records: list[ToolRecord] = []
    for tool in raw_tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or tool.get("id") or "unknown_tool").strip()
        tool_id = str(tool.get("id") or "").strip()
        tool_call_id = str(tool.get("toolCallId") or tool.get("callId") or "").strip()
        status = str(tool.get("status") or "").strip().lower()
        contents = extract_text_parts(tool.get("contents") or []) if isinstance(tool.get("contents"), list) else []
        records.append(
            ToolRecord(
                name=name,
                tool_id=tool_id,
                tool_call_id=tool_call_id,
                status=status,
                contents=contents,
            )
        )
    return records


def format_tool_status(tool: ToolRecord) -> str:
    labels = {
        "init": "init",
        "start": "started",
        "progress": "running",
        "suspended": "suspended",
        "success": "done",
        "fail": "failed",
    }
    label = labels.get(tool.status, tool.status or "updated")
    return f"[tool:{label}] {tool.name}"


def extract_text_tool_parts(tools: Iterable[Any]) -> list[str]:
    parts: list[str] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or tool.get("id") or "").strip()
        if name not in TEXT_TOOL_NAMES:
            continue
        contents = tool.get("contents")
        if isinstance(contents, list):
            parts.extend(extract_text_parts(contents))
    return parts


def extract_text_parts(values: Iterable[Any]) -> list[str]:
    parts: list[str] = []
    for value in values:
        if isinstance(value, str):
            if value.strip():
                parts.append(value.strip())
            continue
        if not isinstance(value, dict):
            continue
        for field in ("text", "value", "content", "delta", "answer", "message"):
            field_value = value.get(field)
            if isinstance(field_value, str) and field_value.strip():
                parts.append(field_value.strip())
        for nested_field in ("contents", "items", "data"):
            nested = value.get(nested_field)
            if isinstance(nested, list):
                parts.extend(extract_text_parts(nested))
            elif isinstance(nested, dict):
                parts.extend(extract_text_parts([nested]))
    return parts


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def message_key(message: Mapping[str, Any], content: str) -> str:
    for field in ("messageId", "id", "traceId"):
        value = message.get(field)
        if value:
            return str(value)
    return sha256_hex(
        json.dumps(
            {
                "role": message.get("role"),
                "timestamp": message.get("timestamp"),
                "runId": message.get("runId"),
                "content": content,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    )


def has_task_finished_event(message: Mapping[str, Any]) -> bool:
    values: list[Any] = [message]
    items = message.get("items")
    if isinstance(items, list):
        values.extend(items)
    for item in values:
        if not isinstance(item, dict):
            continue
        event_name = item.get("event") or item.get("eventType") or item.get("type") or item.get("name")
        if str(event_name or "").strip().lower() == "task_finished":
            return True
    return False


def is_done_message(message: Mapping[str, Any]) -> bool:
    return str(message.get("type") or "").strip().lower() in {"done", "task_finished"}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Call Alibaba Cloud STAROps Agent OpenAPI through an official-style Python Skill script.",
    )
    parser.add_argument("--question", required=True, help="Natural language question to send to STAROps Agent.")
    parser.add_argument("--thread", help="Existing STAROps thread ID for follow-up questions.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSONL events.")
    parser.add_argument("--pipe", action="store_true", help="Emit agent-friendly pipe output with THREAD and answer delimiters.")
    parser.add_argument(
        "--config",
        help=(
            "Path to optional JSON config file. Loaded after "
            f"~/{CONFIG_DIR}/{CONFIG_FILE_NAME} and ./{CONFIG_DIR}/{CONFIG_FILE_NAME}."
        ),
    )
    parser.add_argument("--project", help="Optional STAROps project variable to pass to the Agent.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="CreateChat stream timeout in seconds. Defaults to 1800.",
    )
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=None,
        help="Maximum seconds to wait for the next CreateChat SSE event before failing. Defaults to 60.",
    )
    return parser


def mode_from_args(args: argparse.Namespace) -> OutputMode:
    if args.json and args.pipe:
        raise ConfigError("Use only one output mode: --json or --pipe.")
    if args.json:
        return OutputMode.JSON
    if args.pipe:
        return OutputMode.PIPE
    return OutputMode.CLI


def emit_error(exc: Exception, mode: OutputMode) -> None:
    if mode == OutputMode.JSON:
        print(json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False), flush=True)
    else:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    mode = OutputMode.CLI
    try:
        mode = mode_from_args(args)
        config = build_starops_config(args)
        client = StarOpsAgentClient(config)
        client.ask(args.question, thread_id=args.thread, mode=mode)
        return 0
    except (ConfigError, CredentialError, StarOpsHTTPError, StarOpsTimeoutError) as exc:
        emit_error(exc, mode)
        return 1
    except KeyboardInterrupt:
        emit_error(RuntimeError("Interrupted while waiting for STAROps Agent."), mode)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
