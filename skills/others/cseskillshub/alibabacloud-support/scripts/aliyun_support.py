#!/usr/bin/env python3
"""Local client for the alibabacloud-support Agent Skill."""

from __future__ import annotations

import argparse
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
import time
import unicodedata
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Iterable, Optional

APP_NAME = "alibabacloud-support"
VERSION = "1.8.0"
API_VERSION = "2021-06-10"
# Workorder is invoked through the aliyun CLI in plugin mode (lowercase-hyphenated),
# never the PascalCase generic-RPC form, which aliyun CLI 3.3+/3.4 rejects with
# "unchecked version" for Workorder.
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
# API request parameter whose CLI flag name is not the plain kebab-case form.
WORKORDER_PLUGIN_PARAM_OVERRIDES = {"Language": "biz-language"}
USER_AGENT_PREFIX = f"AlibabaCloud-Agent-Skills/{APP_NAME}"
USER_AGENT_ENVS = ("ALIBABACLOUD_USER_AGENT", "ALIBABA_CLOUD_USER_AGENT")
# The User-Agent skill-version is sourced from references/manifest.json at first
# cloud call. SESSION_ID is a 32-hex string reused across child processes via
# SKILL_SESSION_ID so nested CLI invocations correlate to one assistant turn.
_SKILL_VERSION_SOURCE = "references/manifest.json"
_SESSION_ID_ENV = "SKILL_SESSION_ID"
_skill_version_cache: Optional[str] = None


def session_id() -> str:
    existing = os.environ.get(_SESSION_ID_ENV, "")
    if re.fullmatch(r"[0-9a-fA-F]{32}", existing or ""):
        return existing.lower()
    generated = uuid.uuid4().hex
    os.environ[_SESSION_ID_ENV] = generated
    return generated


def user_agent_skill_version() -> str:
    global _skill_version_cache
    if _skill_version_cache is not None:
        return _skill_version_cache
    manifest = skill_root() / _SKILL_VERSION_SOURCE
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        declared = str(data.get("version", "")).strip()
    except (OSError, ValueError, AttributeError):
        raise ClientError(
            f"{_SKILL_VERSION_SOURCE} is unreadable; the User-Agent skill-version "
            "is never guessed"
        )
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.]+)?", declared or "") is None:
        raise ClientError(
            f"{_SKILL_VERSION_SOURCE} declares no valid semantic version (got {declared!r}); "
            "the User-Agent skill-version is never guessed"
        )
    if declared != VERSION:
        raise ClientError(
            f"{_SKILL_VERSION_SOURCE} version {declared} disagrees with the script VERSION {VERSION}"
        )
    _skill_version_cache = declared
    return declared


def build_user_agent() -> str:
    return (
        f"{USER_AGENT_PREFIX}/{session_id()} "
        f"skill-version/{user_agent_skill_version()}"
    )


def cli_environment() -> dict:
    env = os.environ.copy()
    rendered = build_user_agent()
    for name in USER_AGENT_ENVS:
        env[name] = rendered
    return env


def flag_name(api_param: str) -> str:
    override = WORKORDER_PLUGIN_PARAM_OVERRIDES.get(api_param)
    if override:
        return override
    return re.sub(r"(?<!^)(?=[A-Z])", "-", api_param).lower()

DEFAULT_ENDPOINT = "workorder.aliyuncs.com"
DEFAULT_REGION = "cn-hangzhou"
TICKET_TITLE_PREFIX = "[aliyun-support]"
CLI_PATH_ENV = "ALIBABACLOUD_SUPPORT_CLI_PATH"
CLI_ENCODING_ENV = "ALIBABACLOUD_SUPPORT_CLI_ENCODING"
CLI_INSTALL_DOC_URL = "https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli"
CLI_CREDENTIAL_DOC_URL = "https://help.aliyun.com/zh/cli/configure-credentials/"
CLI_BLOCKED_CAPABILITIES = (
    "catalog",
    "match",
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
    "match": ("ListProducts", "ListCategories"),
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
CONFIRMATION_TTL_SECONDS = 30 * 60
CREATE_RECONCILIATION_CLOCK_SKEW_MS = 60 * 1000
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_FILES = 500
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024
MANIFEST_SCHEMA_VERSION = 1
TERMINAL_STATUS_VALUES = {"6", "closed", "resolved", "confirmed"}
TERMINAL_STATUS_LABELS = {"\u5df2\u5173\u95ed", "\u5f85\u4f60\u8bc4\u4ef7", "\u5df2\u5b8c\u6210"}
TICKET_WEB_URL_TEMPLATE = "https://smartservice.console.aliyun.com/service/ticket-detail?ticketId={ticket_id}"
RULE_PATH_PATTERN = re.compile(r"products/[a-z0-9][a-z0-9_-]*\.json")

PRODUCT_KEYS = {"product", "aliases", "issueTypes"}
ISSUE_KEYS = {"name", "keywords", "categoryKeywords", "categoryHints", "collect"}
FIELD_KEYS = {"field", "label", "required", "type", "description", "example", "enum", "maxLength"}
FORBIDDEN_KEY_PARTS = {
    "command", "shell", "script", "sql", "regex", "pattern", "url", "endpoint", "collector",
    "accesskeysecret", "secretaccesskey", "clientsecret", "apikey", "password", "passwd",
    "privatekey", "secret",
}
FORBIDDEN_COLLECTION_FIELD_NAMES = {
    "accesskeysecret", "secretaccesskey", "apikey", "clientsecret", "password", "passwd",
    "privatekey", "secret", "secretkey",
}
FORBIDDEN_COLLECTION_FIELD_PARTS = {
    "accesskeysecret", "clientsecret", "password", "passwd", "privatekey", "secretaccesskey",
}
SENSITIVE_COLLECTION_LABEL_PATTERN = re.compile(
    r"(?:\u5bc6\u7801|\u53e3\u4ee4|\u79c1\u94a5|\u5bc6\u94a5|access[\s_-]*key[\s_-]*secret|secret[\s_-]*access[\s_-]*key|client[\s_-]*secret|private[\s_-]*key|api[\s_-]*key|pass[\s_-]*word|passwd)",
    re.I,
)
SENSITIVE_COLLECTION_TEXT_PATTERN = re.compile(
    r"(?:\u5bc6\u7801|\u53e3\u4ee4|\u79c1\u94a5|\u5bc6\u94a5|access[\s_-]*key[\s_-]*secret|secret[\s_-]*access[\s_-]*key|client[\s_-]*secret|private[\s_-]*key|api[\s_-]*key|pass[\s_-]*word|passwd)",
    re.I,
)
SENSITIVE_COLLECTION_FIELD_PARTS = (
    "accesskeysecret", "secretaccesskey", "apikey", "clientsecret", "password", "passwd", "privatekey",
)
COLLECTION_ACTION_PATTERN = re.compile(
    r"(?:\u586b\u5199|\u63d0\u4f9b|\u8f93\u5165|\u63d0\u4ea4|\u7c98\u8d34|\u4e0a\u4f20|\u53d1\u9001|fill|provide|enter|submit|paste|upload|send)", re.I,
)
UNSAFE_VALUE_MARKER_PATTERN = re.compile(
    r"(?:\u5b8c\u6574|\u5168\u90e8|\u5168\u91cf|\u6240\u6709(?:\u5b57\u7b26|\u5185\u5bb9)|\u539f\u59cb|\u539f\u503c|\u660e\u6587|\u672a\u7ecf\u8131\u654f|\u672a\u8131\u654f|\u5b9e\u9645\u503c|\u771f\u5b9e\u503c|\u672c\u8eab|full|raw|plain|cleartext|unmasked|unredacted)", re.I,
)
SAFE_COLLECTION_CREDENTIAL_FIELDS = {
    "apikeyprefix": ("\u524d\u7f00", "prefix"),
    "apikeytype": ("\u7c7b\u578b", "\u524d\u7f00", "type"),
}
SAFE_CREDENTIAL_REFERENCE_FIELDS = {
    "operationname": ("\u64cd\u4f5c\u540d\u79f0", "operation name"),
}
RULE_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:ENCRYPTED |RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(
        r"[\"']?(?:pass[\s_-]*word|passwd|private[\s_-]*key|access[\s_-]*key[\s_-]*secret|secret[\s_-]*access[\s_-]*key|client[\s_-]*secret|api[\s_-]*key|\u5bc6\u7801|\u53e3\u4ee4|\u79c1\u94a5|\u5bc6\u94a5)[\"']?\s*[\uff1a:=]\s*[\"']?\S+",
        re.I,
    ),
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}(?![A-Za-z0-9])", re.I),
]
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:ENCRYPTED |RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(
        r"[\"']?(?:authorization|cookie|pass(?:[\s_-])*word|passwd|access(?:[\s_-])*key(?:[\s_-])*secret|secret(?:[\s_-])*access(?:[\s_-])*key|api(?:[\s_-])*key|token|\u5bc6\u7801|\u5bc6\u94a5|\u4ee4\u724c|\u8ba4\u8bc1\u4fe1\u606f)[\"']?\s*[\uff1a:=]\s*[\"']?\S+",
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
    r"((?:\u963f\u91cc\u4e91)?(?:\u7528\u6237|\u5ba2\u6237|\u8d26\u53f7|\u8d26\u6237)\s*(?:UID|ID)|(?:\u963f\u91cc\u4e91)?UID|(?:user|customer|account)\s*id)\s*([\uff1a:=]\s*)(\d{8,32})",
    re.I,
)
URL_PATTERN = re.compile(r"https?://", re.I)
PROMPT_INJECTION_PATTERN = re.compile(
    r"(?:\u5ffd\u7565.{0,12}(?:\u6307\u4ee4|\u89c4\u5219)|\u6267\u884c.{0,8}(?:\u547d\u4ee4|\u811a\u672c)|(?:\u7ec8\u7aef|\u547d\u4ee4\u884c).{0,12}(?:\u8fd0\u884c|\u6267\u884c)|(?:\u8fd0\u884c|\u6267\u884c)\s*(?:uname|whoami|curl|wget|python3?|node|npm|npx|bash|sh|zsh|powershell|cmd)\b|system\s*prompt|run\s+(?:command|shell)|sudo\b|powershell\b|\$\(|`)",
    re.I,
)

