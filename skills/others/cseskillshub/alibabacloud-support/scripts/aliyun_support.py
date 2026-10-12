#!/usr/bin/env python3
"""Local client for the alibabacloud-support Agent Skill."""

from __future__ import annotations

import argparse
import ast
import hashlib
import hmac
import json
import locale
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

APP_NAME = "alibabacloud-support"
VERSION = "2.0.0"
# The aliyun CLI resolves the Workorder endpoint and API version itself; these
# constants are informational only and are never passed as generic-RPC flags.
API_VERSION = "2021-06-10"
DEFAULT_ENDPOINT = "workorder.aliyuncs.com"
DEFAULT_REGION = "cn-hangzhou"
# aliyun CLI plugin mode (MUST SA-2.11): every Workorder call uses the
# lowercase-hyphenated plugin command, never the PascalCase generic-RPC form,
# which aliyun CLI 3.3+/3.4 rejects with "unchecked version" for Workorder.
WORKORDER_PLUGIN_COMMANDS = {
    "ListProducts": "list-products",
    "ListCategories": "list-categories",
    "ListTickets": "list-tickets",
    "GetTicket": "get-ticket",
    "ListTicketNotes": "list-ticket-notes",
    "CreateTicket": "create-ticket",
    "ReplyTicket": "reply-ticket",
    "CloseTicket": "close-ticket",
    "EvaluateTicket": "evaluate-ticket",
}
# API request parameter whose CLI flag name is not the kebab-case form.
WORKORDER_PLUGIN_PARAM_OVERRIDES = {"Language": "biz-language"}
SESSION_ID_ENV = "SKILL_SESSION_ID"
USER_AGENT_PREFIX = f"AlibabaCloud-Agent-Skills/{APP_NAME}"
USER_AGENT_ENVS = ("ALIBABACLOUD_USER_AGENT", "ALIBABA_CLOUD_USER_AGENT")
HEX_32_PATTERN = re.compile(r"^[0-9a-f]{32}$")
# The version component of the User-Agent is declared only in
# references/manifest.json and is read from that file at runtime. It is never
# hardcoded here, never derived from the self-update VERSION constant, and never
# replaced by a placeholder when the manifest cannot be read.
MANIFEST_PATH = Path(__file__).resolve().parent.parent / "references" / "manifest.json"
SKILL_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
DEFAULT_RULES_OSS_URL = "https://aliyun-cse-support.oss-cn-hangzhou.aliyuncs.com/"
DEFAULT_RULES_OSS_PREFIX = ""
TICKET_TITLE_PREFIX = "[aliyun-support]"
CLI_PATH_ENV = "ALIBABACLOUD_SUPPORT_CLI_PATH"
CLI_ENCODING_ENV = "ALIBABACLOUD_SUPPORT_CLI_ENCODING"
CLI_INSTALL_DOC_URL = "https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli"
CLI_CREDENTIAL_DOC_URL = "https://help.aliyun.com/zh/cli/configure-credentials/"
CLI_BLOCKED_CAPABILITIES = (
    "catalog",
    "ticket_list",
    "ticket_create",
    "create_timeout_reconciliation",
    "ticket_query",
    "ticket_reply",
    "ticket_close",
    "ticket_evaluate",
)
WORKORDER_FEATURE_APIS = {
    "catalog": ("ListProducts", "ListCategories"),
    "ticket_list": ("ListTickets",),
    "ticket_create": ("CreateTicket",),
    "create_timeout_reconciliation": ("ListTickets", "GetTicket"),
    "ticket_query": ("GetTicket", "ListTicketNotes"),
    "ticket_reply": ("GetTicket", "ReplyTicket"),
    "ticket_close": ("GetTicket", "CloseTicket"),
    "ticket_evaluate": ("GetTicket", "EvaluateTicket"),
}
NON_IDEMPOTENT_WORKORDER_ACTIONS = frozenset({
    "CreateTicket",
    "ReplyTicket",
    "CloseTicket",
    "EvaluateTicket",
})
CHECK_INTERVAL_SECONDS = 7 * 24 * 60 * 60
CONFIRMATION_TTL_SECONDS = 30 * 60
CREATE_RECONCILIATION_CLOCK_SKEW_MS = 60 * 1000
MAX_LIST_BYTES = 1024 * 1024
MAX_FILES = 500
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024
MAX_LIST_PAGES = 100
MAX_CLIENT_FILE_BYTES = 1024 * 1024
CACHE_SCHEMA_VERSION = 2
CLIENT_UPDATE_TRANSACTION_SCHEMA_VERSION = 1
TERMINAL_STATUS_VALUES = {"6", "closed", "resolved", "confirmed"}
TERMINAL_STATUS_LABELS = {"已关闭", "待你评价", "已完成"}  # status labels returned by Workorder in Chinese
TICKET_WEB_URL_TEMPLATE = "https://smartservice.console.aliyun.com/service/ticket-detail?ticketId={ticket_id}"
GITHUB_OWNER = "aliyun"
GITHUB_REPOSITORY = "alibabacloud-aiops-skills"
GITHUB_BRANCH = "master"
GITHUB_SKILL_ROOT = "skills/others/cseskillshub/alibabacloud-support"
GITHUB_API_ROOT = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPOSITORY}"
GITHUB_RAW_ROOT = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPOSITORY}"
GITHUB_API_ORIGIN = ("https", "api.github.com", 443)
GITHUB_RAW_ORIGIN = ("https", "raw.githubusercontent.com", 443)
CLIENT_BUNDLE_PATHS = ("SKILL.md", "scripts/aliyun_support.py")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