DEFAULT_ISSUE = {
    "name": "\u901a\u7528\u95ee\u9898",
    "keywords": ["\u95ee\u9898", "\u5f02\u5e38", "\u62a5\u9519", "\u54a8\u8be2"],
    "categoryHints": [],
    "collect": [
        {
            "field": "regionId",
            "label": "\u5730\u57df",
            "required": False,
            "type": "string",
            "description": "\u6d89\u53ca\u5730\u57df\u5316\u8d44\u6e90\u65f6\u586b\u5199\u5730\u57df\u6807\u8bc6",
            "maxLength": 64,
        },
        {
            "field": "resourceId",
            "label": "\u8d44\u6e90\u6807\u8bc6",
            "required": False,
            "type": "string",
            "description": "\u6d89\u53ca\u5177\u4f53\u5b9e\u4f8b\u6216\u8d44\u6e90\u65f6\u586b\u5199\u8131\u654f\u540e\u7684\u8d44\u6e90\u6807\u8bc6",
            "maxLength": 120,
        },
        {
            "field": "occurrenceTime",
            "label": "\u53d1\u751f\u65f6\u95f4",
            "required": True,
            "type": "string",
            "description": "\u5305\u542b\u65e5\u671f\u3001\u65f6\u95f4\u548c\u65f6\u533a",
            "maxLength": 64,
        },
        {
            "field": "issueDescription",
            "label": "\u95ee\u9898\u63cf\u8ff0",
            "required": True,
            "type": "string",
            "description": "\u8bf4\u660e\u671f\u671b\u7ed3\u679c\u3001\u5b9e\u9645\u73b0\u8c61\u548c\u89e6\u53d1\u6761\u4ef6",
            "maxLength": 1000,
        },
        {
            "field": "errorCode",
            "label": "\u9519\u8bef\u7801",
            "required": False,
            "type": "string",
            "maxLength": 120,
        },
        {
            "field": "errorMessage",
            "label": "\u9519\u8bef\u4fe1\u606f",
            "required": False,
            "type": "string",
            "description": "\u586b\u5199\u5b8c\u6574\u9519\u8bef\u4fe1\u606f\u5e76\u79fb\u9664\u654f\u611f\u5185\u5bb9",
            "maxLength": 1000,
        },
        {
            "field": "requestId",
            "label": "\u8bf7\u6c42\u6807\u8bc6",
            "required": False,
            "type": "string",
            "description": "\u5b58\u5728\u8bf7\u6c42\u6807\u8bc6\u65f6\u586b\u5199",
            "maxLength": 120,
        },
        {
            "field": "environment",
            "label": "\u8fd0\u884c\u73af\u5883",
            "required": False,
            "type": "string",
            "description": "\u8bf4\u660e\u64cd\u4f5c\u7cfb\u7edf\u3001\u5ba2\u6237\u7aef\u3001SDK\u6216\u63a7\u5236\u53f0\u7b49\u73af\u5883\u53ca\u7248\u672c",
            "maxLength": 500,
        },
        {
            "field": "impactScope",
            "label": "\u5f71\u54cd\u8303\u56f4",
            "required": True,
            "type": "string",
            "description": "\u8bf4\u660e\u53d7\u5f71\u54cd\u4e1a\u52a1\u3001\u8d44\u6e90\u6570\u91cf\u3001\u7528\u6237\u8303\u56f4\u548c\u4e25\u91cd\u7a0b\u5ea6",
            "maxLength": 500,
        },
    ],
}

class ClientError(RuntimeError):
    """Expected validation, configuration, or API error."""


class ManifestValidationError(ClientError):
    """The bundled manifest or package structure is invalid."""


class DuplicateJsonKeyError(ValueError):
    """A JSON object contains a duplicate key."""


class WorkorderIndeterminateError(ClientError):
    """A non-idempotent Workorder call may have reached the service without a reliable result."""

    def __init__(self, action: str, reason: str):
        self.action = action
        self.reason = reason
        super().__init__(f"{action} {reason}\uff1b\u5199\u64cd\u4f5c\u7ed3\u679c\u53ef\u80fd\u4e0d\u660e\u786e\uff0c\u8bf7\u52ff\u81ea\u52a8\u91cd\u8bd5")


class WorkorderTimeoutError(WorkorderIndeterminateError):
    """Workorder call timed out and may have an indeterminate write result."""

    def __init__(self, action: str):
        super().__init__(action, "\u8c03\u7528\u8d85\u65f6")


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def default_home() -> Path:
    configured = os.environ.get("ALIBABACLOUD_SUPPORT_HOME")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / APP_NAME

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
        raise ClientError(f"{source} \u7f16\u7801\u65e0\u6cd5\u8bc6\u522b\uff1b\u5df2\u4e25\u683c\u5c1d\u8bd5\uff1a{', '.join(attempted)}")
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
            f"{CLI_ENCODING_ENV} \u4ec5\u652f\u6301 utf-8\u3001utf-8-sig\u3001gbk\u3001cp936 \u6216 gb18030"
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


def read_input(path_value: str, max_bytes: int = 1024 * 1024) -> str:
    try:
        if path_value == "-":
            binary_stdin = getattr(sys.stdin, "buffer", None)
            if binary_stdin is not None:
                raw = binary_stdin.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    raise ClientError(f"\u8f93\u5165\u5185\u5bb9\u8d85\u8fc7 {max_bytes} \u5b57\u8282\u9650\u5236")
                text = decode_external_bytes(raw, "\u6807\u51c6\u8f93\u5165")
            else:
                text = sys.stdin.read(max_bytes + 1)
        else:
            path = Path(path_value).expanduser()
            if path.stat().st_size > max_bytes:
                raise ClientError(f"\u8f93\u5165\u6587\u4ef6\u8d85\u8fc7 {max_bytes} \u5b57\u8282\u9650\u5236")
            text = path.read_text(encoding="utf-8")
    except ClientError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ClientError(f"\u65e0\u6cd5\u8bfb\u53d6\u8f93\u5165\uff1a{safe_error_text(str(exc))}") from exc
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeError as exc:
        raise ClientError("\u8f93\u5165\u5305\u542b\u65e0\u6cd5\u8f6c\u6362\u4e3a UTF-8 \u7684\u5b57\u7b26\uff1b\u8bf7\u6539\u7528 UTF-8 \u6587\u4ef6\u6216\u4e8c\u8fdb\u5236\u6807\u51c6\u8f93\u5165") from exc
    if encoded_size > max_bytes:
        raise ClientError(f"\u8f93\u5165\u5185\u5bb9\u8d85\u8fc7 {max_bytes} \u5b57\u8282\u9650\u5236")
    return text

def contains_rule_secret(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text)
    candidates = [normalized]
    for _ in range(2):
        decoded = urllib.parse.unquote(candidates[-1])
        if decoded == candidates[-1]:
            break
        candidates.append(decoded)
    return any(pattern.search(candidate) for candidate in candidates for pattern in RULE_SECRET_PATTERNS)


def reject_forbidden_content(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ClientError(f"\u89c4\u5219\u952e\u5fc5\u987b\u662f\u5b57\u7b26\u4e32\uff1a{path}")
            folded = normalize(key).replace("_", "").replace("-", "")
            if folded in FORBIDDEN_KEY_PARTS:
                raise ClientError(f"\u89c4\u5219\u5305\u542b\u7981\u6b62\u5b57\u6bb5\uff1a{path}.{key}")
            reject_forbidden_content(child, f"{path}.{key}")
    elif isinstance(value, list):
        if len(value) > 100:
            raise ClientError(f"\u89c4\u5219\u6570\u7ec4\u8fc7\u957f\uff1a{path}")
        for index, child in enumerate(value):
            reject_forbidden_content(child, f"{path}[{index}]")
    elif isinstance(value, str):
        normalized = unicodedata.normalize("NFKC", value)
        if len(normalized) > 500 or any(ord(char) < 32 and char not in "\t\n\r" for char in normalized):
            raise ClientError(f"\u89c4\u5219\u6587\u672c\u957f\u5ea6\u6216\u63a7\u5236\u5b57\u7b26\u4e0d\u5408\u6cd5\uff1a{path}")
        if URL_PATTERN.search(normalized):
            raise ClientError(f"\u89c4\u5219\u5185\u5bb9\u4e0d\u5f97\u5305\u542b URL\uff1a{path}")
        if contains_rule_secret(normalized):
            raise ClientError(f"\u89c4\u5219\u5185\u5bb9\u7591\u4f3c\u5305\u542b\u51ed\u636e\uff1a{path}")
        if PROMPT_INJECTION_PATTERN.search(normalized):
            raise ClientError(f"\u89c4\u5219\u5185\u5bb9\u7591\u4f3c\u5305\u542b\u6267\u884c\u6307\u4ee4\uff1a{path}")


def require_string(value: Any, name: str, max_length: int = 120) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClientError(f"{name} \u5fc5\u987b\u662f\u975e\u7a7a\u5b57\u7b26\u4e32")
    result = value.strip()
    if len(result) > max_length or "\n" in result or "\r" in result:
        raise ClientError(f"{name} \u8d85\u8fc7\u957f\u5ea6\u9650\u5236\u6216\u5305\u542b\u6362\u884c")
    return result


def require_string_list(value: Any, name: str, max_items: int = 100, max_length: int = 120) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > max_items:
        raise ClientError(f"{name} \u5fc5\u987b\u662f 1-{max_items} \u9879\u5b57\u7b26\u4e32\u6570\u7ec4")
    result = [require_string(item, f"{name}[]", max_length) for item in value]
    if len({normalize(item) for item in result}) != len(result):
        raise ClientError(f"{name} \u5305\u542b\u91cd\u590d\u503c")
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
        raise ClientError(f"\u89c4\u5219\u4e0d\u5f97\u91c7\u96c6\u51ed\u636e\u6216\u79d8\u5bc6\u5b57\u6bb5\uff1a{location}.field")

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
        raise ClientError(f"\u89c4\u5219\u4e0d\u5f97\u91c7\u96c6\u51ed\u636e\u6216\u79d8\u5bc6\u5b57\u6bb5\uff1a{location}.field")
    if UNSAFE_VALUE_MARKER_PATTERN.search(combined_text):
        raise ClientError(f"\u89c4\u5219\u4e0d\u5f97\u8981\u6c42\u63d0\u4ea4\u51ed\u636e\u539f\u503c\uff1a{location}")
    if not any(term in label_text for term in safe_terms):
        raise ClientError(f"\u51ed\u636e\u5143\u6570\u636e\u6807\u7b7e\u4e0e\u5b57\u6bb5\u8bed\u4e49\u4e0d\u4e00\u81f4\uff1a{location}.label")
    if field_description is not None:
        description_text = next(text for text_name, text in texts if text_name == "description")
        if not any(term in description_text for term in safe_terms):
            raise ClientError(f"\u51ed\u636e\u5143\u6570\u636e\u8bf4\u660e\u4e0e\u5b57\u6bb5\u8bed\u4e49\u4e0d\u4e00\u81f4\uff1a{location}.description")
    if field_example is not None:
        raise ClientError(f"\u51ed\u636e\u5143\u6570\u636e\u5b57\u6bb5\u4e0d\u5f97\u63d0\u4f9b\u793a\u4f8b\u503c\uff1a{location}.example")


def validate_product_rule(data: Any, source: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ClientError(f"\u4ea7\u54c1\u89c4\u5219\u5fc5\u987b\u662f\u5bf9\u8c61\uff1a{source}")
    unknown = set(data) - PRODUCT_KEYS
    if unknown:
        raise ClientError(f"\u4ea7\u54c1\u89c4\u5219\u5305\u542b\u672a\u77e5\u5b57\u6bb5\uff1a{source}\uff1a{sorted(unknown)}")
    product = require_string(data.get("product"), f"{source}.product", 64)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", product):
        raise ClientError(f"{source}.product \u5fc5\u987b\u662f\u7a33\u5b9a\u7684\u4ea7\u54c1\u6807\u8bc6")
    aliases_value = data.get("aliases", [])
    if not isinstance(aliases_value, list) or len(aliases_value) > 30:
        raise ClientError(f"{source}.aliases \u5fc5\u987b\u662f 0-30 \u9879\u5b57\u7b26\u4e32\u6570\u7ec4")
    aliases = [require_string(item, f"{source}.aliases[]", 64) for item in aliases_value]
    if len({normalize(item) for item in aliases}) != len(aliases):
        raise ClientError(f"{source}.aliases \u5305\u542b\u91cd\u590d\u503c")
    issue_types = data.get("issueTypes")
    if not isinstance(issue_types, list) or not issue_types or len(issue_types) > 100:
        raise ClientError(f"{source}.issueTypes \u5fc5\u987b\u662f 1-100 \u9879\u6570\u7ec4")

    seen_issue_names: set[str] = set()
    for index, issue in enumerate(issue_types):
        location = f"{source}.issueTypes[{index}]"
        if not isinstance(issue, dict):
            raise ClientError(f"{location} \u5fc5\u987b\u662f\u5bf9\u8c61")
        unknown_issue = set(issue) - ISSUE_KEYS
        if unknown_issue:
            raise ClientError(f"{location} \u5305\u542b\u672a\u77e5\u5b57\u6bb5\uff1a{sorted(unknown_issue)}")
        issue_name = require_string(issue.get("name"), f"{location}.name", 80)
        folded_name = normalize(issue_name)
        if folded_name in seen_issue_names:
            raise ClientError(f"{source} \u5305\u542b\u91cd\u590d\u95ee\u9898\u7c7b\u578b\uff1a{issue_name}")
        seen_issue_names.add(folded_name)
        require_string_list(issue.get("keywords", []), f"{location}.keywords", 50, 80)
        if "categoryKeywords" in issue:
            require_string_list(issue["categoryKeywords"], f"{location}.categoryKeywords", 30, 80)
        if "categoryHints" in issue:
            require_string_list(issue["categoryHints"], f"{location}.categoryHints", 30, 80)
        collect = issue.get("collect")
        if not isinstance(collect, list) or not collect or len(collect) > 50:
            raise ClientError(f"{location}.collect \u5fc5\u987b\u662f 1-50 \u9879\u6570\u7ec4")
        seen_fields: set[str] = set()
        for field_index, field in enumerate(collect):
            field_location = f"{location}.collect[{field_index}]"
            if not isinstance(field, dict):
                raise ClientError(f"{field_location} \u5fc5\u987b\u662f\u5bf9\u8c61")
            unknown_field = set(field) - FIELD_KEYS
            if unknown_field:
                raise ClientError(f"{field_location} \u5305\u542b\u672a\u77e5\u5b57\u6bb5\uff1a{sorted(unknown_field)}")
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
                raise ClientError(f"\u91c7\u96c6\u5b57\u6bb5\u540d\u4e0d\u5408\u6cd5\uff1a{field_name}")
            if field_name in seen_fields:
                raise ClientError(f"{location} \u5305\u542b\u91cd\u590d\u91c7\u96c6\u5b57\u6bb5\uff1a{field_name}")
            seen_fields.add(field_name)
            if "required" in field and not isinstance(field["required"], bool):
                raise ClientError(f"{field_location}.required \u5fc5\u987b\u662f\u5e03\u5c14\u503c")
            field_type = field.get("type", "string")
            if not isinstance(field_type, str) or field_type not in {"string", "integer", "number", "boolean", "array"}:
                raise ClientError(f"{field_location}.type \u4e0d\u53d7\u652f\u6301")
            if "enum" in field and (not isinstance(field["enum"], list) or not field["enum"]):
                raise ClientError(f"{field_location}.enum \u5fc5\u987b\u662f\u975e\u7a7a\u6570\u7ec4")
            if "maxLength" in field and (
                not isinstance(field["maxLength"], int)
                or isinstance(field["maxLength"], bool)
                or field["maxLength"] < 1
            ):
                raise ClientError(f"{field_location}.maxLength \u5fc5\u987b\u662f\u6b63\u6574\u6570")

    reject_forbidden_content(data, source)
    return data

class BundledRuleSet:
    def __init__(self, rules: list[dict[str, Any]], status: dict[str, Any]):
        self.rules = rules
        self.status = status


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(key)
        result[key] = value
    return result


def reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def parse_strict_json(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="strict")
    return json.loads(
        text,
        object_pairs_hook=unique_json_object,
        parse_constant=reject_json_constant,
    )


def bundled_manifest_digest(files: dict[str, dict[str, Any]]) -> str:
    canonical = bytearray()
    for relative in sorted(files, key=lambda value: value.encode("utf-8")):
        record = files[relative]
        canonical.extend(relative.encode("utf-8"))
        canonical.extend(b"\0")
        canonical.extend(str(record["size"]).encode("ascii"))
        canonical.extend(b"\0")
        canonical.extend(record["sha256"].encode("ascii"))
        canonical.extend(b"\n")
    return hashlib.sha256(bytes(canonical)).hexdigest()


def read_skill_version(root: Path) -> str:
    skill_path = root / "SKILL.md"
    try:
        metadata = skill_path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ManifestValidationError("manifest_invalid")
        raw = skill_path.read_bytes()
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ManifestValidationError("manifest_invalid")
        lines = raw.decode("utf-8", errors="strict").splitlines()
    except ManifestValidationError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ManifestValidationError("manifest_invalid") from exc
    if not lines or lines[0].strip() != "---":
        raise ManifestValidationError("manifest_invalid")
    try:
        closing = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ManifestValidationError("manifest_invalid") from exc
    versions = [
        line.split(":", 1)[1].strip().strip('"\'')
        for line in lines[1:closing]
        if re.fullmatch(r"version\s*:\s*.+", line.strip())
    ]
    if len(versions) != 1 or versions[0] != VERSION:
        raise ManifestValidationError("manifest_invalid")
    return versions[0]


def read_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "references/rules-manifest.json"
    try:
        metadata = manifest_path.lstat()
    except OSError as exc:
        raise ManifestValidationError("manifest_invalid") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ManifestValidationError("manifest_invalid")
    if metadata.st_size > MAX_MANIFEST_BYTES:
        raise ManifestValidationError("manifest_invalid")
    try:
        raw = manifest_path.read_bytes()
        manifest = parse_strict_json(raw)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        raise ManifestValidationError("manifest_invalid") from exc
    required = {"schemaVersion", "skillVersion", "contentDigest", "files"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ManifestValidationError("manifest_invalid")
    if type(manifest["schemaVersion"]) is not int or manifest["schemaVersion"] != MANIFEST_SCHEMA_VERSION:
        raise ManifestValidationError("manifest_invalid")
    if manifest["skillVersion"] != VERSION or read_skill_version(root) != VERSION:
        raise ManifestValidationError("manifest_invalid")
    content_digest = manifest["contentDigest"]
    if not isinstance(content_digest, str) or re.fullmatch(r"[0-9a-f]{64}", content_digest) is None:
        raise ManifestValidationError("manifest_invalid")
    files = manifest["files"]
    if not isinstance(files, dict) or not files or len(files) > MAX_FILES:
        raise ManifestValidationError("manifest_invalid")
    total_size = 0
    for relative, record in files.items():
        if not isinstance(relative, str) or RULE_PATH_PATTERN.fullmatch(relative) is None:
            raise ManifestValidationError("manifest_invalid")
        if not isinstance(record, dict) or set(record) != {"size", "sha256"}:
            raise ManifestValidationError("manifest_invalid")
        size = record["size"]
        digest = record["sha256"]
        if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES:
            raise ManifestValidationError("manifest_invalid")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ManifestValidationError("manifest_invalid")
        total_size += size
        if total_size > MAX_TOTAL_BYTES:
            raise ManifestValidationError("manifest_invalid")
    actual_digest = bundled_manifest_digest(files)
    if not hmac.compare_digest(actual_digest, content_digest):
        raise ManifestValidationError("manifest_invalid")
    products = root / "references/products"
    try:
        products_metadata = products.lstat()
    except OSError as exc:
        raise ManifestValidationError("manifest_invalid") from exc
    if stat.S_ISLNK(products_metadata.st_mode) or not stat.S_ISDIR(products_metadata.st_mode):
        raise ManifestValidationError("manifest_invalid")
    return manifest


def rejected_rule(key: str, reason_code: str) -> dict[str, str]:
    return {"key": key, "reasonCode": reason_code}


def load_manifest_rule(root: Path, relative: str, record: dict[str, Any]) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    path = (root / "references").joinpath(*relative.split("/"))
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None, "missing_file"
    except OSError:
        return None, "io_error"
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        return None, "unsafe_file_type"
    if metadata.st_size > MAX_FILE_BYTES:
        return None, "file_too_large"
    if metadata.st_size != record["size"]:
        return None, "size_mismatch"
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "io_error"
    if len(raw) != record["size"]:
        return None, "size_mismatch"
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), record["sha256"]):
        return None, "sha256_mismatch"
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None, "utf8_invalid"
    try:
        data = json.loads(
            text,
            object_pairs_hook=unique_json_object,
            parse_constant=reject_json_constant,
        )
    except DuplicateJsonKeyError:
        return None, "duplicate_json_key"
    except (json.JSONDecodeError, ValueError, RecursionError):
        return None, "json_invalid"
    try:
        return validate_product_rule(data, relative), None
    except (ClientError, RecursionError, TypeError, ValueError):
        return None, "schema_rejected"


def normalized_rule_identity(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).casefold().split())