PRODUCT_KEYS = {"product", "aliases", "issueTypes"}
ISSUE_KEYS = {"name", "keywords", "categoryKeywords", "categoryHints", "collect"}
FIELD_KEYS = {"field", "label", "required", "type", "description", "example", "enum", "maxLength"}
FORBIDDEN_KEY_PARTS = {
    "command",
    "shell",
    "script",
    "sql",
    "regex",
    "pattern",
    "url",
    "endpoint",
    "collector",
    "credential",
    "accesskey",
    "password",
    "cookie",
    "token",
    "secret",
}
FORBIDDEN_COLLECTION_FIELD_NAMES = {
    "accesstoken",
    "apikey",
    "apitoken",
    "authorization",
    "authorizationheader",
    "authorizationvalue",
    "authtoken",
    "bearertoken",
    "clientsecret",
    "cookie",
    "cookieheader",
    "cookievalue",
    "credential",
    "credentials",
    "credentialvalue",
    "idtoken",
    "password",
    "passwd",
    "privatekey",
    "refreshtoken",
    "secret",
    "secretkey",
    "securitytoken",
    "sessiontoken",
    "token",
}
FORBIDDEN_COLLECTION_FIELD_PARTS = {
    "accesskeysecret",
    "accesstoken",
    "apitoken",
    "authorizationheader",
    "authorizationvalue",
    "authtoken",
    "bearertoken",
    "clientsecret",
    "cookieheader",
    "cookievalue",
    "credentialvalue",
    "idtoken",
    "password",
    "passwd",
    "privatekey",
    "refreshtoken",
    "secretaccesskey",
    "securitytoken",
    "sessiontoken",
}
SENSITIVE_COLLECTION_LABEL_PATTERN = re.compile(
    r"(?:密码|口令|私钥|密钥|令牌|凭据|凭证|验证码|access\s*key\s*secret|secret\s*access\s*key|api\s*key|authorization|cookie|credentials?|token|secret)",
    re.I,
)
SENSITIVE_COLLECTION_TEXT_PATTERN = re.compile(
    r"(?:密码|口令|私钥|密钥|令牌|凭据|凭证|验证码|认证信息|鉴权信息|登录时(?:输入|设置).{0,12}(?:字符|内容|值)|access\s*key\s*secret|secret\s*access\s*key|api\s*key|authorization|cookie|credentials?|access\s*token|api\s*token|auth\s*token|bearer\s*token|client\s*secret|id\s*token|private\s*key|refresh\s*token|session\s*token|password|passwd)",
    re.I,
)
SENSITIVE_COLLECTION_FIELD_PARTS = (
    "accesskey",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "passwd",
    "privatekey",
    "secret",
    "token",
    "verificationcode",
)
COLLECTION_ACTION_PATTERN = re.compile(
    r"(?:填写|提供|输入|提交|粘贴|上传|发送|fill|provide|enter|submit|paste|upload|send)",
    re.I,
)
UNSAFE_VALUE_MARKER_PATTERN = re.compile(
    r"(?:完整|全部|全量|所有(?:字符|内容)|原始|原值|明文|未经脱敏|未脱敏|实际值|真实值|本身|full|raw|plain|cleartext|unmasked|unredacted)",
    re.I,
)
SAFE_COLLECTION_CREDENTIAL_FIELDS = {
    "authorizationstatus": ("状态", "是否", "status"),
    "authorizationscope": ("范围", "项目", "scope"),
    "tokenusage": ("用量", "使用量", "usage"),
    "apikeyprefix": ("前缀", "prefix"),
    "apikeytype": ("类型", "前缀", "type"),
}
SAFE_CREDENTIAL_REFERENCE_FIELDS = {
    "operationname": ("操作名称", "operation name"),
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:ENCRYPTED |RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(
        r"[\"']?(?:authorization|cookie|pass(?:[\s_-])*word|passwd|access(?:[\s_-])*key(?:[\s_-])*secret|secret(?:[\s_-])*access(?:[\s_-])*key|api(?:[\s_-])*key|token|密码|密钥|令牌|认证信息)[\"']?\s*[：:=]\s*[\"']?\S+",
        re.I,
    ),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I),
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}(?![A-Za-z0-9])", re.I),
    re.compile(
        r"[?&](?:x-oss-signature|x-oss-security-token|x-amz-signature|x-amz-credential|signature|security-token|accesskeyid|se|sig)=[^&#\s]+",
        re.I,
    ),
]
EMAIL_PATTERN = re.compile(r"(?<![\w.+-])([\w.+-]{1,64})@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_PATTERN = re.compile(r"(?<!\d)(1[3-9]\d)(\d{4})(\d{4})(?!\d)")
ACCESS_KEY_ID_PATTERN = re.compile(r"(?<![A-Za-z0-9])(LTAI[A-Za-z0-9]{12,})(?![A-Za-z0-9])")
ID_CARD_PATTERN = re.compile(r"(?<!\d)(\d{6})(\d{8})(\d{3}[0-9Xx])(?!\d)")
LABELED_UID_PATTERN = re.compile(
    r"((?:阿里云)?(?:用户|客户|账号|账户)\s*(?:UID|ID)|(?:阿里云)?UID|(?:user|customer|account)\s*id)\s*([：:=]\s*)(\d{8,32})",
    re.I,
)
URL_PATTERN = re.compile(r"https?://", re.I)
PROMPT_INJECTION_PATTERN = re.compile(
    r"(?:忽略.{0,12}(?:指令|规则)|执行.{0,8}(?:命令|脚本)|(?:终端|命令行).{0,12}(?:运行|执行)|(?:运行|执行)\s*(?:uname|whoami|curl|wget|python3?|node|npm|npx|bash|sh|zsh|powershell|cmd)\b|system\s*prompt|run\s+(?:command|shell)|sudo\b|powershell\b|\$\(|`)",
    re.I,
)
OSS_PRODUCT_KEY_PATTERN = re.compile(r"products/[a-z0-9][a-z0-9._-]*\.json")
DEFAULT_ISSUE = {
    "name": "General issue",
    "keywords": ["Problem", "Abnormal", "Error message", "Consultation"],
    "categoryHints": ["General consultation"],
    "collect": [
        {
            "field": "regionId",
            "label": "Region",
            "required": False,
            "type": "string",
            "description": "Provide the region identifier when the resource is region scoped",
            "maxLength": 64,
        },
        {
            "field": "resourceId",
            "label": "Resource identifier",
            "required": False,
            "type": "string",
            "description": "Provide the redacted resource identifier when a specific instance or resource is involved",
            "maxLength": 120,
        },
        {
            "field": "occurrenceTime",
            "label": "Occurrence time",
            "required": True,
            "type": "string",
            "description": "Include date, time and time zone",
            "maxLength": 64,
        },
        {
            "field": "issueDescription",
            "label": "Issue description",
            "required": True,
            "type": "string",
            "description": "Describe the expected result, the actual behaviour and the trigger conditions",
            "maxLength": 1000,
        },
        {
            "field": "errorCode",
            "label": "Error code",
            "required": False,
            "type": "string",
            "maxLength": 120,
        },
        {
            "field": "errorMessage",
            "label": "Error message",
            "required": False,
            "type": "string",
            "description": "Provide the complete error message with sensitive content removed",
            "maxLength": 1000,
        },
        {
            "field": "requestId",
            "label": "Request identifier",
            "required": False,
            "type": "string",
            "description": "Provide it when a request identifier exists",
            "maxLength": 120,
        },
        {
            "field": "environment",
            "label": "Runtime environment",
            "required": False,
            "type": "string",
            "description": "Describe the operating system, client, SDK or console environment and version",
            "maxLength": 500,
        },
        {
            "field": "impactScope",
            "label": "Impact scope",
            "required": True,
            "type": "string",
            "description": "Describe the affected business, resource count, user scope and severity",
            "maxLength": 500,
        },
    ],
}


class ClientError(RuntimeError):
    """Expected validation, configuration, or API error."""


class WorkorderIndeterminateError(ClientError):
    """A non-idempotent Workorder call may have reached the service without a reliable result."""

    def __init__(self, action: str, reason: str):
        self.action = action
        self.reason = reason
        super().__init__(f"{action} {reason}; the write result may be indeterminate, do not retry automatically")


class WorkorderTimeoutError(WorkorderIndeterminateError):
    """Workorder call timed out and may have an indeterminate write result."""

    def __init__(self, action: str):
        super().__init__(action, "call timed out")


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject every cross-origin redirect before urllib follows it."""

    def __init__(self, expected_origin: tuple[str, str, int]):
        super().__init__()
        self.expected_origin = expected_origin

    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        validate_https_url(new_url)
        if url_origin(new_url) != self.expected_origin:
            raise ClientError("the remote request was redirected to another origin, so the update stopped")
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def environment_value(primary: str, legacy: str, default: Optional[str] = None) -> tuple[Optional[str], bool]:
    value = os.environ.get(primary)
    if value is not None:
        return value, False
    legacy_value = os.environ.get(legacy)
    if legacy_value is not None:
        return legacy_value, True
    return default, False


def default_home() -> Path:
    configured, _ = environment_value("ALIBABACLOUD_SUPPORT_HOME", "ALIYUN_SUPPORT_HOME")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / APP_NAME


def emit(data: Any) -> None:
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    binary_stdout = getattr(sys.stdout, "buffer", None)
    if binary_stdout is not None:
        binary_stdout.write(payload)
        binary_stdout.flush()
        return
    sys.stdout.write(payload.decode("utf-8"))
    sys.stdout.flush()


def candidate_text_encodings() -> list[str]:
    candidates = ["utf-8-sig", locale.getpreferredencoding(False), "gb18030"]
    result: list[str] = []
    seen: set[str] = set()
    for encoding in candidates:
        normalized = encoding.lower().replace("_", "-")
        if normalized not in seen:
            seen.add(normalized)
            result.append(encoding)
    return result


def decode_candidates(
    data: bytes,
    source: str,
    encodings: Optional[Iterable[str]] = None,
) -> list[tuple[str, str]]:
    attempted: list[str] = []
    decoded: list[tuple[str, str]] = []
    seen_encodings: set[str] = set()
    seen_text: set[str] = set()
    for encoding in encodings or candidate_text_encodings():
        normalized = encoding.lower().replace("_", "-")
        if normalized in seen_encodings:
            continue
        seen_encodings.add(normalized)
        attempted.append(encoding)
        try:
            text = data.decode(encoding, errors="strict")
        except (LookupError, UnicodeDecodeError):
            continue
        if text not in seen_text:
            seen_text.add(text)
            decoded.append((encoding, text))
    if not decoded:
        raise ClientError(f"{source} encoding could not be resolved; strictly attempted: {', '.join(attempted)}")
    return decoded


def decode_external_bytes(data: bytes, source: str) -> str:
    if not data:
        return ""
    return decode_candidates(data, source)[0][1]


def configured_cli_encoding() -> Optional[str]:
    configured = os.environ.get(CLI_ENCODING_ENV)
    if configured is None or not configured.strip():
        return None
    normalized = configured.strip().lower().replace("_", "-")
    aliases = {
        "utf8": "utf-8-sig",
        "utf-8": "utf-8-sig",
        "utf-8-sig": "utf-8-sig",
        "gbk": "gb18030",
        "cp936": "gb18030",
        "gb18030": "gb18030",
    }
    if normalized not in aliases:
        raise ClientError(
            f"{CLI_ENCODING_ENV} only supports utf-8, utf-8-sig, gbk, cp936 or gb18030"
        )
    return aliases[normalized]


def cli_text_encodings() -> list[str]:
    configured = configured_cli_encoding()
    if configured:
        return [configured]
    preferred = locale.getpreferredencoding(False)
    if is_windows_runtime():
        return [preferred, "utf-8-sig", "gb18030"]
    return ["utf-8-sig", preferred, "gb18030"]


def decode_cli_bytes(data: bytes, source: str) -> str:
    if not data:
        return ""
    return decode_candidates(data, source, cli_text_encodings())[0][1]


def read_json(path: Path) -> Any:
    try:
        if path.stat().st_size > MAX_LIST_BYTES:
            raise ClientError(f"the JSON file exceeds the {MAX_LIST_BYTES} byte limit: {path.name}")
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClientError(f"the file does not exist: {path}") from exc
    except (OSError, UnicodeError) as exc:
        raise ClientError(f"cannot read the UTF-8 JSON: {path.name}: {safe_error_text(str(exc))}") from exc
    except json.JSONDecodeError as exc:
        raise ClientError(f"invalid JSON: {path.name}: {exc}") from exc


def read_input(path_value: str, max_bytes: int = 1024 * 1024) -> str:
    try:
        if path_value == "-":
            binary_stdin = getattr(sys.stdin, "buffer", None)
            if binary_stdin is not None:
                raw = binary_stdin.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    raise ClientError(f"the input exceeds the {max_bytes} byte limit")
                text = decode_external_bytes(raw, "standard input")
            else:
                text = sys.stdin.read(max_bytes + 1)
        else:
            path = Path(path_value).expanduser()
            if path.stat().st_size > max_bytes:
                raise ClientError(f"the input file exceeds the {max_bytes} byte limit")
            text = path.read_text(encoding="utf-8")
    except ClientError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ClientError(f"cannot read the input: {safe_error_text(str(exc))}") from exc
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeError as exc:
        raise ClientError("the input contains characters that cannot be converted to UTF-8; use a UTF-8 file or a binary standard input instead") from exc
    if encoded_size > max_bytes:
        raise ClientError(f"the input exceeds the {max_bytes} byte limit")
    return text


def state_path(home: Path) -> Path:
    return home / "state.json"


def load_state(home: Path) -> dict[str, Any]:
    path = state_path(home)
    if not path.exists():
        return {}
    data = read_json(path)
    if not isinstance(data, dict):
        raise ClientError("the local rule state file has an invalid format")
    return data


def write_state(home: Path, data: dict[str, Any]) -> None:
    home.mkdir(parents=True, exist_ok=True)
    path = state_path(home)
    if path.exists():
        history = home / "state-history"
        history.mkdir(parents=True, exist_ok=True)
        backup = history / f"state-{int(time.time())}-{uuid.uuid4().hex[:8]}.json"
        shutil.copy2(path, backup)
    temporary = home / f"state-{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def client_update_state_path(home: Path) -> Path:
    return home / "client-update-state.json"


def load_client_update_state(home: Path) -> dict[str, Any]:
    path = client_update_state_path(home)
    if not path.exists():
        return {}
    try:
        data = read_json(path)
    except ClientError:
        return {}
    return data if isinstance(data, dict) else {}


def write_client_update_state(home: Path, data: dict[str, Any]) -> None:
    home.mkdir(parents=True, exist_ok=True)
    path = client_update_state_path(home)
    temporary = home / f"client-update-state-{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if path.exists():
        history = home / "client-update-history"
        history.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, history / f"client-update-state-{int(time.time())}-{uuid.uuid4().hex[:8]}.json")
    os.replace(temporary, path)


def client_update_installation_state_root() -> Path:
    try:
        install_root = client_file_paths()["SKILL.md"].parent.resolve(strict=True)
    except OSError as exc:
        raise ClientError(f"cannot resolve the local client installation path: {safe_error_text(str(exc))}") from exc
    installation_id = hashlib.sha256(str(install_root).encode("utf-8")).hexdigest()[:32]
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / APP_NAME
    return base / "client-installations" / installation_id


@contextmanager
def client_update_lock(home: Path, *, blocking: bool = True) -> Iterator[None]:
    del home  # the lock is derived from the client installation path, so it must not follow the configurable rule cache directory
    state_root = client_update_installation_state_root()
    state_root.mkdir(parents=True, exist_ok=True)
    lock_path = state_root / "update.lock"
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ClientError("the client update lock is not a regular file")
        handle = os.fdopen(descriptor, "r+b")
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
            msvcrt.locking(handle.fileno(), mode, 1)
        else:
            import fcntl

            mode = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
            fcntl.flock(handle.fileno(), mode)
    except OSError as exc:
        if "handle" in locals():
            handle.close()
        raise ClientError(f"cannot lock the client update: {safe_error_text(str(exc))}") from exc
    try:
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def validate_https_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ClientError("the rule update URL must be a valid HTTPS URL")
    try:
        parsed.port
    except ValueError as exc:
        raise ClientError("the rule update URL contains an invalid port") from exc
    if parsed.username or parsed.password or parsed.fragment:
        raise ClientError("the rule update URL must not contain credentials or a fragment")


def url_origin(url: str) -> tuple[str, str, int]:
    parsed = urllib.parse.urlsplit(url)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port or 443


def validate_oss_root_url(url: str) -> str:
    validate_https_url(url)
    parsed = urllib.parse.urlsplit(url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if not re.fullmatch(
        r"[a-z0-9][a-z0-9.-]*\.oss(?:-[a-z0-9-]+)?\.aliyuncs\.com",
        hostname,
    ):
        raise ClientError("the OSS rule source must use an official Alibaba Cloud OSS bucket endpoint")
    if parsed.port not in {None, 443}:
        raise ClientError("the OSS rule source only allows the default HTTPS port 443")
    if parsed.query or parsed.path not in {"", "/"}:
        raise ClientError("the OSS rule source must be the bucket root HTTPS address without a path or query string")
    return urllib.parse.urlunsplit(("https", hostname, "/", "", ""))


def validate_oss_prefix(value: Optional[str]) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise ClientError("the OSS rule object prefix must be a string")
    if value != value.strip() or len(value) > 512:
        raise ClientError("the OSS rule object prefix contains whitespace or exceeds the length limit")
    if value.startswith("/") or "\\" in value or any(char in value for char in "%?#"):
        raise ClientError("the OSS rule object prefix must be an unencoded relative path")
    normalized = value[:-1] if value.endswith("/") else value
    segments = normalized.split("/")
    if any(
        not segment
        or segment in {".", ".."}
        or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", segment)
        for segment in segments
    ):
        raise ClientError("the OSS rule object prefix contains an illegal path segment")
    return normalized + "/"


def oss_product_prefix(oss_prefix: str) -> str:
    return f"{validate_oss_prefix(oss_prefix)}products/"


def local_rule_key_from_remote(key: str, oss_prefix: str) -> str:
    product_prefix = oss_product_prefix(oss_prefix)
    if not isinstance(key, str) or not key.startswith(product_prefix):
        raise ClientError(f"the OSS rule object path is illegal: {key!r}")
    file_name = key[len(product_prefix):]
    local_key = f"products/{file_name}"
    return validated_rule_key(local_key)


def fetch_bytes(
    url: str,
    limit: int,
    expected_origin: Optional[tuple[str, str, int]] = None,
    request_headers: Optional[dict[str, str]] = None,
) -> tuple[bytes, dict[str, str]]:
    validate_https_url(url)
    headers_to_send = {"User-Agent": f"{APP_NAME}/{VERSION}", **(request_headers or {})}
    request = urllib.request.Request(url, headers=headers_to_send)
    try:
        if expected_origin is None:
            response_context = urllib.request.urlopen(request, timeout=30)
        else:
            opener = urllib.request.build_opener(SameOriginRedirectHandler(expected_origin))
            response_context = opener.open(request, timeout=30)
        with response_context as response:
            final_url = response.geturl()
            validate_https_url(final_url)
            if expected_origin is not None and url_origin(final_url) != expected_origin:
                raise ClientError("the remote request was redirected to another origin, so the update stopped")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > limit:
                raise ClientError("the remote rule response exceeds the size limit")
            payload = response.read(limit + 1)
            if len(payload) > limit:
                raise ClientError("the remote rule response exceeds the size limit")
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            return payload, response_headers
    except ClientError:
        raise
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise ClientError(f"downloading the update content failed: {safe_error_text(str(exc))}") from exc


def decode_utf8(raw: bytes, description: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClientError(f"{description} is not valid UTF-8") from exc


def fetch_json_url(
    url: str,
    limit: int,
    expected_origin: tuple[str, str, int],
) -> Any:
    raw, _ = fetch_bytes(
        url,
        limit,
        expected_origin,
        {"Accept": "application/vnd.github+json"},
    )
    try:
        return json.loads(decode_utf8(raw, "the GitHub API response"))
    except json.JSONDecodeError as exc:
        raise ClientError("the GitHub API did not return valid JSON") from exc


def validate_github_commit(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ClientError("the GitHub commit SHA is invalid")
    return value


def resolve_github_commit() -> str:
    data = fetch_json_url(
        f"{GITHUB_API_ROOT}/commits/{GITHUB_BRANCH}",
        MAX_LIST_BYTES,
        GITHUB_API_ORIGIN,
    )
    if not isinstance(data, dict):
        raise ClientError("the GitHub commit response has an invalid structure")
    return validate_github_commit(data.get("sha"))


def github_raw_file_url(commit: str, relative_path: str) -> str:
    commit = validate_github_commit(commit)
    allowed = relative_path in CLIENT_BUNDLE_PATHS or bool(
        re.fullmatch(r"products/[a-z0-9][a-z0-9._-]*\.json", relative_path)
    )
    if not allowed or relative_path.startswith("/") or ".." in relative_path.split("/"):
        raise ClientError(f"the GitHub file path is illegal: {relative_path!r}")
    quoted = urllib.parse.quote(f"{GITHUB_SKILL_ROOT}/{relative_path}", safe="/-._~")
    return f"{GITHUB_RAW_ROOT}/{commit}/{quoted}"


def github_rules_source_root(commit: str) -> str:
    commit = validate_github_commit(commit)
    quoted = urllib.parse.quote(f"{GITHUB_SKILL_ROOT}/products", safe="/-._~")
    return f"{GITHUB_RAW_ROOT}/{commit}/{quoted}/"


def validate_github_rules_source_root(url: str) -> str:
    validate_https_url(url)
    parsed = urllib.parse.urlsplit(url)
    if url_origin(url) != GITHUB_RAW_ORIGIN or parsed.query or parsed.fragment:
        raise ClientError("the GitHub rule source is not the pinned raw.githubusercontent.com origin")
    match = re.fullmatch(
        rf"/{re.escape(GITHUB_OWNER)}/{re.escape(GITHUB_REPOSITORY)}/([0-9a-f]{{40}})/"
        rf"{re.escape(GITHUB_SKILL_ROOT)}/products/",
        parsed.path,
    )
    if match is None:
        raise ClientError("the GitHub rule source is not pinned to the allowed repository, commit and products directory")
    validate_github_commit(match.group(1))
    return url


def validate_rule_source_root(url: str) -> str:
    try:
        return validate_oss_root_url(url)
    except ClientError as oss_error:
        try:
            return validate_github_rules_source_root(url)
        except ClientError as github_error:
            raise ClientError(
                f"the rule source is neither the allowed OSS root address nor the pinned GitHub directory: {safe_error_text(str(github_error))}"
            ) from oss_error


def github_blob_sha(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def list_github_product_objects(commit: str) -> list[tuple[str, str, int]]:
    commit = validate_github_commit(commit)
    path = urllib.parse.quote(f"{GITHUB_SKILL_ROOT}/products", safe="/-._~")
    data = fetch_json_url(
        f"{GITHUB_API_ROOT}/contents/{path}?ref={commit}",
        MAX_LIST_BYTES,
        GITHUB_API_ORIGIN,
    )
    if not isinstance(data, list):
        raise ClientError("the GitHub products directory response has an invalid structure")
    if not data or len(data) > MAX_FILES:
        raise ClientError("the GitHub rule file count is invalid")
    objects: list[tuple[str, str, int]] = []
    seen: set[str] = set()
    total = 0
    for item in data:
        if not isinstance(item, dict):
            raise ClientError("a GitHub products directory entry has an invalid structure")
        name = item.get("name")
        path_value = item.get("path")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*\.json", name):
            raise ClientError(f"GitHub products contains a disallowed file name: {name!r}")
        expected_path = f"{GITHUB_SKILL_ROOT}/products/{name}"
        if item.get("type") != "file" or path_value != expected_path:
            raise ClientError(f"GitHub products contains a non-direct file or a malicious path: {path_value!r}")
        local_key = validated_rule_key(f"products/{name}")
        folded = local_key.casefold()
        if folded in seen:
            raise ClientError(f"GitHub products contains a duplicate rule: {name}")
        seen.add(folded)
        blob_sha = item.get("sha")
        if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
            raise ClientError(f"the GitHub rule blob SHA is invalid: {name}")
        size = item.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > MAX_FILE_BYTES:
            raise ClientError(f"the GitHub rule file size is invalid: {name}")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ClientError("the total size of the GitHub rule files exceeds the limit")
        objects.append((local_key, blob_sha, size))
    return sorted(objects, key=lambda item: item[0])


def download_github_rules(commit: str) -> list[tuple[str, bytes, dict[str, str]]]:
    commit = validate_github_commit(commit)
    downloaded: list[tuple[str, bytes, dict[str, str]]] = []
    total = 0
    for local_key, expected_sha, expected_size in list_github_product_objects(commit):
        raw, headers = fetch_bytes(
            github_raw_file_url(commit, local_key),
            MAX_FILE_BYTES,
            GITHUB_RAW_ORIGIN,
        )
        if len(raw) != expected_size:
            raise ClientError(f"the GitHub rule file size does not match the contents API: {local_key}")
        if not hmac.compare_digest(github_blob_sha(raw), expected_sha):
            raise ClientError(f"the GitHub rule blob SHA check failed: {local_key}")
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise ClientError("the total size of the GitHub rule files exceeds the limit")
        try:
            data = json.loads(decode_utf8(raw, f"the GitHub rule {local_key}"))
        except json.JSONDecodeError as exc:
            raise ClientError(f"the rule JSON is invalid: {local_key}") from exc
        validate_product_rule(data, local_key)
        downloaded.append((local_key, raw, {**headers, "etag": expected_sha}))
    validate_rule_set([
        json.loads(decode_utf8(raw, f"the GitHub rule {key}"))
        for key, raw, _ in downloaded
    ])
    return downloaded


def parse_semver(value: Any) -> tuple[int, int, int, tuple[tuple[int, Any], ...]]:
    if not isinstance(value, str):
        raise ClientError("the version must be a semver string")
    match = SEMVER_PATTERN.fullmatch(value)
    if match is None:
        raise ClientError(f"the version is not valid semver: {value!r}")
    prerelease: list[tuple[int, Any]] = []
    if match.group(4) is None:
        prerelease.append((2, ""))
    else:
        for identifier in match.group(4).split("."):
            if identifier.isdigit():
                if len(identifier) > 1 and identifier.startswith("0"):
                    raise ClientError(f"the version is not valid semver: {value!r}")
                prerelease.append((0, int(identifier)))
            else:
                prerelease.append((1, identifier))
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), tuple(prerelease)


def compare_semver(left: str, right: str) -> int:
    left_value = parse_semver(left)
    right_value = parse_semver(right)
    return (left_value > right_value) - (left_value < right_value)


def parse_skill_frontmatter(raw: bytes) -> dict[str, str]:
    """Read the top-level frontmatter keys of a remote SKILL.md.

    Indented lines are block-scalar or nested-mapping content (for example a
    `description: |` block or a `metadata:` tree) and are skipped, so only
    top-level keys are collected.
    """
    text = decode_utf8(raw, "the remote SKILL.md")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ClientError("the remote SKILL.md has no frontmatter")
    values: dict[str, str] = {}
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] in (" ", "\t"):
            continue
        if ":" not in line:
            raise ClientError("the remote SKILL.md frontmatter has an invalid format")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in values:
            raise ClientError(f"the remote SKILL.md frontmatter repeats a field: {key}")
        values[key] = value
    if not closed:
        raise ClientError("the remote SKILL.md frontmatter is not closed")
    if values.get("name") != APP_NAME:
        raise ClientError("the remote SKILL.md name does not match this client")
    return values


def script_identity(raw: bytes) -> tuple[str, str]:
    text = decode_utf8(raw, "the remote aliyun_support.py")
    try:
        compile(text, "aliyun_support.py", "exec")
        tree = ast.parse(text, filename="aliyun_support.py")
    except SyntaxError as exc:
        raise ClientError(f"the remote aliyun_support.py cannot be compiled: {safe_error_text(str(exc))}") from exc
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {"APP_NAME", "VERSION"}:
                    constants[target.id] = value.value
    if set(constants) != {"APP_NAME", "VERSION"}:
        raise ClientError("the remote script lacks the APP_NAME/VERSION string constants")
    return constants["APP_NAME"], constants["VERSION"]


def download_github_client_bundle(commit: str) -> dict[str, bytes]:
    commit = validate_github_commit(commit)
    bundle: dict[str, bytes] = {}
    for relative_path in CLIENT_BUNDLE_PATHS:
        raw, _ = fetch_bytes(
            github_raw_file_url(commit, relative_path),
            MAX_CLIENT_FILE_BYTES,
            GITHUB_RAW_ORIGIN,
        )
        bundle[relative_path] = raw
    return bundle


def validate_client_bundle(bundle: dict[str, bytes]) -> str:
    if not isinstance(bundle, dict) or set(bundle) != set(CLIENT_BUNDLE_PATHS):
        raise ClientError("the GitHub client bundle may only contain SKILL.md and scripts/aliyun_support.py")
    if any(not isinstance(raw, bytes) or not raw or len(raw) > MAX_CLIENT_FILE_BYTES for raw in bundle.values()):
        raise ClientError("a GitHub client bundle file is empty or exceeds the size limit")
    frontmatter = parse_skill_frontmatter(bundle["SKILL.md"])
    script_name, script_version = script_identity(bundle["scripts/aliyun_support.py"])
    if script_name != APP_NAME:
        raise ClientError("the remote script APP_NAME does not match this client")
    parse_semver(script_version)
    return script_version


def client_file_paths() -> dict[str, Path]:
    script_path = Path(__file__).absolute()
    return {
        "SKILL.md": script_path.parent.parent / "SKILL.md",
        "scripts/aliyun_support.py": script_path,
    }


def validate_client_targets(targets: dict[str, Path]) -> None:
    if set(targets) != set(CLIENT_BUNDLE_PATHS):
        raise ClientError("the local client file set is invalid")
    skill_root = targets["SKILL.md"].parent
    if skill_root.is_symlink() or targets["scripts/aliyun_support.py"].parent.is_symlink():
        raise ClientError("the local client directory must not be a symbolic link")
    for target in targets.values():
        if not target.is_file() or target.is_symlink():
            raise ClientError(f"the local client file cannot be updated safely: {target}")


def read_local_client_bundle() -> tuple[dict[str, bytes], str]:
    targets = client_file_paths()
    validate_client_targets(targets)
    try:
        bundle = {relative_path: targets[relative_path].read_bytes() for relative_path in CLIENT_BUNDLE_PATHS}
    except OSError as exc:
        raise ClientError(f"cannot read the local client file: {safe_error_text(str(exc))}") from exc
    return bundle, validate_client_bundle(bundle)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def client_update_transaction_path(home: Path) -> Path:
    del home  # the transaction marker is derived from the client installation path, so recovery works across --home values
    return client_update_installation_state_root() / "transaction.json"


def quarantine_path(path: Path, home: Path, label: str) -> None:
    del home  # the archive must live on the same volume as the source files, otherwise Path.rename fails across filesystems
    if not path.exists():
        return
    quarantine = path.parent / ".client-update-history"
    quarantine.mkdir(parents=True, exist_ok=True)
    path.rename(quarantine / f"{label}-{int(time.time())}-{uuid.uuid4().hex[:8]}{path.suffix}")


def write_client_update_transaction(home: Path, data: dict[str, Any]) -> None:
    path = client_update_transaction_path(home)
    if path.exists():
        raise ClientError("an unfinished client update transaction already exists")
    temporary = path.parent / f".client-update-transaction-{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def validate_transaction_hashes(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(CLIENT_BUNDLE_PATHS):
        raise ClientError(f"the {label} file set of the client update transaction is invalid")
    result: dict[str, str] = {}
    for relative_path, digest in value.items():
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ClientError(f"the {label} digest of the client update transaction is invalid: {relative_path}")
        result[relative_path] = digest
    return result


def recover_client_update(home: Path) -> Optional[str]:
    transaction_path = client_update_transaction_path(home)
    if not transaction_path.exists():
        return None
    transaction = read_json(transaction_path)
    required = {"schemaVersion", "transactionId", "createdAt", "backupRoot", "backupSha256", "newSha256"}
    if not isinstance(transaction, dict) or set(transaction) != required:
        raise ClientError("the client update transaction file has an invalid format")
    if transaction.get("schemaVersion") != CLIENT_UPDATE_TRANSACTION_SCHEMA_VERSION:
        raise ClientError("the client update transaction version is not supported")
    transaction_id = transaction.get("transactionId")
    if not isinstance(transaction_id, str) or not re.fullmatch(r"[0-9]+-[0-9a-f]{8}", transaction_id):
        raise ClientError("the client update transaction ID is invalid")
    backup_root = transaction.get("backupRoot")
    if not isinstance(backup_root, str):
        raise ClientError("the client update transaction backup path is invalid")
    backup = Path(backup_root)
    if (
        not backup.is_absolute()
        or backup.name != transaction_id
        or backup.parent.name != "client-update-backups"
        or not backup.is_dir()
        or backup.is_symlink()
        or backup.resolve() != backup.absolute()
    ):
        raise ClientError("the client update transaction has no trusted backup")
    history_home = backup.parent.parent
    backup_hashes = validate_transaction_hashes(transaction.get("backupSha256"), "backup")
    new_hashes = validate_transaction_hashes(transaction.get("newSha256"), "target")
    targets = client_file_paths()
    validate_client_targets(targets)
    current_hashes = {relative_path: sha256_bytes(targets[relative_path].read_bytes()) for relative_path in CLIENT_BUNDLE_PATHS}
    if all(hmac.compare_digest(current_hashes[path], new_hashes[path]) for path in CLIENT_BUNDLE_PATHS):
        quarantine_path(transaction_path, history_home, "completed-transaction")
        return "completed"

    for relative_path in CLIENT_BUNDLE_PATHS:
        source = backup.joinpath(*relative_path.split("/"))
        if not source.is_file() or source.is_symlink():
            raise ClientError(f"the client update transaction backup is invalid: {relative_path}")
        if not hmac.compare_digest(sha256_bytes(source.read_bytes()), backup_hashes[relative_path]):
            raise ClientError(f"the client update transaction backup digest does not match: {relative_path}")
    for relative_path in CLIENT_BUNDLE_PATHS:
        source = backup.joinpath(*relative_path.split("/"))
        target = targets[relative_path]
        restore_temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.restore"
        shutil.copy2(source, restore_temporary)
        os.replace(restore_temporary, target)
    restored_hashes = {relative_path: sha256_bytes(targets[relative_path].read_bytes()) for relative_path in CLIENT_BUNDLE_PATHS}
    if any(not hmac.compare_digest(restored_hashes[path], backup_hashes[path]) for path in CLIENT_BUNDLE_PATHS):
        raise ClientError("the digest check failed after restoring the client update transaction")
    quarantine_path(transaction_path, history_home, "restored-transaction")
    return "restored"


def _install_client_bundle_locked(home: Path, bundle: dict[str, bytes]) -> Path:
    validate_client_bundle(bundle)
    targets = client_file_paths()
    validate_client_targets(targets)
    transaction_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    backup = home / "client-update-backups" / transaction_id
    backup.mkdir(parents=True, exist_ok=False)
    backup_hashes: dict[str, str] = {}
    for relative_path, target in targets.items():
        destination = backup.joinpath(*relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, destination)
        backup_hashes[relative_path] = sha256_bytes(destination.read_bytes())
    transaction = {
        "schemaVersion": CLIENT_UPDATE_TRANSACTION_SCHEMA_VERSION,
        "transactionId": transaction_id,
        "createdAt": utc_now(),
        "backupRoot": str(backup.absolute()),
        "backupSha256": backup_hashes,
        "newSha256": {path: sha256_bytes(bundle[path]) for path in CLIENT_BUNDLE_PATHS},
    }
    write_client_update_transaction(home, transaction)

    temporaries: dict[str, Path] = {}
    try:
        for relative_path, target in targets.items():
            temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
            temporary.write_bytes(bundle[relative_path])
            temporaries[relative_path] = temporary
        for relative_path in CLIENT_BUNDLE_PATHS:
            os.replace(temporaries[relative_path], targets[relative_path])
        installed_hashes = {
            relative_path: sha256_bytes(targets[relative_path].read_bytes())
            for relative_path in CLIENT_BUNDLE_PATHS
        }
        if any(
            not hmac.compare_digest(installed_hashes[path], transaction["newSha256"][path])
            for path in CLIENT_BUNDLE_PATHS
        ):
            raise ClientError("the digest check failed after the client update")
        quarantine_path(client_update_transaction_path(home), home, "completed-transaction")
    except Exception as exc:
        restore_error: Optional[str] = None
        try:
            recovery = recover_client_update(home)
            if recovery == "completed":
                return backup
            if recovery != "restored":
                restore_error = "the transaction was not restored to the backup version"
        except Exception as restore_exc:
            restore_error = safe_error_text(str(restore_exc))
        for temporary in temporaries.values():
            if temporary.exists():
                try:
                    quarantine_path(temporary, home, "failed-temporary")
                except OSError:
                    pass
        detail = f"; restore failed: {restore_error}" if restore_error else ""
        outcome = "restore failed" if restore_error else "restored from backup"
        raise ClientError(f"the client update failed, {outcome}{detail}: {safe_error_text(str(exc))}") from exc
    return backup


def install_client_bundle(home: Path, bundle: dict[str, bytes]) -> Path:
    with client_update_lock(home):
        recover_client_update(home)
        return _install_client_bundle_locked(home, bundle)


def self_update_status(home: Path) -> dict[str, Any]:
    state = load_client_update_state(home)
    checked_at = state.get("checkedAt")
    try:
        _, local_version = read_local_client_bundle()
    except ClientError:
        local_version = state.get("currentVersion", VERSION)
    return {
        "checkedAt": checked_at,
        "currentVersion": local_version,
        "remoteVersion": state.get("remoteVersion"),
        "commit": state.get("commit"),
        "status": state.get("status", "never_checked"),
        "error": state.get("error"),
        "nextCheckDue": (
            datetime.fromtimestamp(parse_checked_at(checked_at) + CHECK_INTERVAL_SECONDS, timezone.utc).isoformat()
            if checked_at else None
        ),
    }


def _self_update_locked(home: Path, force: bool = False) -> dict[str, Any]:
    recovery = recover_client_update(home)
    local_bundle, local_version = read_local_client_bundle()
    previous = load_client_update_state(home)
    if not force and time.time() - parse_checked_at(previous.get("checkedAt")) < CHECK_INTERVAL_SECONDS:
        return {
            **self_update_status(home),
            "updated": False,
            "reason": "checked_recently",
            "recovery": recovery,
        }

    commit: Optional[str] = None
    remote_version: Optional[str] = None
    current_version = local_version
    try:
        commit = resolve_github_commit()
        bundle = download_github_client_bundle(commit)
        remote_version = validate_client_bundle(bundle)
        comparison = compare_semver(remote_version, local_version)
        same_content = all(
            hmac.compare_digest(local_bundle[path], bundle[path])
            for path in CLIENT_BUNDLE_PATHS
        )
        if comparison < 0:
            raise ClientError(f"refusing to downgrade from {local_version} to {remote_version}")
        if comparison == 0 and not same_content:
            raise ClientError(f"the remote {remote_version} has the same version as the local client but different content, so the overwrite was refused")
        if comparison == 0:
            status = "up_to_date"
            updated = False
            backup = None
        else:
            backup = str(_install_client_bundle_locked(home, bundle))
            status = "updated"
            updated = True
            current_version = remote_version
        state = {
            "checkedAt": utc_now(),
            "currentVersion": current_version,
            "remoteVersion": remote_version,
            "commit": commit,
            "status": status,
            "error": None,
        }
        write_client_update_state(home, state)
        return {**state, "updated": updated, "backup": backup, "recovery": recovery}
    except Exception as exc:
        error = safe_error_text(str(exc))
        try:
            _, current_version = read_local_client_bundle()
        except ClientError:
            pass
        state = {
            "checkedAt": utc_now(),
            "currentVersion": current_version,
            "remoteVersion": remote_version,
            "commit": commit,
            "status": "error",
            "error": error,
        }
        write_client_update_state(home, state)
        if isinstance(exc, ClientError):
            raise
        raise ClientError(f"the client self-update failed: {error}") from exc


def self_update(home: Path, force: bool = False) -> dict[str, Any]:
    with client_update_lock(home):
        return _self_update_locked(home, force=force)


def best_effort_self_update(home: Path) -> dict[str, Any]:
    try:
        return self_update(home, force=False)
    except Exception as exc:
        try:
            status = self_update_status(home)
        except Exception:
            status = {
                "checkedAt": None,
                "currentVersion": VERSION,
                "remoteVersion": None,
                "commit": None,
                "status": "error",
                "error": safe_error_text(str(exc)),
                "nextCheckDue": None,
            }
        if status.get("status") != "error":
            status["status"] = "error"
            status["error"] = safe_error_text(str(exc))
        return {**status, "updated": False}


def best_effort_client_recovery(home: Path) -> dict[str, Any]:
    try:
        with client_update_lock(home, blocking=False):
            return {"recovery": recover_client_update(home), "error": None}
    except Exception as exc:
        return {"recovery": None, "error": safe_error_text(str(exc))}


def xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> Optional[str]:
    for child in element:
        if xml_local_name(child.tag) == name:
            return child.text
    return None


def oss_listing_url(
    root_url: str,
    continuation_token: Optional[str],
    oss_prefix: str = "",
) -> str:
    query: list[tuple[str, str]] = [
        ("list-type", "2"),
        ("prefix", oss_product_prefix(oss_prefix)),
        ("delimiter", "/"),
        ("max-keys", str(MAX_FILES)),
        ("encoding-type", "url"),
    ]
    if continuation_token:
        query.append(("continuation-token", continuation_token))
    return f"{root_url}?{urllib.parse.urlencode(query)}"


def parse_oss_listing(
    payload: bytes,
    oss_prefix: str = "",
) -> tuple[list[tuple[str, str, int]], bool, Optional[str]]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ClientError("the OSS object listing is not valid XML") from exc
    root_name = xml_local_name(root.tag)
    if root_name == "Error":
        code = child_text(root, "Code") or "Unknown"
        message = child_text(root, "Message") or "the OSS listing failed"
        raise ClientError(f"the OSS list objects call failed: {safe_error_text(code)}: {safe_error_text(message)}")
    if root_name != "ListBucketResult":
        raise ClientError("the root element of the OSS object listing is invalid")
    encoding_type = child_text(root, "EncodingType")
    if encoding_type != "url":
        raise ClientError("the OSS object listing has an invalid EncodingType")

    product_prefix = oss_product_prefix(oss_prefix)
    objects: list[tuple[str, str, int]] = []
    for element in root.iter():
        if xml_local_name(element.tag) != "Contents":
            continue
        encoded_key = child_text(element, "Key")
        if encoded_key is None:
            raise ClientError("the OSS object listing is missing a Key")
        try:
            key = urllib.parse.unquote(encoded_key, encoding="utf-8", errors="strict")
        except UnicodeError as exc:
            raise ClientError("an OSS object key is not valid UTF-8") from exc
        if key == product_prefix or not key.endswith(".json"):
            continue
        local_rule_key_from_remote(key, oss_prefix)
        etag = child_text(element, "ETag")
        size_text = child_text(element, "Size")
        if not etag or len(etag) > 256 or any(ord(char) < 32 for char in etag):
            raise ClientError(f"an OSS rule object has no valid ETag: {key}")
        try:
            size = int(size_text) if size_text is not None else -1
        except ValueError as exc:
            raise ClientError(f"the OSS rule object size is invalid: {key}") from exc
        if size < 0 or size > MAX_FILE_BYTES:
            raise ClientError(f"the OSS rule object size is invalid: {key}")
        objects.append((key, etag, size))

    truncated_text = child_text(root, "IsTruncated") or "false"
    if truncated_text not in {"true", "false"}:
        raise ClientError("the OSS object listing has an invalid IsTruncated")
    truncated = truncated_text == "true"
    next_token = child_text(root, "NextContinuationToken")
    if truncated and not next_token:
        raise ClientError("the OSS paginated response is missing NextContinuationToken")
    return objects, truncated, next_token


def list_oss_product_objects(
    root_url: str,
    oss_prefix: str = "",
) -> list[tuple[str, str, int]]:
    oss_prefix = validate_oss_prefix(oss_prefix)
    expected_origin = url_origin(root_url)
    continuation_token: Optional[str] = None
    objects: list[tuple[str, str, int]] = []
    seen_keys: set[str] = set()
    seen_tokens: set[str] = set()
    total_size = 0
    for _ in range(MAX_LIST_PAGES):
        payload, _ = fetch_bytes(
            oss_listing_url(root_url, continuation_token, oss_prefix),
            MAX_LIST_BYTES,
            expected_origin,
        )
        page_objects, truncated, next_token = parse_oss_listing(payload, oss_prefix)
        for key, etag, size in page_objects:
            folded = key.casefold()
            if folded in seen_keys:
                raise ClientError(f"the OSS object listing contains a duplicate rule: {key}")
            seen_keys.add(folded)
            objects.append((key, etag, size))
            total_size += size
            if len(objects) > MAX_FILES:
                raise ClientError(f"the OSS rule file count exceeds {MAX_FILES}")
            if total_size > MAX_TOTAL_BYTES:
                raise ClientError("the total size of the OSS rule files exceeds the limit")
        if not truncated:
            break
        if next_token in seen_tokens:
            raise ClientError("the OSS object listing returned a repeated pagination token")
        seen_tokens.add(next_token)
        continuation_token = next_token
    else:
        raise ClientError("the OSS object listing has too many pages")
    if not objects:
        raise ClientError(f"there is no usable JSON rule under {oss_product_prefix(oss_prefix)}")
    return sorted(objects, key=lambda item: item[0])


def list_oss_product_keys(root_url: str, oss_prefix: str = "") -> list[str]:
    return [key for key, _, _ in list_oss_product_objects(root_url, oss_prefix)]


def oss_object_url(root_url: str, key: str, oss_prefix: str = "") -> str:
    local_rule_key_from_remote(key, oss_prefix)
    return urllib.parse.urljoin(root_url, urllib.parse.quote(key, safe="/-._~"))


def download_oss_rules(
    root_url: str,
    oss_prefix: str = "",
) -> list[tuple[str, bytes, dict[str, str]]]:
    oss_prefix = validate_oss_prefix(oss_prefix)
    expected_origin = url_origin(root_url)
    listed_objects = list_oss_product_objects(root_url, oss_prefix)
    downloaded: list[tuple[str, bytes, dict[str, str]]] = []
    total = 0
    for source_key, listed_etag, listed_size in listed_objects:
        local_key = local_rule_key_from_remote(source_key, oss_prefix)
        raw, headers = fetch_bytes(
            oss_object_url(root_url, source_key, oss_prefix),
            MAX_FILE_BYTES,
            expected_origin,
            {"If-Match": listed_etag},
        )
        response_etag = headers.get("etag")
        if response_etag != listed_etag:
            raise ClientError(f"the OSS rule object changed during download or has no ETag: {source_key}")
        if len(raw) != listed_size:
            raise ClientError(f"the OSS rule object size does not match the listing: {source_key}")
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise ClientError("the total size of the OSS rule files exceeds the limit")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ClientError(f"the rule JSON is invalid: {source_key}") from exc
        validate_product_rule(data, local_key)
        downloaded.append((local_key, raw, {**headers, "etag": listed_etag}))
    if list_oss_product_objects(root_url, oss_prefix) != listed_objects:
        raise ClientError("the OSS rule object set changed during download, so the current cache was left unchanged")
    return downloaded


def reject_forbidden_content(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ClientError(f"a rule key must be a string: {path}")
            folded = normalize(key).replace("_", "").replace("-", "")
            if folded in FORBIDDEN_KEY_PARTS:
                raise ClientError(f"the rule contains a forbidden field: {path}.{key}")
            reject_forbidden_content(child, f"{path}.{key}")
    elif isinstance(value, list):
        if len(value) > 100:
            raise ClientError(f"the rule array is too long: {path}")
        for index, child in enumerate(value):
            reject_forbidden_content(child, f"{path}[{index}]")
    elif isinstance(value, str):
        normalized = unicodedata.normalize("NFKC", value)
        if len(normalized) > 500 or any(ord(char) < 32 and char not in "\t\n\r" for char in normalized):
            raise ClientError(f"the rule text length or control characters are illegal: {path}")
        if URL_PATTERN.search(normalized):
            raise ClientError(f"rule content must not contain a URL: {path}")
        if contains_secret(normalized):
            raise ClientError(f"rule content appears to contain credentials: {path}")
        if PROMPT_INJECTION_PATTERN.search(normalized):
            raise ClientError(f"rule content appears to contain execution instructions: {path}")


def require_string(value: Any, name: str, max_length: int = 120) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClientError(f"{name} must be a non-empty string")
    result = value.strip()
    if len(result) > max_length or "\n" in result or "\r" in result:
        raise ClientError(f"{name} exceeds the length limit or contains a newline")
    return result


def require_string_list(value: Any, name: str, max_items: int = 100, max_length: int = 120) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > max_items:
        raise ClientError(f"{name} must be an array of 1-{max_items} strings")
    result = [require_string(item, f"{name}[]", max_length) for item in value]
    if len({normalize(item) for item in result}) != len(result):
        raise ClientError(f"{name} contains duplicate values")
    return result


def reject_sensitive_collection_field(
    field_name: str,
    field_label: str,
    field_description: Optional[str],
    field_example: Optional[str],
    location: str,
) -> None:
    folded_name = re.sub(r"[^a-z0-9]", "", normalize(field_name))
    if folded_name in FORBIDDEN_COLLECTION_FIELD_NAMES or any(
        part in folded_name for part in FORBIDDEN_COLLECTION_FIELD_PARTS
    ):
        raise ClientError(f"rules must not collect credential or secret fields: {location}")

    safe_terms = SAFE_COLLECTION_CREDENTIAL_FIELDS.get(folded_name)
    texts = tuple(
        (text_name, normalize(unicodedata.normalize("NFKC", text)))
        for text_name, text in (
            ("label", field_label),
            ("description", field_description),
            ("example", field_example),
        )
        if text is not None
    )
    label_text = next(text for text_name, text in texts if text_name == "label")
    combined_text = folded_name + "".join(text for _, text in texts)
    field_is_sensitive = any(
        part in folded_name for part in SENSITIVE_COLLECTION_FIELD_PARTS
    )
    label_is_sensitive = bool(SENSITIVE_COLLECTION_LABEL_PATTERN.search(label_text))
    prose_mentions_sensitive_value = bool(
        SENSITIVE_COLLECTION_TEXT_PATTERN.search(combined_text)
    )
    reference_terms = SAFE_CREDENTIAL_REFERENCE_FIELDS.get(folded_name, ())
    safe_reference_context = (
        bool(reference_terms)
        and any(term in label_text for term in reference_terms)
        and not COLLECTION_ACTION_PATTERN.search(combined_text)
        and not UNSAFE_VALUE_MARKER_PATTERN.search(combined_text)
    )
    sensitive_context = (
        field_is_sensitive
        or label_is_sensitive
        or (prose_mentions_sensitive_value and not safe_reference_context)
    )
    if not sensitive_context:
        return
    if safe_terms is None:
        raise ClientError(f"rules must not collect credential or secret fields: {location}")
    if UNSAFE_VALUE_MARKER_PATTERN.search(combined_text):
        raise ClientError(f"rules must not request the raw value of a credential: {location}")
    if not any(term in label_text for term in safe_terms):
        raise ClientError(f"the credential metadata label does not match the field semantics: {location}")
    if field_description is not None:
        description_text = next(text for text_name, text in texts if text_name == "description")
        if not any(term in description_text for term in safe_terms):
            raise ClientError(f"the credential metadata description does not match the field semantics: {location}")
    if field_example is not None:
        raise ClientError(f"credential metadata fields must not provide an example value: {location}")


def validate_product_rule(data: Any, source: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ClientError(f"a product rule must be an object: {source}")
    unknown = set(data) - PRODUCT_KEYS
    if unknown:
        raise ClientError(f"the product rule contains unknown fields: {source}: {sorted(unknown)}")
    product = require_string(data.get("product"), f"{source}.product", 64)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", product):
        raise ClientError(f"{source}.product must be a stable product identifier")
    aliases_value = data.get("aliases", [])
    if not isinstance(aliases_value, list) or len(aliases_value) > 30:
        raise ClientError(f"{source}.aliases must be an array of 0-30 strings")
    aliases = [require_string(item, f"{source}.aliases[]", 64) for item in aliases_value]
    if len({normalize(item) for item in aliases}) != len(aliases):
        raise ClientError(f"{source}.aliases contains duplicate values")
    issue_types = data.get("issueTypes")
    if not isinstance(issue_types, list) or not issue_types or len(issue_types) > 100:
        raise ClientError(f"{source}.issueTypes must be an array of 1-100 items")

    seen_issue_names: set[str] = set()
    for index, issue in enumerate(issue_types):
        location = f"{source}.issueTypes[{index}]"
        if not isinstance(issue, dict):
            raise ClientError(f"{location} must be an object")
        unknown_issue = set(issue) - ISSUE_KEYS
        if unknown_issue:
            raise ClientError(f"{location} contains unknown fields: {sorted(unknown_issue)}")
        issue_name = require_string(issue.get("name"), f"{location}.name", 80)
        folded_name = normalize(issue_name)
        if folded_name in seen_issue_names:
            raise ClientError(f"{source} contains a duplicate issue type: {issue_name}")
        seen_issue_names.add(folded_name)
        require_string_list(issue.get("keywords", []), f"{location}.keywords", 50, 80)
        if "categoryKeywords" in issue:
            require_string_list(issue["categoryKeywords"], f"{location}.categoryKeywords", 30, 80)
        if "categoryHints" in issue:
            require_string_list(issue["categoryHints"], f"{location}.categoryHints", 30, 80)
        collect = issue.get("collect")
        if not isinstance(collect, list) or not collect or len(collect) > 50:
            raise ClientError(f"{location}.collect must be an array of 1-50 items")
        seen_fields: set[str] = set()
        for field_index, field in enumerate(collect):
            field_location = f"{location}.collect[{field_index}]"
            if not isinstance(field, dict):
                raise ClientError(f"{field_location} must be an object")
            unknown_field = set(field) - FIELD_KEYS
            if unknown_field:
                raise ClientError(f"{field_location} contains unknown fields: {sorted(unknown_field)}")
            field_name = require_string(field.get("field"), f"{field_location}.field", 64)
            field_label = require_string(field.get("label"), f"{field_location}.label", 80)
            field_description = (
                require_string(field["description"], f"{field_location}.description", 240)
                if "description" in field
                else None
            )
            field_example = (
                require_string(field["example"], f"{field_location}.example", 240)
                if "example" in field
                else None
            )
            reject_sensitive_collection_field(
                field_name,
                field_label,
                field_description,
                field_example,
                field_location,
            )
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", field_name):
                raise ClientError(f"the collection field name is illegal: {field_name}")
            if field_name in seen_fields:
                raise ClientError(f"{location} contains a duplicate collection field: {field_name}")
            seen_fields.add(field_name)
            if "required" in field and not isinstance(field["required"], bool):
                raise ClientError(f"{field_location}.required must be a boolean")
            if field.get("type", "string") not in {"string", "integer", "number", "boolean", "array"}:
                raise ClientError(f"{field_location}.type is not supported")
            if "enum" in field and (not isinstance(field["enum"], list) or not field["enum"]):
                raise ClientError(f"{field_location}.enum must be a non-empty array")
            if "maxLength" in field and (
                not isinstance(field["maxLength"], int)
                or isinstance(field["maxLength"], bool)
                or field["maxLength"] < 1
            ):
                raise ClientError(f"{field_location}.maxLength must be a positive integer")

    reject_forbidden_content(data, source)
    return data


def validate_rule_set(rules: list[dict[str, Any]]) -> None:
    owners: dict[str, tuple[int, str]] = {}
    for index, rule in enumerate(rules):
        product = rule["product"]
        for name in [product, *rule["aliases"]]:
            folded = normalize(name)
            owner = owners.get(folded)
            if owner is not None and owner[0] != index:
                raise ClientError(f"the rule snapshot contains a conflicting product identifier: {name!r} ({owner[1]} and {product})")
            owners[folded] = (index, product)


def validated_rule_key(name: str) -> str:
    if not isinstance(name, str) or not OSS_PRODUCT_KEY_PATTERN.fullmatch(name):
        raise ClientError(f"the rule object path is illegal: {name!r}")
    return name


def snapshot_digest(files: Iterable[tuple[str, bytes, dict[str, str]]]) -> str:
    digest = hashlib.sha256()
    for key, raw, _ in sorted(files, key=lambda item: item[0]):
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def install_rule_files(
    home: Path,
    files: list[tuple[str, bytes, dict[str, str]]],
    source_root: str,
) -> str:
    if not files or len(files) > MAX_FILES:
        raise ClientError("the rule file count is invalid")
    source_root = validate_rule_source_root(source_root)
    seen: set[str] = set()
    total = 0
    for key, raw, headers in files:
        validated_rule_key(key)
        folded = key.casefold()
        if folded in seen:
            raise ClientError(f"a rule file repeats an object: {key}")
        seen.add(folded)
        if not isinstance(raw, bytes) or len(raw) > MAX_FILE_BYTES:
            raise ClientError(f"a rule file exceeds the size limit: {key}")
        if not isinstance(headers, dict):
            raise ClientError(f"a rule file response header is invalid: {key}")
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise ClientError("the total size of the rule files exceeds the limit")
    snapshot_id = snapshot_digest(files)
    packages = home / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    target = packages / snapshot_id
    if target.exists():
        try:
            load_rules_from_dir(target, expected_snapshot_id=snapshot_id)
            return snapshot_id
        except ClientError:
            quarantine = packages / f"invalid-{snapshot_id[:12]}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
            target.rename(quarantine)

    staging = packages / f"staging-{snapshot_id[:12]}-{uuid.uuid4().hex[:8]}"
    staging.mkdir(parents=True, exist_ok=False)
    manifest_files: dict[str, dict[str, Any]] = {}
    try:
        for key, raw, headers in sorted(files, key=lambda item: item[0]):
            relative = validated_rule_key(key)
            destination = staging.joinpath(*relative.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            manifest_files[relative] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
                "etag": headers.get("etag"),
            }
        manifest = {
            "schemaVersion": CACHE_SCHEMA_VERSION,
            "contentDigest": snapshot_id,
            "sourceRoot": source_root,
            "fetchedAt": utc_now(),
            "files": manifest_files,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        load_rules_from_dir(staging, expected_snapshot_id=snapshot_id)
        staging.rename(target)
    except Exception:
        quarantine = packages / f"invalid-staging-{snapshot_id[:12]}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        if staging.exists():
            staging.rename(quarantine)
        raise
    return snapshot_id


def parse_checked_at(value: Any) -> float:
    if not isinstance(value, str):
        return 0.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0.0


def valid_cached_package_names(home: Path, state: dict[str, Any]) -> list[str]:
    valid: list[str] = []
    for key in ("active", "previous"):
        name = state.get(key)
        if name in valid:
            continue
        package = package_path(home, name)
        if package is None:
            continue
        try:
            load_rules_from_dir(package, expected_snapshot_id=name)
        except ClientError:
            continue
        valid.append(name)
    return valid


def oss_configuration_source(args: Optional[argparse.Namespace] = None) -> str:
    argument_root = getattr(args, "oss_url", None) if args is not None else None
    argument_prefix = getattr(args, "oss_prefix", None) if args is not None else None
    if argument_root is not None or argument_prefix is not None:
        return "command_line"
    if (
        "ALIBABACLOUD_SUPPORT_RULES_OSS_URL" in os.environ
        or "ALIBABACLOUD_SUPPORT_RULES_OSS_PREFIX" in os.environ
    ):
        return "environment"
    if (
        "ALIYUN_SUPPORT_RULES_OSS_URL" in os.environ
        or "ALIYUN_SUPPORT_RULES_OSS_PREFIX" in os.environ
    ):
        return "legacy_environment"
    return "built_in_default"


def configured_oss_source(args: Optional[argparse.Namespace] = None) -> tuple[Optional[str], str, bool, Optional[str]]:
    argument_root = getattr(args, "oss_url", None) if args is not None else None
    argument_prefix = getattr(args, "oss_prefix", None) if args is not None else None
    legacy_used = False
    if argument_root is not None:
        configured_root = argument_root
    else:
        configured_root, root_legacy = environment_value(
            "ALIBABACLOUD_SUPPORT_RULES_OSS_URL",
            "ALIYUN_SUPPORT_RULES_OSS_URL",
            DEFAULT_RULES_OSS_URL,
        )
        legacy_used = legacy_used or root_legacy
    if argument_prefix is not None:
        configured_prefix = argument_prefix
    else:
        configured_prefix, prefix_legacy = environment_value(
            "ALIBABACLOUD_SUPPORT_RULES_OSS_PREFIX",
            "ALIYUN_SUPPORT_RULES_OSS_PREFIX",
            DEFAULT_RULES_OSS_PREFIX,
        )
        legacy_used = legacy_used or prefix_legacy
    try:
        root_url = validate_oss_root_url(configured_root) if configured_root else None
        oss_prefix = validate_oss_prefix(configured_prefix)
    except ClientError as exc:
        return None, "", legacy_used, safe_error_text(str(exc))
    return root_url, oss_prefix, legacy_used, None


def rules_update_result(
    state: dict[str, Any],
    self_update_result: dict[str, Any],
    *,
    updated: bool,
    source_type: str,
    source_commit: Optional[str],
    oss_error: Optional[str],
    github_error: Optional[str],
    degraded: bool,
    effective_source: str,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    result = {
        "updated": updated,
        "active": state.get("active"),
        "previous": state.get("previous"),
        "fileCount": state.get("fileCount"),
        "sourceRoot": state.get("sourceRoot") or state.get("source"),
        "sourcePrefix": state.get("sourcePrefix", ""),
        "sourceType": source_type,
        "sourceCommit": source_commit,
        "ossError": oss_error,
        "githubError": github_error,
        "degraded": degraded,
        "effectiveSource": effective_source,
        "selfUpdate": self_update_result,
    }
    if reason is not None:
        result["reason"] = reason
    return result


def update_rules(args: argparse.Namespace) -> dict[str, Any]:
    home: Path = args.home
    self_update_result = best_effort_self_update(home)
    try:
        state = load_state(home)
    except ClientError:
        state = {}

    root_url, oss_prefix, legacy_used, configuration_error = configured_oss_source(args)
    valid_before_update = valid_cached_package_names(home, state)
    recently_checked = time.time() - parse_checked_at(state.get("checkedAt")) < CHECK_INTERVAL_SECONDS
    if state.get("sourceType") == "github":
        source_unchanged = True
    elif configuration_error is None and root_url is not None:
        source_unchanged = (
            state.get("sourceType") == "oss"
            and (state.get("sourceRoot") or state.get("source")) == root_url
            and state.get("sourcePrefix", "") == oss_prefix
        )
    else:
        source_unchanged = False
    active_valid = bool(valid_before_update and valid_before_update[0] == state.get("active"))
    if not getattr(args, "force", False) and recently_checked and source_unchanged and active_valid:
        return rules_update_result(
            state,
            self_update_result,
            updated=False,
            source_type=state.get("sourceType", "default"),
            source_commit=state.get("sourceCommit"),
            oss_error=state.get("ossError"),
            github_error=state.get("githubError"),
            degraded=bool(state.get("degraded", False)),
            effective_source=state.get("effectiveSource") or state.get("sourceRoot") or "default",
            reason="checked_recently",
        )

    commit: Optional[str] = None
    github_error: Optional[str] = None
    try:
        commit = resolve_github_commit()
        files = download_github_rules(commit)
        source_root = github_rules_source_root(commit)
        snapshot_id = install_rule_files(home, files, source_root)
        previous = next((name for name in valid_before_update if name != snapshot_id), None)
        new_state = {
            "schemaVersion": CACHE_SCHEMA_VERSION,
            "active": snapshot_id,
            "previous": previous,
            "checkedAt": utc_now(),
            "sourceRoot": source_root,
            "sourcePrefix": "",
            "sourceType": "github",
            "sourceCommit": commit,
            "ossError": None,
            "githubError": None,
            "degraded": False,
            "effectiveSource": source_root,
            "fileCount": len(files),
            "legacyConfiguration": legacy_used,
        }
        write_state(home, new_state)
        return rules_update_result(
            new_state,
            self_update_result,
            updated=state.get("active") != snapshot_id,
            source_type="github",
            source_commit=commit,
            oss_error=None,
            github_error=None,
            degraded=False,
            effective_source=source_root,
        )
    except Exception as exc:
        github_error = safe_error_text(str(exc))

    oss_error = configuration_error
    if root_url is None and oss_error is None:
        oss_error = "not_configured"
    if root_url is not None and configuration_error is None:
        try:
            files = download_oss_rules(root_url, oss_prefix)
            snapshot_id = install_rule_files(home, files, root_url)
            previous = next((name for name in valid_before_update if name != snapshot_id), None)
            new_state = {
                "schemaVersion": CACHE_SCHEMA_VERSION,
                "active": snapshot_id,
                "previous": previous,
                "checkedAt": utc_now(),
                "sourceRoot": root_url,
                "sourcePrefix": oss_prefix,
                "sourceType": "oss",
                "sourceCommit": None,
                "ossError": None,
                "githubError": github_error,
                "degraded": False,
                "effectiveSource": root_url,
                "fileCount": len(files),
                "legacyConfiguration": legacy_used,
            }
            write_state(home, new_state)
            return rules_update_result(
                new_state,
                self_update_result,
                updated=state.get("active") != snapshot_id,
                source_type="oss",
                source_commit=None,
                oss_error=None,
                github_error=github_error,
                degraded=False,
                effective_source=root_url,
            )
        except Exception as exc:
            oss_error = safe_error_text(str(exc))

    fallback_state = {
        "schemaVersion": CACHE_SCHEMA_VERSION,
        "active": None,
        "previous": None,
        "checkedAt": utc_now(),
        "sourceRoot": None,
        "sourcePrefix": "",
        "sourceType": "default",
        "sourceCommit": commit,
        "ossError": oss_error,
        "githubError": github_error,
        "degraded": True,
        "effectiveSource": "default",
        "fileCount": 0,
        "legacyConfiguration": legacy_used,
    }
    write_state(home, fallback_state)
    return rules_update_result(
        fallback_state,
        self_update_result,
        updated=False,
        source_type="default",
        source_commit=commit,
        oss_error=oss_error,
        github_error=github_error,
        degraded=True,
        effective_source="default",
    )


def package_path(home: Path, name: Any) -> Optional[Path]:
    if not isinstance(name, str) or not re.fullmatch(r"[0-9a-f]{64}", name):
        return None
    package = home / "packages" / name
    try:
        return package if package.is_dir() else None
    except OSError:
        return None


def cached_product_paths(products: Path, package: Path) -> dict[str, Path]:
    if products.is_symlink() or not products.is_dir():
        raise ClientError("the rule cache has no valid products directory")
    paths: dict[str, Path] = {}
    total_size = 0
    for path in products.iterdir():
        relative = path.relative_to(package).as_posix()
        if path.is_symlink() or not path.is_file():
            raise ClientError(f"the rule cache contains a disallowed file type: {relative}")
        validated_rule_key(relative)
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ClientError(f"a rule cache file exceeds the size limit: {relative}")
        total_size += size
        if total_size > MAX_TOTAL_BYTES:
            raise ClientError("the total size of the rule cache files exceeds the limit")
        paths[relative] = path
    if not paths or len(paths) > MAX_FILES:
        raise ClientError("the rule cache file count is invalid")
    return paths


def _load_rules_from_dir(package: Path, expected_snapshot_id: Optional[str] = None) -> list[dict[str, Any]]:
    products = package / "products"
    paths = cached_product_paths(products, package)
    manifest_path = package / "manifest.json"

    if not manifest_path.is_file():
        raise ClientError("the rule cache is missing its manifest")
    manifest = read_json(manifest_path)
    required = {"schemaVersion", "contentDigest", "sourceRoot", "fetchedAt", "files"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ClientError("the rule cache manifest has an invalid format")
    if manifest.get("schemaVersion") != CACHE_SCHEMA_VERSION:
        raise ClientError("the rule cache manifest version is not supported")
    content_digest = manifest.get("contentDigest")
    if not isinstance(content_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", content_digest):
        raise ClientError("the rule cache content digest is invalid")
    if expected_snapshot_id is not None and not hmac.compare_digest(content_digest, expected_snapshot_id):
        raise ClientError("the rule cache does not match the expected snapshot")
    source_root = manifest.get("sourceRoot")
    if not isinstance(source_root, str):
        raise ClientError("the rule cache source is invalid")
    validate_rule_source_root(source_root)
    file_records = manifest.get("files")

    if not isinstance(file_records, dict) or not file_records or len(file_records) > MAX_FILES:
        raise ClientError("the rule cache file list is invalid")
    if set(paths) != set(file_records):
        raise ClientError("the rule cache file set does not match the manifest")

    rules: list[dict[str, Any]] = []
    verified_files: list[tuple[str, bytes, dict[str, str]]] = []
    for relative in sorted(file_records):
        validated_rule_key(relative)
        record = file_records.get(relative)
        if not isinstance(record, dict) or set(record) != {"sha256", "size", "etag"}:
            raise ClientError(f"a rule cache file record is invalid: {relative}")
        expected_hash = record.get("sha256")
        expected_size = record.get("size")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ClientError(f"a rule cache file digest is invalid: {relative}")
        if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 0:
            raise ClientError(f"a rule cache file size is invalid: {relative}")
        raw = paths[relative].read_bytes()
        if len(raw) != expected_size or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_hash):
            raise ClientError(f"the rule cache file integrity check failed: {relative}")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ClientError(f"the rule cache JSON is invalid: {relative}") from exc
        rules.append(validate_product_rule(data, relative))
        verified_files.append((relative, raw, {}))
    actual_digest = snapshot_digest(verified_files)
    if not hmac.compare_digest(actual_digest, content_digest):
        raise ClientError("the rule cache content digest check failed")
    validate_rule_set(rules)
    return rules


def load_rules_from_dir(package: Path, expected_snapshot_id: Optional[str] = None) -> list[dict[str, Any]]:
    try:
        return _load_rules_from_dir(package, expected_snapshot_id)
    except ClientError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ClientError(f"cannot read the rule cache: {safe_error_text(str(exc))}") from exc


def load_rules(home: Path) -> list[dict[str, Any]]:
    try:
        state = load_state(home)
    except ClientError:
        return []
    for key in ("active", "previous"):
        name = state.get(key)
        package = package_path(home, name)
        if package is None:
            continue
        try:
            return load_rules_from_dir(package, expected_snapshot_id=name)
        except ClientError:
            continue
    return []


def issue_candidates(rules: Iterable[dict[str, Any]], text: str, product_filter: Optional[str]) -> list[dict[str, Any]]:
    folded_text = normalize(text)
    folded_filter = normalize(product_filter) if product_filter else None
    candidates: list[dict[str, Any]] = []
    for rule in rules:
        product_names = [rule["product"], *rule["aliases"]]
        if folded_filter and folded_filter not in {normalize(item) for item in product_names}:
            continue
        product_hits = sum(2 for item in product_names if normalize(item) and normalize(item) in folded_text)
        for issue in rule["issueTypes"]:
            keyword_hits = sum(3 for item in issue["keywords"] if normalize(item) in folded_text)
            category_hits = sum(1 for item in issue.get("categoryKeywords", []) if normalize(item) in folded_text)
            score = product_hits + keyword_hits + category_hits
            if score > 0 or folded_filter:
                candidates.append(
                    {
                        "product": rule["product"],
                        "issueType": issue["name"],
                        "score": score,
                        "productScore": product_hits,
                        "issueScore": keyword_hits + category_hits,
                        "ruleMatched": True,
                        "categoryHints": issue.get("categoryHints", issue.get("categoryKeywords", [])),
                        "collect": issue["collect"],
                    }
                )
    candidates.sort(key=lambda item: (-item["score"], item["product"], item["issueType"]))
    return candidates


def mask_email(match: re.Match[str]) -> str:
    local, domain = match.groups()
    shown = local[:2] if len(local) > 1 else local[:1]
    return f"{shown}****@{domain}"


def mask_access_key_id(match: re.Match[str]) -> str:
    value = match.group(1)
    return f"{value[:4]}****{value[-4:]}"


def contains_secret(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text)
    candidates = [normalized]
    for _ in range(2):
        decoded = urllib.parse.unquote(candidates[-1])
        if decoded == candidates[-1]:
            break
        candidates.append(decoded)
    return any(pattern.search(candidate) for candidate in candidates for pattern in SECRET_PATTERNS)


def redact_text(text: str) -> str:
    if contains_secret(text):
        raise ClientError("a password, token, AccessKey secret, cookie, Authorization header or private key was detected, so processing was blocked")
    text = EMAIL_PATTERN.sub(mask_email, text)
    text = PHONE_PATTERN.sub(lambda match: f"{match.group(1)}****{match.group(3)}", text)
    text = ACCESS_KEY_ID_PATTERN.sub(mask_access_key_id, text)
    text = ID_CARD_PATTERN.sub(lambda match: f"{match.group(1)}********{match.group(3)}", text)
    text = LABELED_UID_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{mask_identifier(match.group(3))}",
        text,
    )
    return text


def mask_identifier(value: str) -> str:
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}****{value[-3:]}"


def validate_field_value(field: dict[str, Any], value: Any) -> Any:
    expected = field.get("type", "string")
    valid = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
    }[expected]
    if not valid:
        raise ClientError(f"the type of field \"{field['label']}\" must be {expected}")
    if isinstance(value, str) and field.get("maxLength") and len(value) > field["maxLength"]:
        raise ClientError(f"field \"{field['label']}\" exceeds the length limit")
    if "enum" in field and value not in field["enum"]:
        raise ClientError(f"field \"{field['label']}\" is not within the allowed values")
    return value


def resolve_issue(
    rules: list[dict[str, Any]],
    product: str,
    issue_type: str,
) -> tuple[dict[str, Any], dict[str, Any], bool, Optional[str]]:
    product_found = False
    for rule in rules:
        names = [rule["product"], *rule["aliases"]]
        if normalize(product) not in {normalize(item) for item in names}:
            continue
        product_found = True
        for issue in rule["issueTypes"]:
            if normalize(issue_type) == normalize(issue["name"]):
                return rule, issue, True, None
    reason = "issue_type_not_found" if product_found else "product_not_found"
    fallback_rule = {"product": product, "aliases": [], "issueTypes": [DEFAULT_ISSUE]}
    return fallback_rule, DEFAULT_ISSUE, False, reason


def default_match_template(product: Optional[str], reason: str) -> dict[str, Any]:
    return {
        "product": product,
        "issueType": DEFAULT_ISSUE["name"],
        "score": 0,
        "issueScore": 0,
        "ruleMatched": False,
        "fallbackReason": reason,
        "categoryHints": DEFAULT_ISSUE["categoryHints"],
        "collect": DEFAULT_ISSUE["collect"],
    }


def format_value(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def is_user_identity_field(field: dict[str, Any]) -> bool:
    folded_name = re.sub(r"[^a-z0-9]", "", normalize(str(field.get("field", ""))))
    exact_names = {
        "uid",
        "userid",
        "useruid",
        "aliyunuid",
        "accountuid",
        "customeruid",
        "tenantuid",
        "accountid",
        "aliyunaccountid",
        "ownerid",
        "creatorid",
        "customerid",
        "mainaccountid",
        "subaccountid",
        "ramuserid",
        "ramuseruid",
        "loginid",
        "memberid",
        "accountname",
        "idcard",
        "idcardnumber",
    }
    identity_suffixes = ("userid", "useruid", "accountid", "ownerid", "creatorid", "customeruid")
    if folded_name in exact_names or any(folded_name.endswith(suffix) for suffix in identity_suffixes):
        return True
    label = normalize(str(field.get("label", "")))
    return bool(re.search(r"(?:用户|客户|云账号|主账号|子账号|账户|账号).{0,8}(?:uid|id|标识)|身份证", label, re.I))


def suggested_collection_field(field: dict[str, Any]) -> dict[str, str]:
    result = {"field": field["field"], "label": field["label"]}
    for key in ("description", "example"):
        value = field.get(key)
        if isinstance(value, str) and value:
            result[key] = value
    return result


def create_draft(home: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ClientError("the draft input must be a JSON object")
    product = redact_text(require_string(payload.get("product"), "product"))
    issue_type = redact_text(require_string(payload.get("issueType"), "issueType"))
    summary = require_string(payload.get("summary"), "summary")
    requested_impact = payload.get("impact")
    steps = payload.get("stepsTried", [])
    values = payload.get("values", {})
    if not isinstance(values, dict):
        raise ClientError("values must be an object")
    if not isinstance(steps, list) or not all(isinstance(item, str) for item in steps):
        raise ClientError("stepsTried must be an array of strings")

    _, issue, rule_matched, fallback_reason = resolve_issue(load_rules(home), product, issue_type)
    resolved_issue_type = issue["name"]
    impact = requested_impact if requested_impact not in (None, "") else "Not specified"
    if not rule_matched and values.get("impactScope") not in (None, "", []):
        impact = values["impactScope"]
    suggested_missing: list[dict[str, str]] = []
    collected: list[tuple[str, str]] = []
    redacted_fields: list[str] = []

    for field in issue["collect"]:
        name = field["field"]
        if name not in values or values[name] in (None, "", []):
            if not is_user_identity_field(field):
                suggested_missing.append(suggested_collection_field(field))
            continue
        value = validate_field_value(field, values[name])
        rendered = format_value(value)
        if contains_secret(rendered):
            raise ClientError(f"field \"{field['label']}\" contains sensitive information that must not be submitted")
        masked = redact_text(rendered)
        if is_user_identity_field(field):
            masked = mask_identifier(masked)
        if masked != rendered:
            redacted_fields.append(name)
        if not rule_matched and name == "impactScope":
            continue
        collected.append((field["label"], masked))

    safe_summary = redact_text(summary)
    safe_impact = redact_text(format_value(impact))
    safe_steps = [redact_text(item) for item in steps]
    lines = [
        "[Issue summary]",
        safe_summary,
        "",
        "[Product and issue type]",
        f"- Product: {product}",
        f"- Issue type: {resolved_issue_type}",
        "",
        "[Impact scope]",
        safe_impact,
        "",
        "[Collected information]",
    ]
    if collected:
        lines.extend(f"- {label}: {value}" for label, value in collected)
    else:
        lines.append("- Not provided")
    lines.extend(["", "[Steps already tried]"])
    lines.extend(f"- {item}" for item in safe_steps) if safe_steps else lines.append("- Not specified")
    draft = "\n".join(lines).strip()
    if len(draft) > 20000:
        raise ClientError("the ticket draft exceeds 20000 characters; shorten it and try again")
    return {
        "ready": True,
        "product": product,
        "issueType": resolved_issue_type,
        "requestedIssueType": issue_type,
        "ruleMatched": rule_matched,
        "fallbackReason": fallback_reason,
        "categoryHints": issue.get("categoryHints", issue.get("categoryKeywords", [])),
        "suggestedMissing": suggested_missing,
        "redactedFields": sorted(set(redacted_fields)),
        "draftSha256": hashlib.sha256(draft.encode("utf-8")).hexdigest(),
        "draft": draft,
    }


def is_windows_runtime() -> bool:
    return os.name == "nt" or sys.platform.startswith(("win32", "cygwin", "msys"))


def agent_data_directory_names() -> list[str]:
    supported = [".qwenworkcn", ".qoderwork"]
    script_path = str(Path(__file__)).lower()
    preferred = [name for name in supported if name in script_path]
    return preferred + [name for name in supported if name not in preferred]


def windows_cli_candidates() -> list[Path]:
    return [Path.home() / name / "aliyun-cli" / "aliyun.exe" for name in agent_data_directory_names()]


def resolve_cli_executable() -> tuple[Optional[str], str]:
    configured = os.environ.get(CLI_PATH_ENV)
    if configured:
        candidate = Path(os.path.expandvars(configured)).expanduser()
        if candidate.is_file():
            return str(candidate), "environment"
    executable = shutil.which("aliyun")
    if executable:
        return executable, "path"
    if is_windows_runtime():
        for candidate in windows_cli_candidates():
            if candidate.is_file():
                return str(candidate), "agent_data_directory"
    return None, "missing"


def cli_executable() -> str:
    executable, _ = resolve_cli_executable()
    if not executable:
        raise ClientError(
            f"the Alibaba Cloud CLI was not found; install it, refresh PATH, or point {CLI_PATH_ENV} at the aliyun executable"
        )
    return executable


def session_id() -> str:
    """Return the 32-character hex session id, creating and exporting one if needed."""
    existing = (os.environ.get(SESSION_ID_ENV) or "").strip().lower()
    if HEX_32_PATTERN.match(existing):
        return existing
    generated = uuid.uuid4().hex
    os.environ[SESSION_ID_ENV] = generated
    return generated


class SkillVersionError(ClientError):
    """references/manifest.json is missing, unreadable or carries no valid version.

    The version is never guessed, so a run that cannot read it stops here, before
    the first cloud call, instead of sending a User-Agent without a version.
    """


_SKILL_VERSION: Optional[str] = None


def skill_version(manifest_path: Optional[Path] = None) -> str:
    """Return the User-Agent skill version, read from references/manifest.json.

    The value is resolved on the first User-Agent build, that is before the first
    cloud call of the run, and then cached for the rest of the run the same way as
    the session id. A missing or unreadable manifest, or a version that is not a
    semantic version, raises SkillVersionError rather than substituting a guess.
    """
    global _SKILL_VERSION
    if _SKILL_VERSION is not None and manifest_path is None:
        return _SKILL_VERSION
    path = manifest_path or MANIFEST_PATH
    try:
        declared = read_json(path).get("version")
    except (ClientError, OSError, ValueError, AttributeError) as exc:
        raise SkillVersionError(f"the skill version cannot be read from {path}: {safe_error_text(str(exc))}") from exc
    rendered = str(declared or "").strip()
    if not SKILL_VERSION_PATTERN.match(rendered):
        raise SkillVersionError(
            f"{path} declares no valid semantic version (got {declared!r}); the User-Agent version is never guessed"
        )
    if manifest_path is None:
        _SKILL_VERSION = rendered
    return rendered


def _selfcheck_skill_version() -> None:
    """Boundary assertions for skill_version(): normal, boundary, illegal.

    They open no network connection and call no cloud API, and they pin the
    contract that the version comes from the manifest file verbatim and that an
    unusable manifest stops the run instead of producing a guessed value.
    """
    global _SKILL_VERSION
    if not SKILL_VERSION_PATTERN.match("1.2.3") or not SKILL_VERSION_PATTERN.match("1.2.3-rc.1"):
        raise AssertionError("the version pattern must accept release and pre-release versions")
    if (SKILL_VERSION_PATTERN.match("1.0") or SKILL_VERSION_PATTERN.match("v1.2.3")
            or SKILL_VERSION_PATTERN.match("")):
        raise AssertionError("the version pattern must reject malformed versions")
    previous = _SKILL_VERSION
    try:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for name, payload in (("missing", None), ("bad", '{"version": "not-a-version"}'), ("ok", '{"version": "0.0.1"}')):
                path = root / f"{name}.json"
                if payload is not None:
                    path.write_text(payload, encoding="utf-8")
                    if name == "ok":
                        if skill_version(path) != "0.0.1":
                            raise AssertionError("the declared version must be returned verbatim")
                        continue
                try:
                    skill_version(path)
                    raise AssertionError(f"an unusable manifest must raise: {name}")
                except SkillVersionError:
                    pass
        if _SKILL_VERSION is not None:
            raise AssertionError("an explicit manifest path must not populate the run cache")
    finally:
        _SKILL_VERSION = previous


def user_agent() -> str:
    return f"{USER_AGENT_PREFIX}/{session_id()} skill-version/{skill_version()}"


def cli_environment() -> dict[str, str]:
    env = os.environ.copy()
    rendered = user_agent()
    for name in USER_AGENT_ENVS:
        env[name] = rendered
    return env


def flag_name(api_param: str) -> str:
    override = WORKORDER_PLUGIN_PARAM_OVERRIDES.get(api_param)
    if override:
        return override
    return re.sub(r"(?<!^)(?=[A-Z])", "-", api_param).lower()


def parameter_args(params: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (dict, list)):
            rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            rendered = str(value)
        result.extend([f"--{flag_name(key)}", rendered])
    return result


def safe_error_text(text: str) -> str:
    try:
        return redact_text(text)[:2000]
    except ClientError:
        return "the command output contained sensitive information and was hidden"


def decode_process_stream(value: Any, source: str) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return decode_cli_bytes(value, source)
    raise ClientError(f"{source} has an invalid type: {type(value).__name__}")


def run_cli_process(command: list[str], timeout: int) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=False,
        timeout=timeout,
        check=False,
        stdin=subprocess.DEVNULL,
        env=cli_environment(),
    )
    stdout = decode_process_stream(completed.stdout, "the Alibaba Cloud CLI standard output")
    stderr = decode_process_stream(completed.stderr, "the Alibaba Cloud CLI standard error")
    return completed.returncode, stdout, stderr


def workorder_call(action: str, params: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    plugin_command = WORKORDER_PLUGIN_COMMANDS.get(action)
    if not plugin_command:
        raise ClientError(f"unsupported Workorder operation: {action}")
    serialized_params = json.dumps(params, ensure_ascii=False, separators=(",", ":"))
    if contains_secret(serialized_params):
        raise ClientError(f"the request parameters of {action} appear to contain credentials, so the call was blocked")
    region = os.environ.get("ALIBABA_CLOUD_REGION_ID", DEFAULT_REGION)
    command = [
        cli_executable(),
        "workorder",
        plugin_command,
        "--region",
        region,
        "--retry-count",
        "0",
        "--connect-timeout",
        "10",
        "--read-timeout",
        str(timeout),
        "--user-agent",
        user_agent(),
        *parameter_args(params),
    ]
    is_non_idempotent = action in NON_IDEMPOTENT_WORKORDER_ACTIONS
    try:
        returncode, stdout, stderr = run_cli_process(command, timeout)
    except KeyboardInterrupt as exc:
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, "interrupted by the user while executing") from exc
        raise
    except subprocess.TimeoutExpired as exc:
        if is_non_idempotent:
            raise WorkorderTimeoutError(action) from exc
        raise ClientError(f"{action} call timed out") from exc
    except ClientError as exc:
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, "the CLI output could not be decoded reliably") from exc
        raise
    except OSError as exc:
        raise ClientError(f"cannot start the Alibaba Cloud CLI for {action}: {safe_error_text(str(exc))}") from exc

    response: Any = None
    response_error: Optional[json.JSONDecodeError] = None
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as exc:
        response_error = exc

    if returncode != 0:
        if isinstance(response, dict) and response.get("Success") is False:
            summary = {
                "Success": response.get("Success"),
                "Code": response.get("Code"),
                "Message": safe_error_text(str(response.get("Message", ""))),
                "RequestId": response.get("RequestId"),
            }
            raise ClientError(f"{action} was not successful: {json.dumps(summary, ensure_ascii=False)}")
        detail = safe_error_text(stderr or stdout)
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, f"the CLI exited abnormally (exit code {returncode}): {detail}")
        raise ClientError(f"{action} failed (exit code {returncode}): {detail}")
    if response_error is not None:
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, "the response is not verifiable JSON") from response_error
        raise ClientError(f"{action} returned non-JSON content: {safe_error_text(stdout)}") from response_error
    if not isinstance(response, dict):
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, "the response structure cannot be verified")
        raise ClientError(f"{action} returned an invalid structure")
    success = response.get("Success")
    code = response.get("Code")
    if success is not True or (code is not None and str(code) not in {"0", "200"}):
        summary = {
            "Success": success,
            "Code": code,
            "Message": safe_error_text(str(response.get("Message", ""))),
            "RequestId": response.get("RequestId"),
        }
        if is_non_idempotent and success is not False:
            raise WorkorderIndeterminateError(
                action,
                f"the success state of the response cannot be verified: {json.dumps(summary, ensure_ascii=False)}",
            )
        raise ClientError(f"{action} was not successful: {json.dumps(summary, ensure_ascii=False)}")
    # Successful responses are returned verbatim: API content such as engineer replies is
    # not secret-filtered, so the whole conversation stays retrievable.
    # Secret checks only apply to the customer sending side (request parameters and the
    # create/reply/evaluate content), see contains_secret and redact_text above.
    return response


def ticket_status(response: dict[str, Any]) -> tuple[str, str]:
    data = response.get("Data")
    status = data.get("Status") if isinstance(data, dict) else None
    if isinstance(status, dict):
        return str(status.get("Value", "")), str(status.get("Label", ""))
    return str(status or ""), ""


def current_ticket_state(ticket_id: str) -> dict[str, str]:
    response = workorder_call("GetTicket", {"TicketId": ticket_id})
    value, label = ticket_status(response)
    if not value and not label:
        raise ClientError(f"cannot confirm the current state of ticket {ticket_id}, so the write operation stopped")
    return {"value": value, "label": label}


def non_terminal_state(ticket_id: str) -> dict[str, str]:
    state = current_ticket_state(ticket_id)
    if normalize(state["value"]) in TERMINAL_STATUS_VALUES or state["label"] in TERMINAL_STATUS_LABELS:
        raise ClientError(f"ticket {ticket_id} is already in a terminal state ({state['label'] or state['value']}); further writes are forbidden")
    return state


def ticket_url(ticket_id: str) -> str:
    return TICKET_WEB_URL_TEMPLATE.format(ticket_id=urllib.parse.quote(ticket_id, safe=""))


def ticket_list_data(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response.get("Data")
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ClientError("ListTickets returned an invalid ticket list structure")
    return data


def list_ticket_result(response: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    tickets: list[dict[str, Any]] = []
    for item in ticket_list_data(response):
        enriched = dict(item)
        ticket_id = item.get("TicketId")
        if isinstance(ticket_id, (str, int)) and not isinstance(ticket_id, bool):
            rendered_ticket_id = str(ticket_id).strip()
            if rendered_ticket_id:
                enriched["TicketUrl"] = ticket_url(rendered_ticket_id)
        tickets.append(enriched)
    return {
        "query": query,
        "pageNumber": response.get("PageNumber"),
        "pageSize": response.get("PageSize"),
        "totalCount": response.get("TotalCount"),
        "tickets": tickets,
        "apiResponse": response,
    }


def list_ticket_params(args: argparse.Namespace) -> dict[str, Any]:
    days = int(args.days)
    page_number = int(args.page_number)
    page_size = int(args.page_size)
    if not 1 <= days <= 3650:
        raise ClientError("days must be between 1 and 3650")
    if not 1 <= page_number <= 9_999_999:
        raise ClientError("page-number must be between 1 and 9999999")
    if not 10 <= page_size <= 100:
        raise ClientError("page-size must be between 10 and 100")
    end_date = int(time.time() * 1000)
    params: dict[str, Any] = {
        "StartDate": end_date - days * 24 * 60 * 60 * 1000,
        "EndDate": end_date,
        "PageNumber": page_number,
        "PageSize": page_size,
    }
    keyword = getattr(args, "keyword", None)
    if keyword:
        safe_keyword = redact_text(str(keyword)).strip()
        if len(safe_keyword) > 200:
            raise ClientError("keyword must not exceed 200 characters")
        params["Keyword"] = safe_keyword
    requested_ticket_id = getattr(args, "ticket_id", None)
    if requested_ticket_id:
        rendered_ticket_id = str(requested_ticket_id).strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", rendered_ticket_id):
            raise ClientError("ticket-id has an invalid format")
        params["TicketId"] = rendered_ticket_id
    return params


def severity_value(data: dict[str, Any]) -> str:
    severity = data.get("Severity")
    if isinstance(severity, dict):
        return str(severity.get("Value", ""))
    return str(severity or "")


def ticket_matches_create_payload(
    response: dict[str, Any],
    payload: dict[str, Any],
    start_date: int,
    end_date: int,
) -> bool:
    data = response.get("Data")
    if not isinstance(data, dict):
        return False
    create_time = data.get("CreateTime")
    try:
        rendered_create_time = int(create_time)
    except (TypeError, ValueError):
        return False
    return (
        start_date <= rendered_create_time <= end_date
        and str(data.get("Title", "")) == payload["Title"]
        and str(data.get("Description", "")) == payload["Description"]
        and str(data.get("CategoryId", "")) == payload["CategoryId"]
        and severity_value(data) == str(payload["Severity"])
    )


def reconcile_indeterminate_create(
    payload: dict[str, Any],
    started_at_ms: int,
    request_id: str,
    failure: WorkorderIndeterminateError,
) -> dict[str, Any]:
    start_date = max(0, started_at_ms - CREATE_RECONCILIATION_CLOCK_SKEW_MS)
    end_date = int(time.time() * 1000) + CREATE_RECONCILIATION_CLOCK_SKEW_MS
    query = {
        "StartDate": start_date,
        "EndDate": end_date,
        "PageNumber": 1,
        "PageSize": 100,
    }
    try:
        listed = workorder_call("ListTickets", query, timeout=20)
        tickets = ticket_list_data(listed)
        total_count = listed.get("TotalCount")
        if not isinstance(total_count, int) or isinstance(total_count, bool) or total_count != len(tickets):
            raise ClientError("the recent ticket result was incomplete")
        title_matches = [item for item in tickets if str(item.get("Title", "")) == payload["Title"]]
        verified: list[tuple[str, dict[str, Any]]] = []
        for item in title_matches:
            ticket_id = item.get("TicketId")
            if not isinstance(ticket_id, (str, int)) or isinstance(ticket_id, bool):
                continue
            rendered_ticket_id = str(ticket_id).strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", rendered_ticket_id):
                continue
            detail = workorder_call("GetTicket", {"TicketId": rendered_ticket_id}, timeout=20)
            if ticket_matches_create_payload(detail, payload, start_date, end_date):
                verified.append((rendered_ticket_id, detail))
    except KeyboardInterrupt as exc:
        raise ClientError(
            "the CreateTicket result is indeterminate and the automatic reconciliation was interrupted by the user; the creation state remains unknown, automatic retry is forbidden, "
            "verify manually through ticket list or the ticket console"
        ) from exc
    except ClientError as exc:
        raise ClientError(
            "the CreateTicket result is indeterminate and the automatic reconciliation failed; the creation state remains unknown, automatic retry is forbidden, "
            f"verify manually through ticket list or the ticket console. Reconciliation error: {safe_error_text(str(exc))}"
        ) from exc
    if len(verified) != 1:
        raise ClientError(
            "the CreateTicket result is indeterminate and the automatic reconciliation found no unique, fully matching ticket; the creation state remains unknown, "
            "automatic retry is forbidden, verify manually through ticket list or the ticket console"
        )
    ticket_id, detail = verified[0]
    return {
        "ticketId": ticket_id,
        "ticketUrl": ticket_url(ticket_id),
        "creationState": (
            "reconciled_after_timeout"
            if isinstance(failure, WorkorderTimeoutError)
            else "reconciled_after_indeterminate_result"
        ),
        "createRetried": False,
        "clientRequestId": request_id,
        "reconciliation": {
            "outcome": "unique_verified_match",
            "method": "ListTickets+GetTicket+clientRequestId",
            "trigger": failure.reason,
            "startDate": start_date,
            "endDate": end_date,
        },
        "ticketResponse": detail,
    }


def evaluation_payload(
    args: argparse.Namespace,
    state: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(args.score, int) or isinstance(args.score, bool) or not 1 <= args.score <= 5:
        raise ClientError("score must be an integer from 1 to 5")
    if not isinstance(args.solved, bool):
        raise ClientError("solved must be true or false")
    api_payload: dict[str, Any] = {
        "TicketId": args.ticket_id,
        "Score": str(args.score),
        "Solved": args.solved,
    }
    content_file = getattr(args, "content_file", None)
    if content_file:
        content = redact_text(read_input(content_file, 2_000)).strip()
        if content:
            api_payload["Content"] = content
    confirmation_payload = {**api_payload, "ExpectedStatus": state}
    return api_payload, confirmation_payload


def confirmation_digest(operation: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"operation": operation, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def new_confirmation_token_id() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


def confirmation_token_id(provided: Optional[str]) -> str:
    if not provided:
        raise ClientError("a write operation is missing its confirmation token; run the matching preview command first and show the complete draft to the user")
    match = re.fullmatch(r"v1:([a-f0-9]{64})", provided)
    if not match:
        raise ClientError("the confirmation token has an invalid format; preview again and obtain user confirmation")
    return match.group(1)


def issue_confirmation(
    home: Path,
    operation: str,
    payload: dict[str, Any],
    token_id: Optional[str] = None,
) -> str:
    resolved_token_id = token_id or new_confirmation_token_id()
    if not re.fullmatch(r"[a-f0-9]{64}", resolved_token_id):
        raise ClientError("the confirmation token identifier is invalid")
    directory = home / "confirmations" / "pending"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError as exc:
        raise ClientError(f"cannot protect the confirmation token directory: {safe_error_text(str(exc))}") from exc
    record = {
        "digest": confirmation_digest(operation, payload),
        "expiresAt": time.time() + CONFIRMATION_TTL_SECONDS,
    }
    path = directory / f"{resolved_token_id}.json"
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        path.chmod(0o600)
    except OSError as exc:
        raise ClientError(f"cannot save the confirmation token: {safe_error_text(str(exc))}") from exc
    return f"v1:{resolved_token_id}"


def require_confirmation(
    home: Path,
    provided: Optional[str],
    operation: str,
    payload: dict[str, Any],
) -> None:
    token_id = confirmation_token_id(provided)
    pending = home / "confirmations" / "pending" / f"{token_id}.json"
    try:
        record = json.loads(pending.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClientError("the confirmation token does not exist or was already used; preview again and obtain user confirmation") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClientError("the confirmation token record is invalid; preview again and obtain user confirmation") from exc
    expected = confirmation_digest(operation, payload)
    if (
        not isinstance(record, dict)
        or not isinstance(record.get("digest"), str)
        or not hmac.compare_digest(record["digest"], expected)
    ):
        raise ClientError("the confirmation token does not match the current content or ticket state; preview again and obtain user confirmation")
    expires_at = record.get("expiresAt")
    if not isinstance(expires_at, (int, float)) or isinstance(expires_at, bool) or time.time() > expires_at:
        raise ClientError("the confirmation token has expired; preview again and obtain user confirmation")

    consumed_dir = home / "confirmations" / "consumed"
    consumed_dir.mkdir(parents=True, exist_ok=True)
    try:
        consumed_dir.chmod(0o700)
        os.replace(pending, consumed_dir / f"{token_id}.json")
    except FileNotFoundError as exc:
        raise ClientError("the confirmation token does not exist or was already used; preview again and obtain user confirmation") from exc
    except OSError as exc:
        raise ClientError(f"cannot consume the confirmation token: {safe_error_text(str(exc))}") from exc


def ticket_id_from_create_response(response: dict[str, Any]) -> Optional[str]:
    data = response.get("Data")
    candidates: list[Any] = [data, response.get("TicketId"), response.get("ticketId")]
    if isinstance(data, dict):
        candidates.extend(data.get(key) for key in ("TicketId", "ticketId", "Id", "id"))
    for candidate in candidates:
        if isinstance(candidate, (str, int)) and not isinstance(candidate, bool):
            ticket_id = str(candidate).strip()
            if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", ticket_id):
                return ticket_id
    return None


def created_ticket_result(response: dict[str, Any]) -> dict[str, Any]:
    ticket_id = ticket_id_from_create_response(response)
    if ticket_id is None:
        raise WorkorderIndeterminateError(
            "CreateTicket",
            "the response reported success but returned no verifiable ticket id",
        )
    return {
        "ticketId": ticket_id,
        "ticketUrl": ticket_url(ticket_id),
        "creationState": "api_confirmed",
        "createRetried": False,
        "apiResponse": response,
    }


def create_payload(args: argparse.Namespace) -> dict[str, Any]:
    content = redact_text(read_input(args.content_file, 25_000)).strip()
    title = redact_text(args.title).strip()
    if not content:
        raise ClientError("the ticket content must not be empty")
    if not title:
        raise ClientError("the ticket title must not be empty")
    if not title.startswith(TICKET_TITLE_PREFIX):
        title = f"{TICKET_TITLE_PREFIX} {title}"
    return {
        "Description": content,
        "Severity": args.severity,
        "CategoryId": str(args.category_id),
        "Title": title,
    }


def bind_create_request_marker(
    payload: dict[str, Any],
    token_id: str,
) -> tuple[dict[str, Any], str]:
    request_id = hashlib.sha256(token_id.encode("ascii")).hexdigest()[:24]
    marked_payload = dict(payload)
    description = str(payload.get("Description", ""))
    marker = f"[client request id] {request_id}"
    if marker not in description:
        marked_payload["Description"] = f"{description}\n\n{marker}"
    return marked_payload, request_id


def _selfcheck_bind_create_request_marker() -> None:
    """Boundary assertions for bind_create_request_marker(): normal, repeated, distinct token.

    They call no cloud API and pin the contract that the marker is appended exactly once,
    that binding an already marked payload again is idempotent (a replayed preview must not
    double-append the marker), and that the original payload is never mutated.
    """
    token_id = "a" * 64
    base = {"Description": "body", "Severity": 1, "CategoryId": "123", "Title": "t"}
    marked, request_id = bind_create_request_marker(base, token_id)
    marker = f"[client request id] {request_id}"
    if marked["Description"] != f"body\n\n{marker}":
        raise AssertionError("the first bind must append exactly one marker")
    if base["Description"] != "body":
        raise AssertionError("binding must not mutate the original payload")
    again, repeated_id = bind_create_request_marker(marked, token_id)
    if repeated_id != request_id or again["Description"] != marked["Description"]:
        raise AssertionError("binding an already marked payload must be idempotent")
    other, other_id = bind_create_request_marker(base, "b" * 64)
    if other_id == request_id or other["Description"] == marked["Description"]:
        raise AssertionError("a different confirmation token must produce a different marker")


def reply_payload(args: argparse.Namespace, state: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    content = redact_text(read_input(args.content_file, 20_000)).strip()
    if not content:
        raise ClientError("the reply content must not be empty")
    api_payload = {"TicketId": args.ticket_id, "Content": content, "Encrypt": False}
    confirmation_payload = {**api_payload, "ExpectedStatus": state}
    return api_payload, confirmation_payload


def rules_status(home: Path) -> dict[str, Any]:
    try:
        state = load_state(home)
        state_error = None
    except ClientError as exc:
        state = {}
        state_error = safe_error_text(str(exc))
    selected: Optional[str] = None
    integrity_error: Optional[str] = state_error
    for key in ("active", "previous"):
        name = state.get(key)
        package = package_path(home, name)
        if package is None:
            continue
        try:
            load_rules_from_dir(package, expected_snapshot_id=name)
            selected = key
            break
        except ClientError as exc:
            integrity_error = safe_error_text(str(exc))
    effective_source = state.get("effectiveSource")
    if selected is None and not effective_source:
        effective_source = "default"
    return {
        "available": selected is not None,
        "selected": selected,
        "usingFallback": selected == "previous",
        "active": state.get("active"),
        "previous": state.get("previous"),
        "integrityError": integrity_error if selected is None else None,
        "checkedAt": state.get("checkedAt"),
        "sourceRoot": state.get("sourceRoot") or state.get("source"),
        "sourcePrefix": state.get("sourcePrefix", ""),
        "sourceType": state.get("sourceType", "cached" if selected else "default"),
        "sourceCommit": state.get("sourceCommit"),
        "ossError": state.get("ossError"),
        "githubError": state.get("githubError"),
        "degraded": bool(state.get("degraded", selected is None)),
        "effectiveSource": effective_source,
        "fileCount": state.get("fileCount"),
        "nextCheckDue": (
            datetime.fromtimestamp(parse_checked_at(state.get("checkedAt")) + CHECK_INTERVAL_SECONDS, timezone.utc).isoformat()
            if state.get("checkedAt")
            else None
        ),
    }


def aliyun_cli_status() -> dict[str, Any]:
    executable, executable_source = resolve_cli_executable()
    if not executable:
        return {
            "installed": False,
            "usable": False,
            "reason": "cli_missing",
            "version": None,
            "oauthSupported": None,
            "executableSource": executable_source,
        }
    # The User-Agent version gate is evaluated before any CLI call is probed, so an
    # incomplete installation is reported as itself instead of looking like a broken CLI.
    try:
        skill_version()
    except SkillVersionError as exc:
        return {
            "installed": True,
            "usable": False,
            "reason": "skill_version_unavailable",
            "version": None,
            "oauthSupported": None,
            "executableSource": executable_source,
            "detail": safe_error_text(str(exc)),
        }
    try:
        returncode, stdout, stderr = run_cli_process([executable, "version"], timeout=10)
    except (ClientError, OSError, subprocess.TimeoutExpired) as exc:
        return {
            "installed": True,
            "usable": False,
            "reason": "version_check_failed",
            "version": None,
            "oauthSupported": None,
            "executableSource": executable_source,
            "detail": safe_error_text(str(exc)),
        }
    version_text = safe_error_text(stdout or stderr).strip()
    if returncode != 0:
        return {
            "installed": True,
            "usable": False,
            "reason": "version_check_failed",
            "version": version_text or None,
            "oauthSupported": None,
            "executableSource": executable_source,
            "detail": f"aliyun version exited with code {returncode}",
        }
    oauth_supported: Optional[bool] = None
    try:
        help_returncode, help_stdout, help_stderr = run_cli_process(
            [executable, "configure", "--help"], timeout=10
        )
        if help_returncode == 0:
            oauth_supported = "OAuth" in (help_stdout + help_stderr)
    except (ClientError, OSError, subprocess.TimeoutExpired):
        pass
    return {
        "installed": True,
        "usable": True,
        "reason": "version_succeeded",
        "version": version_text[:120] or None,
        "oauthSupported": oauth_supported,
        "executableSource": executable_source,
    }


def unknown_workorder_capabilities(reason: str, detail: Optional[str] = None) -> dict[str, Any]:
    probe: dict[str, Any] = {"state": "unknown", "complete": False, "reason": reason}
    if detail:
        probe["detail"] = safe_error_text(detail)
    required_apis = sorted({api for apis in WORKORDER_FEATURE_APIS.values() for api in apis})
    return {
        "probe": probe,
        "advertisedApis": [],
        "apiSupport": {api: "unknown" for api in required_apis},
    }


def workorder_capability_status() -> dict[str, Any]:
    """Report which Workorder plugin commands the local CLI can resolve.

    One `aliyun workorder --help` call is enough: when the workorder product plugin
    is installed, its help lists every command in lowercase-hyphenated form, and
    that listing is language independent because the command tokens are ASCII.
    A help page without any known command token proves nothing about the API
    surface, so every operation stays `unknown` instead of being called
    unsupported. No API request is sent by this probe.
    """
    executable, _ = resolve_cli_executable()
    if not executable:
        return unknown_workorder_capabilities("cli_missing")
    try:
        skill_version()
    except SkillVersionError as exc:
        return unknown_workorder_capabilities("skill_version_unavailable", str(exc))
    try:
        returncode, stdout, stderr = run_cli_process([executable, "workorder", "--help"], timeout=15)
    except (ClientError, OSError, subprocess.TimeoutExpired) as exc:
        return unknown_workorder_capabilities("workorder_help_failed", str(exc))
    if returncode != 0:
        return unknown_workorder_capabilities(
            "workorder_help_failed",
            f"aliyun workorder --help exited with code {returncode}: {stderr or stdout}",
        )
    text = f"{stdout}\n{stderr}"
    advertised = {
        api
        for api, plugin_command in WORKORDER_PLUGIN_COMMANDS.items()
        if re.search(rf"(?m)^\s*{re.escape(plugin_command)}\b", text)
    }
    if not advertised:
        return unknown_workorder_capabilities(
            "workorder_help_lists_no_commands",
            "the help page did not list any workorder command, so the plugin is probably not installed",
        )
    api_support = {
        api: "supported" if api in advertised else "unsupported"
        for api in sorted(WORKORDER_PLUGIN_COMMANDS)
    }
    unsupported = sorted(api for api, state in api_support.items() if state == "unsupported")
    return {
        "probe": {
            "state": "succeeded",
            "complete": True,
            "reason": "plugin_help_command_list_resolved" if not unsupported else "some_plugin_commands_unsupported",
            "mode": "plugin_help_listing",
            "listedCommands": len(advertised),
            "unsupportedApis": unsupported,
            "undeterminedApis": [],
        },
        "advertisedApis": sorted(advertised),
        "apiSupport": api_support,
    }


def support_capability_matrix(
    workorder_capabilities: dict[str, Any],
    workorder_status: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    matrix: dict[str, dict[str, Any]] = {
        capability: {
            "support": "supported",
            "available": True,
            "requiresCli": False,
            "requiredApis": [],
            "missingApis": [],
            "unknownApis": [],
            "blockedReason": None,
            "permissionVerified": True,
            "availabilityBasis": "local_client",
        }
        for capability in ("rules_update", "match", "draft")
    }
    api_support = workorder_capabilities.get("apiSupport", {})
    for capability, required_apis in WORKORDER_FEATURE_APIS.items():
        missing = [api for api in required_apis if api_support.get(api) == "unsupported"]
        unknown = [api for api in required_apis if api_support.get(api) not in {"supported", "unsupported"}]
        if missing:
            support = "unsupported"
        elif unknown:
            support = "unknown"
        else:
            support = "supported"
        if not workorder_status.get("usable"):
            available: Optional[bool] = False
            blocked_reason = workorder_status.get("reason", "workorder_access_unavailable")
        elif support == "supported":
            available = True
            blocked_reason = None
        elif support == "unsupported":
            available = False
            blocked_reason = "required_api_unsupported"
        else:
            available = None
            blocked_reason = "api_support_unknown"
        matrix[capability] = {
            "support": support,
            "available": available,
            "requiresCli": True,
            "requiredApis": list(required_apis),
            "missingApis": missing,
            "unknownApis": unknown,
            "blockedReason": blocked_reason,
            "permissionVerified": False,
            "availabilityBasis": "cli_advertised_and_list_products_access",
            "operationStillSubjectToRamAndTicketState": True,
        }
    return matrix


def windows_shell_guidance() -> dict[str, dict[str, str]]:
    data_directory = agent_data_directory_names()[0]
    windows_relative = f"{data_directory}\\aliyun-cli"
    posix_relative = f"{data_directory}/aliyun-cli"
    oauth_args = "configure --mode OAuth --profile default"
    return {
        "cmd": {
            "temporaryPath": f'set "PATH=%USERPROFILE%\\{windows_relative};%PATH%"',
            "verify": "aliyun version",
            "oauthFullPath": f'"%USERPROFILE%\\{windows_relative}\\aliyun.exe" {oauth_args}',
        },
        "powershell": {
            "temporaryPath": f'$env:Path = "$env:USERPROFILE\\{windows_relative};$env:Path"',
            "verify": "aliyun version",
            "oauthFullPath": f'& "$env:USERPROFILE\\{windows_relative}\\aliyun.exe" {oauth_args}',
        },
        "gitBash": {
            "temporaryPath": f'export PATH="$HOME/{posix_relative}:$PATH"',
            "verify": "aliyun version",
            "oauthFullPath": f'"$HOME/{posix_relative}/aliyun.exe" {oauth_args}',
        },
    }


def cli_install_plan() -> dict[str, Any]:
    shell_guidance: Optional[dict[str, dict[str, str]]] = None
    recommended_directory: Optional[str] = None
    if sys.platform == "darwin":
        if shutil.which("brew"):
            method = "homebrew"
            command = "brew install aliyun-cli"
            download_url = None
            interactive = False
        else:
            method = "official_pkg"
            command = None
            download_url = "https://aliyuncli.alicdn.com/aliyun-cli-latest.pkg"
            interactive = True
        platform_name = "macos"
    elif is_windows_runtime():
        platform_name = "windows"
        machine = platform.machine().lower()
        if machine in {"amd64", "x86_64"}:
            method = "official_zip"
            download_url = "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip"
        else:
            method = "unsupported_architecture"
            download_url = None
        command = None
        interactive = True
        data_directory = agent_data_directory_names()[0]
        recommended_directory = f"%USERPROFILE%\\{data_directory}\\aliyun-cli"
        shell_guidance = windows_shell_guidance()
    elif sys.platform.startswith("linux"):
        platform_name = "linux"
        method = "official_install_script"
        command = '/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"'
        download_url = "https://aliyuncli.alicdn.com/install.sh"
        interactive = False
    else:
        platform_name = "unsupported"
        method = "official_documentation"
        command = None
        download_url = None
        interactive = True
    return {
        "platform": platform_name,
        "recommendedMethod": method,
        "command": command,
        "downloadUrl": download_url,
        "interactive": interactive,
        "recommendedInstallDirectory": recommended_directory,
        "shellGuidance": shell_guidance,
        "pathRefreshRequired": platform_name == "windows",
        "cliPathOverrideEnvironmentVariable": CLI_PATH_ENV,
        "cliEncodingOverrideEnvironmentVariable": CLI_ENCODING_ENV,
        "documentation": CLI_INSTALL_DOC_URL,
        "requiresExplicitConsent": True,
        "executeAutomatically": False,
        "impact": "installs a system-level executable, and may modify PATH, access the network or request administrator privileges",
    }


def workorder_access_status() -> dict[str, Any]:
    executable, _ = resolve_cli_executable()
    if not executable:
        return {"usable": False, "reason": "cli_missing"}
    try:
        skill_version()
    except SkillVersionError as exc:
        return {"usable": False, "reason": "skill_version_unavailable", "detail": safe_error_text(str(exc))}
    try:
        workorder_call("ListProducts", {"Language": "zh"}, timeout=20)
    except ClientError as exc:
        return {"usable": False, "reason": "api_probe_failed", "detail": safe_error_text(str(exc))}
    return {"usable": True, "reason": "list_products_succeeded"}


def support_readiness(cli_status: dict[str, Any], workorder_status: dict[str, Any]) -> dict[str, Any]:
    if cli_status.get("reason") == "skill_version_unavailable" or workorder_status.get("reason") == "skill_version_unavailable":
        state = "workorder_access_unavailable"
        next_action = "request_skill_reinstallation_consent"
    elif not cli_status["installed"]:
        state = "cli_missing"
        next_action = "request_cli_install_consent"
    elif not cli_status["usable"]:
        state = "cli_unusable"
        next_action = "request_cli_repair_consent"
    elif not workorder_status["usable"] and cli_status.get("oauthSupported") is False:
        state = "oauth_unsupported"
        next_action = "request_cli_update_consent"
    elif not workorder_status["usable"]:
        state = "workorder_access_unavailable"
        next_action = "request_oauth_configuration_consent"
    else:
        state = "ready"
        next_action = "none"
    return {
        "readyForTicketOperations": state == "ready",
        "state": state,
        "nextAction": next_action,
        "localCapabilities": ["rules_update", "match", "draft"],
        "blockingCapabilities": [] if state == "ready" else list(CLI_BLOCKED_CAPABILITIES),
    }


def cli_setup_guidance(cli_status: dict[str, Any], workorder_status: dict[str, Any]) -> dict[str, Any]:
    install_plan = cli_install_plan()
    install_plan["required"] = not cli_status["installed"]
    oauth_supported = cli_status.get("oauthSupported")
    oauth_command = (
        "aliyun configure --mode OAuth --profile default"
        if oauth_supported is not False
        else None
    )
    shell_guidance = windows_shell_guidance() if is_windows_runtime() else None
    customer_commands = (
        {shell: oauth_command for shell in ("cmd", "powershell", "gitBash")}
        if shell_guidance is not None and oauth_command is not None
        else ({"posix": oauth_command} if oauth_command is not None else None)
    )
    full_path_fallback = (
        {shell: values["oauthFullPath"] for shell, values in shell_guidance.items()}
        if shell_guidance is not None and oauth_command is not None
        else None
    )
    python_launcher = "py" if is_windows_runtime() else "python3"
    return {
        "installation": install_plan,
        "authentication": {
            "required": not workorder_status["usable"],
            "preferredMode": "OAuth",
            "available": oauth_supported,
            "command": oauth_command,
            "customerCommandsByShell": customer_commands,
            "fullPathFallbackByShell": full_path_fallback,
            "actionWhenUnsupported": "request_cli_update_consent",
            "browserRequired": True,
            "requiresExplicitConsent": True,
            "customerCompletesAuthentication": True,
            "executionOwner": "customer",
            "agentMustNotExecute": True,
            "mustRunInCustomerTerminal": True,
            "mustNotCaptureOutput": True,
            "mustNotRecordAuthorizationUrl": True,
            "fallbackModes": [
                "CloudSSO",
                "EcsRamRole",
                "OIDC",
                "RamRoleArn",
                "ChainableRamRoleArn",
                "CredentialsURI",
                "External",
            ],
            "fallbackRequiresCustomerChoice": True,
            "documentation": CLI_CREDENTIAL_DOC_URL,
            "secretPolicy": (
                "never ask for, fill in or echo an AccessKey secret, STS token, bearer token or other secret in the conversation; "
                "if the customer insists on a credential mode that carries a secret, only the customer may configure it interactively in their own terminal"
            ),
        },
        "verification": {
            "pythonLauncher": python_launcher,
            "commands": ["aliyun version", f"{python_launcher} scripts/aliyun_support.py doctor"],
            "successCondition": "doctor.readiness.readyForTicketOperations=true and the Workorder ListProducts probe succeeded",
            "authenticationSuccessMustBeVerifiedByDoctor": True,
        },
    }


def rules_source_configuration_status() -> dict[str, Any]:
    root_url, oss_prefix, legacy_used, error = configured_oss_source()
    return {
        "configured": root_url is not None,
        "configurationSource": oss_configuration_source(),
        "sourceRoot": root_url,
        "sourcePrefix": oss_prefix if error is None else None,
        "legacyConfiguration": legacy_used,
        "error": error,
    }


def command_doctor(args: argparse.Namespace) -> dict[str, Any]:
    cli_status = aliyun_cli_status()
    workorder_status = (
        workorder_access_status()
        if cli_status["usable"]
        else {"usable": False, "reason": cli_status["reason"]}
    )
    workorder_capabilities = (
        workorder_capability_status()
        if cli_status["usable"]
        else unknown_workorder_capabilities(cli_status["reason"])
    )
    source_configuration = rules_source_configuration_status()
    _, home_legacy = environment_value("ALIBABACLOUD_SUPPORT_HOME", "ALIYUN_SUPPORT_HOME")
    return {
        "appName": APP_NAME,
        "version": VERSION,
        "python": sys.version.split()[0],
        "pythonSupported": sys.version_info >= (3, 9),
        "aliyunCliInstalled": cli_status["installed"],
        "aliyunCli": cli_status,
        "workorderAccess": workorder_status,
        "workorderCapabilities": workorder_capabilities,
        "capabilityMatrix": support_capability_matrix(workorder_capabilities, workorder_status),
        "readiness": support_readiness(cli_status, workorder_status),
        "setupGuidance": cli_setup_guidance(cli_status, workorder_status),
        "rulesConfigured": source_configuration["configured"],
        "rulesSource": source_configuration,
        "rules": rules_status(args.home),
        "selfUpdate": self_update_status(args.home),
        "legacyConfiguration": {
            "inUse": home_legacy or source_configuration["legacyConfiguration"],
            "home": home_legacy,
            "rules": source_configuration["legacyConfiguration"],
        },
        "credentialHandling": "Alibaba Cloud CLI default credential chain; credential values are never read or printed",
        "writeTransport": "redacted RPC string parameters are passed directly to the local aliyun CLI without a shell",
    }


def command_match(args: argparse.Namespace) -> dict[str, Any]:
    text = redact_text(read_input(args.input, 100_000))
    product_filter = redact_text(args.product) if args.product else None
    candidates = issue_candidates(load_rules(args.home), text, product_filter)
    if not product_filter:
        candidates = [item for item in candidates if item["productScore"] > 0]
    top = candidates[:5]
    selected = None
    fallback = None
    confidence = "none"
    if top and top[0]["issueScore"] > 0:
        runner_score = top[1]["score"] if len(top) > 1 else -1
        if top[0]["score"] >= 3 and top[0]["score"] > runner_score:
            selected = top[0]
            confidence = "high"
        else:
            confidence = "ambiguous"
    elif top:
        confidence = "fallback"
        fallback = default_match_template(product_filter or top[0]["product"], "issue_type_not_found")
    else:
        confidence = "fallback"
        fallback = default_match_template(product_filter, "product_not_found")
    return {
        "confidence": confidence,
        "selected": selected,
        "candidates": top,
        "fallback": fallback,
    }


def command_draft(args: argparse.Namespace) -> dict[str, Any]:
    try:
        payload = json.loads(read_input(args.input))
    except json.JSONDecodeError as exc:
        raise ClientError(f"the draft input JSON is invalid: {exc}") from exc
    return create_draft(args.home, payload)


def command_catalog(args: argparse.Namespace) -> dict[str, Any]:
    if args.catalog_command == "products":
        return workorder_call("ListProducts", {"Name": args.name, "Language": args.language})
    return workorder_call(
        "ListCategories",
        {"ProductId": args.product_id, "Name": args.name, "Language": args.language},
    )


def command_ticket(args: argparse.Namespace) -> dict[str, Any]:
    home = args.home
    if args.ticket_command == "get":
        params = {"TicketId": args.ticket_id}
        return {
            "ticket": workorder_call("GetTicket", params),
            "notes": workorder_call("ListTicketNotes", params),
        }

    if args.ticket_command == "list":
        params = list_ticket_params(args)
        return list_ticket_result(workorder_call("ListTickets", params), params)

    if args.ticket_command in {"preview-create", "create"}:
        base_payload = create_payload(args)
        if args.ticket_command == "preview-create":
            token_id = new_confirmation_token_id()
            payload, request_id = bind_create_request_marker(base_payload, token_id)
            return {
                "operation": "create",
                "preview": {
                    "categoryId": payload["CategoryId"],
                    "severity": payload["Severity"],
                    "title": payload["Title"],
                    # preview.content is the exact body the customer confirms and the client
                    # replays; the request marker lives only inside the create payload, so a
                    # replay of preview-create output can never double-append it.
                    "content": base_payload["Description"],
                    "clientRequestId": request_id,
                },
                "confirmationToken": issue_confirmation(home, "create", payload, token_id=token_id),
            }
        token_id = confirmation_token_id(args.confirmation_token)
        payload, request_id = bind_create_request_marker(base_payload, token_id)
        require_confirmation(home, args.confirmation_token, "create", payload)
        started_at_ms = int(time.time() * 1000)
        try:
            result = created_ticket_result(workorder_call("CreateTicket", payload))
            result["clientRequestId"] = request_id
            return result
        except WorkorderIndeterminateError as exc:
            return reconcile_indeterminate_create(payload, started_at_ms, request_id, exc)

    if args.ticket_command in {"preview-reply", "reply"}:
        state = non_terminal_state(args.ticket_id)
        api_payload, bound_payload = reply_payload(args, state)
        if args.ticket_command == "preview-reply":
            return {
                "operation": "reply",
                "preview": {
                    "ticketId": args.ticket_id,
                    "currentStatus": state,
                    "content": api_payload["Content"],
                },
                "confirmationToken": issue_confirmation(home, "reply", bound_payload),
            }
        require_confirmation(home, args.confirmation_token, "reply", bound_payload)
        latest_state = non_terminal_state(args.ticket_id)
        if latest_state != state:
            raise ClientError("the ticket status changed after confirmation; preview the reply again and obtain user confirmation")
        return workorder_call("ReplyTicket", api_payload)

    if args.ticket_command in {"preview-evaluate", "evaluate"}:
        state = current_ticket_state(args.ticket_id)
        api_payload, bound_payload = evaluation_payload(args, state)
        if args.ticket_command == "preview-evaluate":
            return {
                "operation": "evaluate",
                "preview": {
                    "ticketId": args.ticket_id,
                    "ticketUrl": ticket_url(args.ticket_id),
                    "currentStatus": state,
                    "score": int(api_payload["Score"]),
                    "solved": api_payload["Solved"],
                    "content": api_payload.get("Content"),
                },
                "confirmationToken": issue_confirmation(home, "evaluate", bound_payload),
            }
        require_confirmation(home, args.confirmation_token, "evaluate", bound_payload)
        latest_state = current_ticket_state(args.ticket_id)
        if latest_state != state:
            raise ClientError("the ticket status changed after confirmation; preview the evaluation again and obtain user confirmation")
        return {
            "ticketId": args.ticket_id,
            "ticketUrl": ticket_url(args.ticket_id),
            "apiResponse": workorder_call("EvaluateTicket", api_payload),
        }

    if args.ticket_command in {"preview-close", "close"}:
        state = non_terminal_state(args.ticket_id)
        bound_payload = {"TicketId": args.ticket_id, "ExpectedStatus": state}
        if args.ticket_command == "preview-close":
            return {
                "operation": "close",
                "preview": {"ticketId": args.ticket_id, "currentStatus": state},
                "confirmationToken": issue_confirmation(home, "close", bound_payload),
            }
        require_confirmation(home, args.confirmation_token, "close", bound_payload)
        latest_state = non_terminal_state(args.ticket_id)
        if latest_state != state:
            raise ClientError("the ticket status changed after confirmation; preview the close operation again and obtain user confirmation")
        return workorder_call("CloseTicket", {"TicketId": args.ticket_id})
    raise ClientError("unknown ticket command")


def parse_cli_boolean(value: str) -> bool:
    rendered = normalize(value)
    if rendered == "true":
        return True
    if rendered == "false":
        return False
    raise argparse.ArgumentTypeError("must be true or false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="local client for Alibaba Cloud support tickets")
    parser.add_argument("--home", type=Path, default=default_home(), help="local rule cache directory")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="check the local runtime conditions")

    self_update_parser = commands.add_parser("self-update", help="manage the client self-update").add_subparsers(
        dest="self_update_command", required=True
    )
    self_update_parser.add_parser("status", help="show the client self-update status")
    self_update_command = self_update_parser.add_parser("update", help="check and update the client from the pinned GitHub source")
    self_update_command.add_argument("--force", action="store_true", help="ignore the seven-day check interval")

    rules = commands.add_parser("rules", help="manage the public rule cache").add_subparsers(dest="rules_command", required=True)
    rules.add_parser("status", help="show the local rule status")
    update = rules.add_parser("update", help="update rules in the fixed GitHub-then-OSS order")
    update.add_argument(
        "--oss-url",
        help="public OSS bucket root HTTPS address; takes precedence over environment variables and the built-in source, an empty string disables OSS",
    )
    update.add_argument(
        "--oss-prefix",
        help="OSS object root prefix; takes precedence over environment variables and the built-in empty prefix",
    )
    update.add_argument("--force", action="store_true", help="ignore the seven-day rule check interval")

    match = commands.add_parser("match", help="match the product issue type")
    match.add_argument("--input", default="-", help="problem text file; - means standard input")
    match.add_argument("--product", help="optional product name or alias")

    draft = commands.add_parser("draft", help="validate the collected fields and build a redacted draft")
    draft.add_argument("--input", required=True, help="case JSON file; - means standard input")

    catalog = commands.add_parser("catalog", help="query products and categories dynamically").add_subparsers(dest="catalog_command", required=True)
    products = catalog.add_parser("products", help="query products that accept tickets")
    products.add_argument("--name")
    products.add_argument("--language", choices=["zh", "en", "jp"], default="zh")
    categories = catalog.add_parser("categories", help="query the issue categories of a product")
    categories.add_argument("--product-id", type=int, required=True)
    categories.add_argument("--name")
    categories.add_argument("--language", choices=["zh", "en", "jp"], default="zh")

    ticket = commands.add_parser("ticket", help="manage tickets").add_subparsers(dest="ticket_command", required=True)
    get_ticket = ticket.add_parser("get", help="query a ticket")
    get_ticket.add_argument("--ticket-id", required=True)

    list_ticket = ticket.add_parser("list", help="query recent tickets with pagination")
    list_ticket.add_argument("--days", type=int, default=30, help="how many recent days to query, 30 by default")
    list_ticket.add_argument("--page-number", type=int, default=1)
    list_ticket.add_argument("--page-size", type=int, default=20)
    list_ticket.add_argument("--keyword", help="fuzzy match on the ticket content")
    list_ticket.add_argument("--ticket-id", help="filter by ticket id")

    for name, help_text in (("preview-create", "preview the ticket creation and issue a confirmation token"), ("create", "create the ticket")):
        create = ticket.add_parser(name, help=help_text)
        create.add_argument("--category-id", required=True)
        create.add_argument("--severity", type=int, choices=[1, 2], default=1)
        create.add_argument("--title", required=True)
        create.add_argument("--content-file", required=True, help="content file; - means standard input")
        if name == "create":
            create.add_argument("--confirmation-token", help="the confirmation token returned by preview-create")

    for name, help_text in (("preview-reply", "preview the reply and issue a confirmation token"), ("reply", "reply to the ticket")):
        reply = ticket.add_parser(name, help=help_text)
        reply.add_argument("--ticket-id", required=True)
        reply.add_argument("--content-file", required=True, help="reply file; - means standard input")
        if name == "reply":
            reply.add_argument("--confirmation-token", help="the confirmation token returned by preview-reply")

    for name, help_text in (("preview-evaluate", "preview the evaluation and issue a confirmation token"), ("evaluate", "evaluate the ticket")):
        evaluate = ticket.add_parser(name, help=help_text)
        evaluate.add_argument("--ticket-id", required=True)
        evaluate.add_argument("--score", type=int, choices=range(1, 6), required=True, help="1 to 5 stars")
        evaluate.add_argument("--solved", type=parse_cli_boolean, required=True, help="whether the issue is resolved: true or false")
        evaluate.add_argument("--content-file", help="optional evaluation content file; - means standard input")
        if name == "evaluate":
            evaluate.add_argument("--confirmation-token", help="the confirmation token returned by preview-evaluate")

    for name, help_text in (("preview-close", "preview the close operation and issue a confirmation token"), ("close", "close the ticket")):
        close = ticket.add_parser(name, help=help_text)
        close.add_argument("--ticket-id", required=True)
        if name == "close":
            close.add_argument("--confirmation-token", help="the confirmation token returned by preview-close")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.home = args.home.expanduser().resolve()
    try:
        best_effort_client_recovery(args.home)
        if args.command == "doctor":
            result = command_doctor(args)
        elif args.command == "self-update":
            result = (
                self_update_status(args.home)
                if args.self_update_command == "status"
                else self_update(args.home, force=args.force)
            )
        elif args.command == "rules":
            result = rules_status(args.home) if args.rules_command == "status" else update_rules(args)
        elif args.command == "match":
            result = command_match(args)
        elif args.command == "draft":
            result = command_draft(args)
        elif args.command == "catalog":
            result = command_catalog(args)
        elif args.command == "ticket":
            result = command_ticket(args)
        else:
            parser.error("unknown command")
            return 2
        emit({"success": True, "data": result})
        return 0
    except ClientError as exc:
        emit({"success": False, "error": str(exc)})
        return 1
    except KeyboardInterrupt:
        emit({"success": False, "error": "the operation was cancelled"})
        return 130


# The version gate is verified at import time, once every helper it uses exists,
# so a broken references/manifest.json contract fails loudly before any cloud call.
_selfcheck_skill_version()
_selfcheck_bind_create_request_marker()


if __name__ == "__main__":
    raise SystemExit(main())