def find_unlisted_json(root: Path, listed: set[str]) -> list[dict[str, str]]:
    rejected: list[dict[str, str]] = []
    products = root / "references/products"
    try:
        entries = list(products.iterdir())
    except OSError as exc:
        raise ManifestValidationError("manifest_invalid") from exc
    for entry in entries:
        if entry.name.casefold().endswith(".json"):
            relative = f"products/{entry.name}"
            if relative not in listed:
                rejected.append(rejected_rule(relative, "unlisted_rule"))
    return rejected


def invalid_bundled_rules() -> BundledRuleSet:
    return BundledRuleSet([], {
        "source": "bundled",
        "sourceType": "skill_package",
        "networkFetchDisabled": True,
        "skillVersion": VERSION,
        "contentDigest": None,
        "listedCount": 0,
        "acceptedCount": 0,
        "rejectedCount": 1,
        "rejectedFiles": [rejected_rule("rules-manifest.json", "manifest_invalid")],
        "usableCount": 0,
        "partial": False,
        "degraded": True,
        "manifestError": "manifest_invalid",
    })


def load_bundled_rules() -> BundledRuleSet:
    root = skill_root()
    try:
        manifest = read_manifest(root)
        files: dict[str, dict[str, Any]] = manifest["files"]
        rejected = find_unlisted_json(root, set(files))
    except ManifestValidationError:
        return invalid_bundled_rules()

    accepted: list[tuple[str, dict[str, Any]]] = []
    for relative in sorted(files, key=lambda value: value.encode("utf-8")):
        rule, reason = load_manifest_rule(root, relative, files[relative])
        if reason is not None:
            rejected.append(rejected_rule(relative, reason))
        elif rule is not None:
            accepted.append((relative, rule))

    owners: dict[str, set[str]] = {}
    for relative, rule in accepted:
        for name in [rule["product"], *rule["aliases"]]:
            owners.setdefault(normalized_rule_identity(name), set()).add(relative)
    conflicts: set[str] = set()
    for participants in owners.values():
        if len(participants) > 1:
            conflicts.update(participants)
    if conflicts:
        rejected.extend(rejected_rule(relative, "product_alias_conflict") for relative in conflicts)
        accepted = [(relative, rule) for relative, rule in accepted if relative not in conflicts]

    rejected.sort(key=lambda item: (item["key"].encode("utf-8"), item["reasonCode"]))
    rules = [rule for _, rule in accepted]
    accepted_count = len(rules)
    rejected_count = len(rejected)
    status = {
        "source": "bundled",
        "sourceType": "skill_package",
        "networkFetchDisabled": True,
        "skillVersion": VERSION,
        "contentDigest": manifest["contentDigest"],
        "listedCount": len(files),
        "acceptedCount": accepted_count,
        "rejectedCount": rejected_count,
        "rejectedFiles": rejected,
        "usableCount": accepted_count,
        "partial": bool(accepted_count and rejected_count),
        "degraded": accepted_count != len(files) or bool(rejected),
        "manifestError": None,
    }
    return BundledRuleSet(rules, status)


def category_key(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).casefold().split())


def category_identifier(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ClientError(f"{name} \u5fc5\u987b\u662f\u6574\u6570\u6216\u5341\u8fdb\u5236\u5b57\u7b26\u4e32")
    if isinstance(value, str):
        if not re.fullmatch(r"[0-9]+", value):
            raise ClientError(f"{name} \u5fc5\u987b\u662f 0..99999999999 \u7684\u5341\u8fdb\u5236 ID")
        digits = value.lstrip("0") or "0"
        if len(digits) > 11:
            raise ClientError(f"{name} \u8d85\u51fa 0..99999999999 \u8303\u56f4")
        value = int(digits)
    if not 0 <= value <= 99999999999:
        raise ClientError(f"{name} \u8d85\u51fa 0..99999999999 \u8303\u56f4")
    return value


def category_name(value: Any, name: str) -> str:
    if not isinstance(value, str) or not category_key(value):
        raise ClientError(f"{name} \u5fc5\u987b\u662f\u975e\u7a7a\u540d\u79f0")
    if len(value) > 120 or any(unicodedata.category(char).startswith("C") for char in value):
        raise ClientError(f"{name} \u540d\u79f0\u957f\u5ea6\u6216\u63a7\u5236\u5b57\u7b26\u4e0d\u5408\u6cd5")
    if PROMPT_INJECTION_PATTERN.search(unicodedata.normalize("NFKC", value)):
        raise ClientError(f"{name} \u540d\u79f0\u5305\u542b\u6267\u884c\u6307\u4ee4")
    return redact_text(value)


def validate_category(value: Any) -> dict[str, Any]:
    """Validate local shape only; this is not an API verification claim."""
    fields = {"productId", "productName", "categoryId", "categoryName"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ClientError("category \u5fc5\u987b\u4ec5\u5305\u542b productId/productName/categoryId/categoryName \u56db\u5b57\u6bb5")
    return {
        "productId": category_identifier(value["productId"], "productId"),
        "productName": category_name(value["productName"], "productName"),
        "categoryId": category_identifier(value["categoryId"], "categoryId"),
        "categoryName": category_name(value["categoryName"], "categoryName"),
    }


def catalog_array(value: Any, wrapper: str, location: str) -> list[Any]:
    if isinstance(value, dict) and set(value) == {wrapper}:
        value = value[wrapper]
    if not isinstance(value, list):
        raise ClientError(f"{location} \u5fc5\u987b\u662f\u6570\u7ec4\u6216\u6807\u51c6 {wrapper}.{wrapper} \u5305\u88c5")
    return value


def catalog_data(response: Any, action: str) -> list[Any]:
    if not isinstance(response, dict) or response.get("Success") is not True or (
        response.get("Code") is not None and str(response["Code"]) not in {"0", "200"}
    ):
        raise ClientError(f"{action} \u54cd\u5e94\u6210\u529f\u72b6\u6001\u65e0\u6cd5\u9a8c\u8bc1")
    return catalog_array(response.get("Data"), "Data", f"{action}.Data")


def lookup_category(product_id: Any, category_id: Any) -> dict[str, Any]:
    product_id = category_identifier(product_id, "product-id")
    category_id = category_identifier(category_id, "category-id")
    products: dict[int, str] = {}
    for directory in catalog_data(workorder_call("ListProducts", {"Language": "zh"}), "ListProducts"):
        if not isinstance(directory, dict) or "ProductList" not in directory:
            raise ClientError("ListProducts directory \u7f3a\u5c11 ProductList \u6216\u7ed3\u6784\u9519\u8bef")
        for product in catalog_array(directory["ProductList"], "ProductList", "directory.ProductList"):
            if not isinstance(product, dict):
                raise ClientError("ListProducts product \u7ed3\u6784\u9519\u8bef")
            identifier = category_identifier(product.get("ProductId"), "ProductId")
            name = category_name(product.get("ProductName"), "ProductName")
            if identifier in products:
                raise ClientError("ListProducts \u5305\u542b\u91cd\u590d ProductId")
            products[identifier] = name
    if product_id not in products:
        raise ClientError("product-id \u4e0d\u5728\u771f\u5b9e ListProducts \u4ea7\u54c1\u76ee\u5f55\u4e2d")
    categories: dict[int, str] = {}
    response = workorder_call("ListCategories", {"ProductId": product_id, "Language": "zh"})
    for category in catalog_data(response, "ListCategories"):
        if not isinstance(category, dict):
            raise ClientError("ListCategories category \u7ed3\u6784\u9519\u8bef")
        identifier = category_identifier(category.get("CategoryId"), "CategoryId")
        name = category_name(category.get("CategoryName"), "CategoryName")
        if "ProductId" in category and category_identifier(category["ProductId"], "ProductId") != product_id:
            raise ClientError("ListCategories \u5206\u7c7b\u5f52\u5c5e\u4ea7\u54c1\u9519\u8bef")
        if identifier in categories:
            raise ClientError("ListCategories \u5305\u542b\u91cd\u590d CategoryId")
        categories[identifier] = name
    if category_id not in categories:
        raise ClientError("category-id \u4e0d\u5c5e\u4e8e\u6240\u9009\u4ea7\u54c1\u7684\u771f\u5b9e ListCategories \u5206\u7c7b\u76ee\u5f55")
    return {
        "productId": product_id,
        "productName": products[product_id],
        "categoryId": category_id,
        "categoryName": categories[category_id],
    }


def category_variants(value: str, product_names: Iterable[str]) -> set[str]:
    folded = category_key(value)
    variants = {folded}
    # Remove at most one whole, longest known prefix, never a character set or substring.
    for prefix in sorted({category_key(name) for name in product_names}, key=lambda item: (-len(item), item)):
        if not prefix or not folded.startswith(prefix):
            continue
        remainder = folded[len(prefix):]
        if not remainder:
            break
        if prefix[-1].isascii() and prefix[-1].isalnum() and remainder[0].isascii() and remainder[0].isalnum():
            continue
        variants.add(remainder)
        break
    return variants


def map_category_rule(
    rules: Iterable[dict[str, Any]], category: dict[str, Any],
) -> tuple[Optional[dict[str, Any]], dict[str, Any], bool, Optional[str]]:
    """Map exact catalog names to collection rules, never customer text or keywords."""
    product_found = False
    mappings: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for rule in rules:
        names = [rule["product"], *rule["aliases"]]
        if category_key(category["productName"]) not in {category_key(name) for name in names}:
            continue
        product_found = True
        variants = category_variants(category["categoryName"], names)
        for issue in rule["issueTypes"]:
            if any(variants & category_variants(name, names) for name in [issue["name"], *issue.get("categoryHints", [])]):
                mappings.append((rule, issue))
    if len(mappings) == 1:
        rule, issue = mappings[0]
        return rule, issue, True, None
    reason = "category_rule_ambiguous" if mappings else (
        "category_not_found" if product_found else "product_not_found"
    )
    return None, DEFAULT_ISSUE, False, reason


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
        raise ClientError("\u68c0\u6d4b\u5230\u5bc6\u7801\u3001\u4ee4\u724c\u3001AccessKey Secret\u3001Cookie\u3001Authorization \u6216\u79c1\u94a5\uff0c\u5df2\u963b\u6b62\u5904\u7406")
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
        raise ClientError(f"\u5b57\u6bb5“{field['label']}”\u7c7b\u578b\u5e94\u4e3a {expected}")
    if isinstance(value, str) and field.get("maxLength") and len(value) > field["maxLength"]:
        raise ClientError(f"\u5b57\u6bb5“{field['label']}”\u8d85\u8fc7\u957f\u5ea6\u9650\u5236")
    if "enum" in field and value not in field["enum"]:
        raise ClientError(f"\u5b57\u6bb5“{field['label']}”\u4e0d\u5728\u5141\u8bb8\u503c\u8303\u56f4\u5185")
    return value


def default_match_template(product: Optional[str], reason: str) -> dict[str, Any]:
    return {
        "product": product,
        "issueType": DEFAULT_ISSUE["name"],
        "collectionRuleIssueType": DEFAULT_ISSUE["name"],
        "ruleMatched": False,
        "fallbackReason": reason,
        "categoryHints": [],
        "collect": [dict(field) for field in DEFAULT_ISSUE["collect"] if not is_user_identity_field(field)],
    }


def format_value(value: Any) -> str:
    if isinstance(value, list):
        return "\uff1b".join(str(item) for item in value)
    if isinstance(value, bool):
        return "\u662f" if value else "\u5426"
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
    return bool(re.search(r"(?:\u7528\u6237|\u5ba2\u6237|\u4e91\u8d26\u53f7|\u4e3b\u8d26\u53f7|\u5b50\u8d26\u53f7|\u8d26\u6237|\u8d26\u53f7).{0,8}(?:uid|id|\u6807\u8bc6)|\u8eab\u4efd\u8bc1", label, re.I))


def suggested_collection_field(field: dict[str, Any]) -> dict[str, str]:
    result = {"field": field["field"], "label": field["label"]}
    for key in ("description", "example"):
        value = field.get(key)
        if isinstance(value, str) and value:
            result[key] = value
    return result


def create_draft(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ClientError("\u8349\u7a3f\u8f93\u5165\u5fc5\u987b\u662f JSON \u5bf9\u8c61")
    category = validate_category(payload["category"]) if "category" in payload else None
    if category is not None:
        product = category["productName"]
        issue_type = category["categoryName"]
        _, issue, rule_matched, fallback_reason = map_category_rule(load_bundled_rules().rules, category)
    else:
        product = redact_text(require_string(payload.get("product", "\u672a\u6307\u5b9a\u4ea7\u54c1"), "product"))
        issue_type = redact_text(require_string(payload.get("issueType", DEFAULT_ISSUE["name"]), "issueType"))
        issue, rule_matched, fallback_reason = DEFAULT_ISSUE, False, "category_missing"
    summary = require_string(payload.get("summary"), "summary")
    requested_impact = payload.get("impact")
    steps = payload.get("stepsTried", [])
    values = payload.get("values", {})
    if not isinstance(values, dict):
        raise ClientError("values \u5fc5\u987b\u662f\u5bf9\u8c61")
    if not isinstance(steps, list) or not all(isinstance(item, str) for item in steps):
        raise ClientError("stepsTried \u5fc5\u987b\u662f\u5b57\u7b26\u4e32\u6570\u7ec4")

    resolved_issue_type = issue_type if category is not None else issue["name"]
    impact = requested_impact if requested_impact not in (None, "") else "\u672a\u8bf4\u660e"
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
            raise ClientError(f"\u5b57\u6bb5“{field['label']}”\u5305\u542b\u7981\u6b62\u63d0\u4ea4\u7684\u654f\u611f\u4fe1\u606f")
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
        "[\u95ee\u9898\u6982\u8ff0]",
        safe_summary,
        "",
        "[\u4ea7\u54c1\u4e0e\u95ee\u9898\u7c7b\u578b]",
        f"- \u4ea7\u54c1\uff1a{product}",
        f"- \u95ee\u9898\u7c7b\u578b\uff1a{resolved_issue_type}",
        "",
        "[\u5f71\u54cd\u8303\u56f4]",
        safe_impact,
        "",
        "[\u91c7\u96c6\u4fe1\u606f]",
    ]
    if collected:
        lines.extend(f"- {label}\uff1a{value}" for label, value in collected)
    else:
        lines.append("- \u672a\u63d0\u4f9b")
    lines.extend(["", "[\u5df2\u5c1d\u8bd5\u64cd\u4f5c]"])
    lines.extend(f"- {item}" for item in safe_steps) if safe_steps else lines.append("- \u672a\u8bf4\u660e")
    draft = "\n".join(lines).strip()
    if len(draft) > 20000:
        raise ClientError("\u5de5\u5355\u8349\u7a3f\u8d85\u8fc7 20000 \u5b57\u7b26\uff0c\u8bf7\u7cbe\u7b80\u540e\u91cd\u8bd5")
    return {
        "ready": True,
        "product": product,
        "issueType": resolved_issue_type,
        "requestedIssueType": issue_type,
        "collectionRuleIssueType": issue["name"],
        "category": category,
        "ruleMatched": rule_matched,
        "fallbackReason": fallback_reason,
        "categoryHints": issue.get("categoryHints", []),
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
            f"\u672a\u627e\u5230\u963f\u91cc\u4e91 CLI\uff1b\u8bf7\u5b89\u88c5\u540e\u5237\u65b0 PATH\uff0c\u6216\u901a\u8fc7 {CLI_PATH_ENV} \u6307\u5411 aliyun \u53ef\u6267\u884c\u6587\u4ef6"
        )
    return executable


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
        return "\u547d\u4ee4\u8fd4\u56de\u5185\u5bb9\u5305\u542b\u654f\u611f\u4fe1\u606f\uff0c\u5df2\u9690\u85cf"


def decode_process_stream(value: Any, source: str) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return decode_cli_bytes(value, source)
    raise ClientError(f"{source} \u7c7b\u578b\u65e0\u6548\uff1a{type(value).__name__}")


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
    stdout = decode_process_stream(completed.stdout, "\u963f\u91cc\u4e91 CLI \u6807\u51c6\u8f93\u51fa")
    stderr = decode_process_stream(completed.stderr, "\u963f\u91cc\u4e91 CLI \u6807\u51c6\u9519\u8bef")
    return completed.returncode, stdout, stderr


def workorder_call(action: str, params: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    plugin_command = WORKORDER_PLUGIN_COMMANDS.get(action)
    if not plugin_command:
        raise ClientError(f"unsupported Workorder operation: {action}")
    serialized_params = json.dumps(params, ensure_ascii=False, separators=(",", ":"))
    if contains_secret(serialized_params):
        raise ClientError(f"{action} \u8bf7\u6c42\u53c2\u6570\u7591\u4f3c\u5305\u542b\u51ed\u636e\uff0c\u5df2\u963b\u6b62\u8c03\u7528")
    command = [
        cli_executable(),
        "workorder",
        plugin_command,
        "--region",
        os.environ.get("ALIBABA_CLOUD_REGION_ID", DEFAULT_REGION),
        "--retry-count",
        "0",
        "--connect-timeout",
        "10",
        "--read-timeout",
        str(timeout),
        "--user-agent",
        build_user_agent(),
        *parameter_args(params),
    ]
    is_non_idempotent = action in NON_IDEMPOTENT_WORKORDER_ACTIONS
    try:
        returncode, stdout, stderr = run_cli_process(command, timeout)
    except KeyboardInterrupt as exc:
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, "\u6267\u884c\u671f\u95f4\u88ab\u7528\u6237\u4e2d\u65ad") from exc
        raise
    except subprocess.TimeoutExpired as exc:
        if is_non_idempotent:
            raise WorkorderTimeoutError(action) from exc
        raise ClientError(f"{action} \u8c03\u7528\u8d85\u65f6") from exc
    except ClientError as exc:
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, "CLI \u8f93\u51fa\u65e0\u6cd5\u53ef\u9760\u89e3\u7801") from exc
        raise
    except OSError as exc:
        raise ClientError(f"{action} \u65e0\u6cd5\u542f\u52a8\u963f\u91cc\u4e91 CLI\uff1a{safe_error_text(str(exc))}") from exc

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
            raise ClientError(f"{action} \u672a\u6210\u529f\uff1a{json.dumps(summary, ensure_ascii=False)}")
        detail = safe_error_text(stderr or stdout)
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, f"CLI \u5f02\u5e38\u9000\u51fa\uff08\u9000\u51fa\u7801 {returncode}\uff09\uff1a{detail}")
        raise ClientError(f"{action} \u8c03\u7528\u5931\u8d25\uff08\u9000\u51fa\u7801 {returncode}\uff09\uff1a{detail}")
    if response_error is not None:
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, "\u8fd4\u56de\u5185\u5bb9\u4e0d\u662f\u53ef\u9a8c\u8bc1\u7684 JSON") from response_error
        raise ClientError(f"{action} \u8fd4\u56de\u975e JSON \u5185\u5bb9\uff1a{safe_error_text(stdout)}") from response_error
    if not isinstance(response, dict):
        if is_non_idempotent:
            raise WorkorderIndeterminateError(action, "\u8fd4\u56de\u7ed3\u6784\u65e0\u6cd5\u9a8c\u8bc1")
        raise ClientError(f"{action} \u8fd4\u56de\u7ed3\u6784\u65e0\u6548")
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
                f"\u54cd\u5e94\u6210\u529f\u72b6\u6001\u65e0\u6cd5\u9a8c\u8bc1\uff1a{json.dumps(summary, ensure_ascii=False)}",
            )
        raise ClientError(f"{action} \u672a\u6210\u529f\uff1a{json.dumps(summary, ensure_ascii=False)}")
    # \u6210\u529f\u54cd\u5e94\u539f\u6837\u8fd4\u56de\uff1a\u5de5\u7a0b\u5e08\u56de\u590d\u7b49 API \u5185\u5bb9\u4e0d\u505a\u79d8\u5bc6\u62e6\u622a\uff0c\u786e\u4fdd\u53ef\u88ab\u5b8c\u6574\u91c7\u96c6\u3002
    # \u654f\u611f\u4fe1\u606f\u68c0\u67e5\u53ea\u4f5c\u7528\u4e8e\u5ba2\u6237\u53d1\u9001\u4fa7\uff08\u8bf7\u6c42\u53c2\u6570\u4e0e\u521b\u5efa/\u56de\u590d\u6b63\u6587\uff09\uff0c\u89c1\u4e0a\u65b9 contains_secret \u4e0e redact_text\u3002
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
        raise ClientError(f"\u65e0\u6cd5\u786e\u8ba4\u5de5\u5355 {ticket_id} \u7684\u5f53\u524d\u72b6\u6001\uff0c\u5df2\u505c\u6b62\u5199\u64cd\u4f5c")
    return {"value": value, "label": label}


def non_terminal_state(ticket_id: str) -> dict[str, str]:
    state = current_ticket_state(ticket_id)
    if normalize(state["value"]) in TERMINAL_STATUS_VALUES or state["label"] in TERMINAL_STATUS_LABELS:
        raise ClientError(f"\u5de5\u5355 {ticket_id} \u5df2\u5904\u4e8e\u7ec8\u6001\uff08{state['label'] or state['value']}\uff09\uff0c\u7981\u6b62\u7ee7\u7eed\u5199\u5165")
    return state


def ticket_url(ticket_id: str) -> str:
    return TICKET_WEB_URL_TEMPLATE.format(ticket_id=urllib.parse.quote(ticket_id, safe=""))


def ticket_list_data(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response.get("Data")
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ClientError("ListTickets \u8fd4\u56de\u7684\u5de5\u5355\u5217\u8868\u7ed3\u6784\u65e0\u6548")
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
        raise ClientError("days \u5fc5\u987b\u5728 1 \u5230 3650 \u4e4b\u95f4")
    if not 1 <= page_number <= 9_999_999:
        raise ClientError("page-number \u5fc5\u987b\u5728 1 \u5230 9999999 \u4e4b\u95f4")
    if not 10 <= page_size <= 100:
        raise ClientError("page-size \u5fc5\u987b\u5728 10 \u5230 100 \u4e4b\u95f4")
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
            raise ClientError("keyword \u4e0d\u80fd\u8d85\u8fc7 200 \u4e2a\u5b57\u7b26")
        params["Keyword"] = safe_keyword
    requested_ticket_id = getattr(args, "ticket_id", None)
    if requested_ticket_id:
        rendered_ticket_id = str(requested_ticket_id).strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", rendered_ticket_id):
            raise ClientError("ticket-id \u683c\u5f0f\u65e0\u6548")
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
            raise ClientError("\u8fd1\u671f\u5de5\u5355\u7ed3\u679c\u672a\u5b8c\u6574\u8fd4\u56de")
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
            "CreateTicket \u5199\u5165\u7ed3\u679c\u4e0d\u660e\u786e\uff0c\u4e14\u81ea\u52a8\u5bf9\u8d26\u88ab\u7528\u6237\u4e2d\u65ad\uff1b\u521b\u5efa\u7ed3\u679c\u4ecd\u4e0d\u786e\u5b9a\uff0c\u7981\u6b62\u81ea\u52a8\u91cd\u8bd5\uff0c"
            "\u8bf7\u901a\u8fc7 ticket list \u6216\u5de5\u5355\u63a7\u5236\u53f0\u4eba\u5de5\u6838\u5bf9"
        ) from exc
    except ClientError as exc:
        raise ClientError(
            "CreateTicket \u5199\u5165\u7ed3\u679c\u4e0d\u660e\u786e\uff0c\u4e14\u81ea\u52a8\u5bf9\u8d26\u5931\u8d25\uff1b\u521b\u5efa\u7ed3\u679c\u4ecd\u4e0d\u786e\u5b9a\uff0c\u7981\u6b62\u81ea\u52a8\u91cd\u8bd5\uff0c"
            f"\u8bf7\u901a\u8fc7 ticket list \u6216\u5de5\u5355\u63a7\u5236\u53f0\u4eba\u5de5\u6838\u5bf9\u3002\u5bf9\u8d26\u9519\u8bef\uff1a{safe_error_text(str(exc))}"
        ) from exc
    if len(verified) != 1:
        raise ClientError(
            "CreateTicket \u5199\u5165\u7ed3\u679c\u4e0d\u660e\u786e\uff0c\u81ea\u52a8\u5bf9\u8d26\u672a\u627e\u5230\u552f\u4e00\u4e14\u5b8c\u6574\u5339\u914d\u7684\u5de5\u5355\uff1b\u521b\u5efa\u7ed3\u679c\u4ecd\u4e0d\u786e\u5b9a\uff0c"
            "\u7981\u6b62\u81ea\u52a8\u91cd\u8bd5\uff0c\u8bf7\u901a\u8fc7 ticket list \u6216\u5de5\u5355\u63a7\u5236\u53f0\u4eba\u5de5\u6838\u5bf9"
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
        raise ClientError("score \u5fc5\u987b\u662f 1 \u5230 5 \u7684\u6574\u6570")
    if not isinstance(args.solved, bool):
        raise ClientError("solved \u5fc5\u987b\u662f true \u6216 false")
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
        raise ClientError("\u5199\u64cd\u4f5c\u7f3a\u5c11\u786e\u8ba4\u4ee4\u724c\uff1b\u8bf7\u5148\u6267\u884c\u5bf9\u5e94\u7684 preview \u547d\u4ee4\u5e76\u5411\u7528\u6237\u5c55\u793a\u5b8c\u6574\u8349\u7a3f")
    match = re.fullmatch(r"v1:([a-f0-9]{64})", provided)
    if not match:
        raise ClientError("\u786e\u8ba4\u4ee4\u724c\u683c\u5f0f\u65e0\u6548\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4")
    return match.group(1)


def issue_confirmation(
    home: Path,
    operation: str,
    payload: dict[str, Any],
    token_id: Optional[str] = None,
) -> str:
    resolved_token_id = token_id or new_confirmation_token_id()
    if not re.fullmatch(r"[a-f0-9]{64}", resolved_token_id):
        raise ClientError("\u786e\u8ba4\u4ee4\u724c\u6807\u8bc6\u65e0\u6548")
    directory = home / "confirmations" / "pending"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError as exc:
        raise ClientError(f"\u65e0\u6cd5\u4fdd\u62a4\u786e\u8ba4\u4ee4\u724c\u76ee\u5f55\uff1a{safe_error_text(str(exc))}") from exc
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
        raise ClientError(f"\u65e0\u6cd5\u4fdd\u5b58\u786e\u8ba4\u4ee4\u724c\uff1a{safe_error_text(str(exc))}") from exc
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
        raise ClientError("\u786e\u8ba4\u4ee4\u724c\u4e0d\u5b58\u5728\u6216\u5df2\u4f7f\u7528\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClientError("\u786e\u8ba4\u4ee4\u724c\u8bb0\u5f55\u65e0\u6548\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4") from exc
    expected = confirmation_digest(operation, payload)
    if (
        not isinstance(record, dict)
        or not isinstance(record.get("digest"), str)
        or not hmac.compare_digest(record["digest"], expected)
    ):
        raise ClientError("\u786e\u8ba4\u4ee4\u724c\u4e0e\u5f53\u524d\u5185\u5bb9\u6216\u5de5\u5355\u72b6\u6001\u4e0d\u4e00\u81f4\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4")
    expires_at = record.get("expiresAt")
    if not isinstance(expires_at, (int, float)) or isinstance(expires_at, bool) or time.time() > expires_at:
        raise ClientError("\u786e\u8ba4\u4ee4\u724c\u5df2\u8fc7\u671f\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4")

    consumed_dir = home / "confirmations" / "consumed"
    consumed_dir.mkdir(parents=True, exist_ok=True)
    try:
        consumed_dir.chmod(0o700)
        os.replace(pending, consumed_dir / f"{token_id}.json")
    except FileNotFoundError as exc:
        raise ClientError("\u786e\u8ba4\u4ee4\u724c\u4e0d\u5b58\u5728\u6216\u5df2\u4f7f\u7528\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4") from exc
    except OSError as exc:
        raise ClientError(f"\u65e0\u6cd5\u6d88\u8d39\u786e\u8ba4\u4ee4\u724c\uff1a{safe_error_text(str(exc))}") from exc


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
            "\u54cd\u5e94\u6807\u8bb0\u6210\u529f\u4f46\u672a\u8fd4\u56de\u53ef\u9a8c\u8bc1\u7684\u5de5\u5355\u53f7",
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
        raise ClientError("\u5de5\u5355\u6b63\u6587\u4e0d\u80fd\u4e3a\u7a7a")
    if not title:
        raise ClientError("\u5de5\u5355\u6807\u9898\u4e0d\u80fd\u4e3a\u7a7a")
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
    marked_payload["Description"] = f"{payload['Description']}\n\n[\u5ba2\u6237\u7aef\u8bf7\u6c42\u6807\u8bc6] {request_id}"
    return marked_payload, request_id


def reply_payload(args: argparse.Namespace, state: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    content = redact_text(read_input(args.content_file, 20_000)).strip()
    if not content:
        raise ClientError("\u56de\u590d\u5185\u5bb9\u4e0d\u80fd\u4e3a\u7a7a")
    api_payload = {"TicketId": args.ticket_id, "Content": content, "Encrypt": False}
    confirmation_payload = {**api_payload, "ExpectedStatus": state}
    return api_payload, confirmation_payload


def rules_status() -> dict[str, Any]:
    return dict(load_bundled_rules().status)


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
            "detail": f"aliyun version \u9000\u51fa\u7801 {returncode}",
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
    executable, _ = resolve_cli_executable()
    if not executable:
        return unknown_workorder_capabilities("cli_missing")
    try:
        returncode, stdout, stderr = run_cli_process([executable, "workorder", "--help"], timeout=10)
    except (ClientError, OSError, subprocess.TimeoutExpired) as exc:
        return unknown_workorder_capabilities("workorder_help_failed", str(exc))
    if returncode != 0:
        return unknown_workorder_capabilities(
            "workorder_help_failed",
            f"aliyun workorder --help \u9000\u51fa\u7801 {returncode}\uff1a{stderr or stdout}",
        )
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return unknown_workorder_capabilities("workorder_help_invalid_json", str(exc))
    if not isinstance(response, dict) or not isinstance(response.get("apis"), list):
        return unknown_workorder_capabilities("workorder_help_invalid_structure")
    advertised: set[str] = set()
    for item in response["apis"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
            return unknown_workorder_capabilities("workorder_help_invalid_structure")
        advertised.add(item["name"].strip())
    result = response.get("result")
    shown = result.get("shown") if isinstance(result, dict) else None
    total = result.get("total") if isinstance(result, dict) else None
    truncated = result.get("truncated") if isinstance(result, dict) else None
    complete = (
        truncated is False
        and isinstance(shown, int)
        and not isinstance(shown, bool)
        and isinstance(total, int)
        and not isinstance(total, bool)
        and shown == total == len(response["apis"])
        and len(advertised) == len(response["apis"])
    )
    required_apis = sorted({api for apis in WORKORDER_FEATURE_APIS.values() for api in apis})
    api_support = {
        api: "supported" if api in advertised else ("unsupported" if complete else "unknown")
        for api in required_apis
    }
    return {
        "probe": {
            "state": "succeeded",
            "complete": complete,
            "reason": "workorder_help_succeeded" if complete else "workorder_help_incomplete_or_inconsistent",
            "shown": shown,
            "total": total,
            "truncated": truncated,
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
        for capability in ("rules_status", "match_local_only", "draft")
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
        "impact": "\u5b89\u88c5\u7cfb\u7edf\u7ea7\u53ef\u6267\u884c\u6587\u4ef6\uff0c\u53ef\u80fd\u4fee\u6539 PATH\u3001\u8bbf\u95ee\u7f51\u7edc\u6216\u8bf7\u6c42\u7ba1\u7406\u5458\u6743\u9650",
    }


def workorder_access_status() -> dict[str, Any]:
    executable, _ = resolve_cli_executable()
    if not executable:
        return {"usable": False, "reason": "cli_missing"}
    try:
        workorder_call("ListProducts", {"Language": "zh"}, timeout=20)
    except ClientError as exc:
        return {"usable": False, "reason": "api_probe_failed", "detail": safe_error_text(str(exc))}
    return {"usable": True, "reason": "list_products_succeeded"}


def support_readiness(cli_status: dict[str, Any], workorder_status: dict[str, Any]) -> dict[str, Any]:
    if not cli_status["installed"]:
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
        "localCapabilities": ["rules_status", "match_local_only", "draft"],
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
                "\u4e0d\u5f97\u5728\u5bf9\u8bdd\u4e2d\u7d22\u53d6\u3001\u4ee3\u586b\u6216\u56de\u663e AccessKey Secret\u3001STS Token\u3001Bearer Token \u7b49\u79d8\u5bc6\uff1b"
                "\u5ba2\u6237\u575a\u6301\u4f7f\u7528\u542b\u79d8\u5bc6\u7684\u51ed\u636e\u6a21\u5f0f\u65f6\uff0c\u53ea\u80fd\u7531\u5ba2\u6237\u5728\u81ea\u5df1\u7684\u7ec8\u7aef\u4ea4\u4e92\u5f0f\u914d\u7f6e"
            ),
        },
        "verification": {
            "pythonLauncher": python_launcher,
            "commands": ["aliyun version", f"{python_launcher} scripts/aliyun_support.py doctor"],
            "successCondition": "doctor.readiness.readyForTicketOperations=true \u4e14 Workorder ListProducts \u63a2\u6d4b\u6210\u529f",
            "authenticationSuccessMustBeVerifiedByDoctor": True,
        },
    }


def command_doctor() -> dict[str, Any]:
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
        "rules": rules_status(),
        "credentialHandling": "Alibaba Cloud CLI default credential chain; credential values are never read or printed",
        "writeTransport": "redacted RPC string parameters are passed directly to the local aliyun CLI without a shell",
    }



def command_match(args: argparse.Namespace) -> dict[str, Any]:
    local_only = getattr(args, "local_only", False)
    product = getattr(args, "product", None)
    input_path = getattr(args, "input", None)
    product_id = getattr(args, "product_id", None)
    category_id = getattr(args, "category_id", None)
    if local_only:
        if product_id is not None or category_id is not None:
            raise ClientError("--local-only \u4e0d\u63a5\u53d7\u5206\u7c7b ID\uff1b\u4ec5\u63d0\u4f9b\u901a\u7528\u6a21\u677f")
        product = redact_text(require_string(product, "product")) if product is not None else None
        if input_path is not None:
            redact_text(read_input(input_path, 100_000))
        return {
            "confidence": "fallback",
            "selected": None,
            "candidates": [],
            "fallback": default_match_template(product, "local_only"),
            "category": None,
        }
    if product is not None or input_path is not None:
        raise ClientError("\u6b63\u5e38 match \u7981\u6b62\u65e7 --input/--product \u6587\u672c\u5339\u914d\uff1b\u8bf7\u4f7f\u7528 --product-id ID --category-id ID\uff0c\u6216\u663e\u5f0f --local-only")
    if product_id is None or category_id is None:
        raise ClientError("\u6b63\u5e38 match \u8981\u6c42 --product-id ID --category-id ID")
    category = lookup_category(product_id, category_id)
    rule, issue, matched, reason = map_category_rule(load_bundled_rules().rules, category)
    template = {
        "product": rule["product"],
        "issueType": issue["name"],
        "collectionRuleIssueType": issue["name"],
        "ruleMatched": True,
        "fallbackReason": None,
        "categoryHints": issue.get("categoryHints", []),
        "collect": [dict(field) for field in issue["collect"] if not is_user_identity_field(field)],
    } if matched else default_match_template(category["productName"], reason)
    template["category"] = category
    return {
        "confidence": "category_exact" if matched else "fallback",
        "selected": template if matched else None,
        "candidates": [template] if matched else [],
        "fallback": None if matched else template,
        "category": category,
    }


def command_draft(args: argparse.Namespace) -> dict[str, Any]:
    try:
        payload = json.loads(read_input(args.input))
    except json.JSONDecodeError as exc:
        raise ClientError(f"\u8349\u7a3f\u8f93\u5165 JSON \u65e0\u6548\uff1a{exc}") from exc
    return create_draft(payload)


def command_catalog(args: argparse.Namespace) -> dict[str, Any]:
    name = redact_text(args.name) if args.name is not None else None
    if args.catalog_command == "products":
        return workorder_call("ListProducts", {"Name": name, "Language": args.language})
    return workorder_call(
        "ListCategories",
        {"ProductId": args.product_id, "Name": name, "Language": args.language},
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
                    "content": payload["Description"],
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
            raise ClientError("\u5de5\u5355\u72b6\u6001\u5728\u786e\u8ba4\u540e\u53d1\u751f\u53d8\u5316\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u56de\u590d\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4")
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
            raise ClientError("\u5de5\u5355\u72b6\u6001\u5728\u786e\u8ba4\u540e\u53d1\u751f\u53d8\u5316\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u8bc4\u4ef7\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4")
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
            raise ClientError("\u5de5\u5355\u72b6\u6001\u5728\u786e\u8ba4\u540e\u53d1\u751f\u53d8\u5316\uff1b\u8bf7\u91cd\u65b0\u9884\u89c8\u5173\u95ed\u64cd\u4f5c\u5e76\u83b7\u5f97\u7528\u6237\u786e\u8ba4")
        return workorder_call("CloseTicket", {"TicketId": args.ticket_id})
    raise ClientError("\u672a\u77e5\u5de5\u5355\u547d\u4ee4")


def parse_cli_boolean(value: str) -> bool:
    rendered = normalize(value)
    if rendered == "true":
        return True
    if rendered == "false":
        return False
    raise argparse.ArgumentTypeError("\u5fc5\u987b\u662f true \u6216 false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="\u963f\u91cc\u4e91\u5de5\u5355\u652f\u6301\u672c\u5730\u5ba2\u6237\u7aef")
    parser.add_argument("--home", type=Path, default=default_home(), help="\u786e\u8ba4\u4ee4\u724c\u7b49\u975e\u89c4\u5219\u672c\u5730\u72b6\u6001\u76ee\u5f55")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="\u68c0\u67e5\u672c\u5730\u8fd0\u884c\u6761\u4ef6")


    rules = commands.add_parser("rules", help="\u67e5\u770b\u968f Skill \u53d1\u5e03\u7684\u672c\u5730\u89c4\u5219").add_subparsers(dest="rules_command", required=True)
    rules.add_parser("status", help="\u6821\u9a8c bundled \u89c4\u5219\u5305\u72b6\u6001")

    match = commands.add_parser("match", help="\u6838\u9a8c\u771f\u5b9e\u4ea7\u54c1\u5206\u7c7b\u5e76\u5339\u914d\u91c7\u96c6\u89c4\u5219")
    match.add_argument("--product-id", help="\u4ece\u771f\u5b9e\u4ea7\u54c1\u76ee\u5f55\u9009\u62e9\u7684 ProductId")
    match.add_argument("--category-id", help="\u4ece\u8be5\u4ea7\u54c1\u771f\u5b9e\u5206\u7c7b\u76ee\u5f55\u9009\u62e9\u7684 CategoryId")
    match.add_argument("--local-only", action="store_true", help="\u4e0d\u8c03 API\u3001\u4e0d\u52a0\u8f7d\u4e13\u9879\u89c4\u5219\uff0c\u53ea\u7ed9\u901a\u7528\u6a21\u677f")
    match.add_argument("--input", help="\u4ec5 --local-only \u53ef\u9009\u8131\u654f\u68c0\u67e5\u6587\u672c\u6587\u4ef6\uff1b- \u8868\u793a\u6807\u51c6\u8f93\u5165")
    match.add_argument("--product", help="\u4ec5 --local-only \u53ef\u9009\u4ea7\u54c1\u5c55\u793a\u6587\u672c")

    draft = commands.add_parser("draft", help="\u6821\u9a8c\u91c7\u96c6\u9879\u5e76\u751f\u6210\u8131\u654f\u8349\u7a3f")
    draft.add_argument("--input", required=True, help="\u6848\u4f8b JSON \u6587\u4ef6\uff1b- \u8868\u793a\u6807\u51c6\u8f93\u5165")

    catalog = commands.add_parser("catalog", help="\u52a8\u6001\u67e5\u8be2\u4ea7\u54c1\u548c\u5206\u7c7b").add_subparsers(dest="catalog_command", required=True)
    products = catalog.add_parser("products", help="\u67e5\u8be2\u53ef\u63d0\u5355\u4ea7\u54c1")
    products.add_argument("--name")
    products.add_argument("--language", choices=["zh", "en", "jp"], default="zh")
    categories = catalog.add_parser("categories", help="\u67e5\u8be2\u4ea7\u54c1\u95ee\u9898\u5206\u7c7b")
    categories.add_argument("--product-id", type=int, required=True)
    categories.add_argument("--name")
    categories.add_argument("--language", choices=["zh", "en", "jp"], default="zh")

    ticket = commands.add_parser("ticket", help="\u7ba1\u7406\u5de5\u5355").add_subparsers(dest="ticket_command", required=True)
    get_ticket = ticket.add_parser("get", help="\u67e5\u8be2\u5de5\u5355")
    get_ticket.add_argument("--ticket-id", required=True)

    list_ticket = ticket.add_parser("list", help="\u5206\u9875\u67e5\u8be2\u8fd1\u671f\u5de5\u5355")
    list_ticket.add_argument("--days", type=int, default=30, help="\u67e5\u8be2\u6700\u8fd1\u591a\u5c11\u5929\uff0c\u9ed8\u8ba4 30 \u5929")
    list_ticket.add_argument("--page-number", type=int, default=1)
    list_ticket.add_argument("--page-size", type=int, default=20)
    list_ticket.add_argument("--keyword", help="\u6309\u5de5\u5355\u6b63\u6587\u6a21\u7cca\u5339\u914d")
    list_ticket.add_argument("--ticket-id", help="\u6309\u5de5\u5355\u53f7\u7b5b\u9009")

    for name, help_text in (("preview-create", "\u9884\u89c8\u521b\u5efa\u5de5\u5355\u5e76\u751f\u6210\u786e\u8ba4\u4ee4\u724c"), ("create", "\u521b\u5efa\u5de5\u5355")):
        create = ticket.add_parser(name, help=help_text)
        create.add_argument("--category-id", required=True)
        create.add_argument("--severity", type=int, choices=[1, 2], default=1)
        create.add_argument("--title", required=True)
        create.add_argument("--content-file", required=True, help="\u6b63\u6587\u6587\u4ef6\uff1b- \u8868\u793a\u6807\u51c6\u8f93\u5165")
        if name == "create":
            create.add_argument("--confirmation-token", help="preview-create \u8fd4\u56de\u7684\u786e\u8ba4\u4ee4\u724c")

    for name, help_text in (("preview-reply", "\u9884\u89c8\u56de\u590d\u5e76\u751f\u6210\u786e\u8ba4\u4ee4\u724c"), ("reply", "\u56de\u590d\u5de5\u5355")):
        reply = ticket.add_parser(name, help=help_text)
        reply.add_argument("--ticket-id", required=True)
        reply.add_argument("--content-file", required=True, help="\u56de\u590d\u6587\u4ef6\uff1b- \u8868\u793a\u6807\u51c6\u8f93\u5165")
        if name == "reply":
            reply.add_argument("--confirmation-token", help="preview-reply \u8fd4\u56de\u7684\u786e\u8ba4\u4ee4\u724c")

    for name, help_text in (("preview-evaluate", "\u9884\u89c8\u8bc4\u4ef7\u5e76\u751f\u6210\u786e\u8ba4\u4ee4\u724c"), ("evaluate", "\u8bc4\u4ef7\u5de5\u5355")):
        evaluate = ticket.add_parser(name, help=help_text)
        evaluate.add_argument("--ticket-id", required=True)
        evaluate.add_argument("--score", type=int, choices=range(1, 6), required=True, help="1 \u5230 5 \u661f")
        evaluate.add_argument("--solved", type=parse_cli_boolean, required=True, help="\u95ee\u9898\u662f\u5426\u89e3\u51b3\uff1atrue \u6216 false")
        evaluate.add_argument("--content-file", help="\u53ef\u9009\u8bc4\u4ef7\u5185\u5bb9\u6587\u4ef6\uff1b- \u8868\u793a\u6807\u51c6\u8f93\u5165")
        if name == "evaluate":
            evaluate.add_argument("--confirmation-token", help="preview-evaluate \u8fd4\u56de\u7684\u786e\u8ba4\u4ee4\u724c")

    for name, help_text in (("preview-close", "\u9884\u89c8\u5173\u95ed\u5e76\u751f\u6210\u786e\u8ba4\u4ee4\u724c"), ("close", "\u5173\u95ed\u5de5\u5355")):
        close = ticket.add_parser(name, help=help_text)
        close.add_argument("--ticket-id", required=True)
        if name == "close":
            close.add_argument("--confirmation-token", help="preview-close \u8fd4\u56de\u7684\u786e\u8ba4\u4ee4\u724c")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.home = args.home.expanduser().resolve()
    try:
        if args.command == "doctor":
            result = command_doctor()
        elif args.command == "rules":
            result = rules_status()
        elif args.command == "match":
            result = command_match(args)
        elif args.command == "draft":
            result = command_draft(args)
        elif args.command == "catalog":
            result = command_catalog(args)
        elif args.command == "ticket":
            result = command_ticket(args)
        else:
            parser.error("\u672a\u77e5\u547d\u4ee4")
            return 2
        emit({"success": True, "data": result})
        return 0
    except ClientError as exc:
        emit({"success": False, "error": str(exc)})
        return 1
    except KeyboardInterrupt:
        emit({"success": False, "error": "\u64cd\u4f5c\u5df2\u53d6\u6d88"})
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
