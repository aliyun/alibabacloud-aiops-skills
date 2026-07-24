#!/usr/bin/env python3
"""STAROps API CLI for alibabacloud-sre-toolkit.

Handles HTTPS + ACS3-HMAC-SHA256 signing natively for STAROps APIs:
CreateThread, CreateChat (SSE stream), ListDigitalEmployees, GetDigitalEmployee,
CreateDigitalEmployee, DeleteDigitalEmployee.
Bundled with the skill so the host framework can invoke it via Shell execution.

Usage:
    python3 starops_manager.py chat <thread_id> <question> [--config <path>] [--uid <uid>]
    python3 starops_manager.py list-employees [--profile <name>] [--max-results <N>]
    python3 starops_manager.py get-employee <name> [--profile <name>]
    python3 starops_manager.py create-thread --employee-id <id> [--config <path>] [--uid <uid>]
    python3 starops_manager.py create-employee --display-name <name> [--description <desc>] [--profile <name>]
    python3 starops_manager.py delete-employee <name> [--profile <name>]
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional
from urllib.parse import quote, quote_plus

try:
    import requests
except ImportError:
    sys.exit("ERROR: requests not installed. Run: pip3 install -r requirements.txt")

try:
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_credentials.models import Config as CredentialConfig
except ImportError:
    sys.exit("ERROR: alibabacloud-credentials not installed. Run: pip3 install -r requirements.txt")

API_VERSION = "2026-04-28"
ALGORITHM = "ACS3-HMAC-SHA256"
DEFAULT_ENDPOINT = "starops.cn-beijing.aliyuncs.com"
# Only these endpoints are permitted — prevents credential exfiltration to arbitrary hosts.
_ALLOWED_ENDPOINT_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*\.aliyuncs\.com$")
DEFAULT_IDLE_TIMEOUT = 120
CONFIG_DIR = ".starops"
CONFIG_FILE = "config.json"
SKILL_NAME = "alibabacloud-sre-toolkit"


# ---------------------------------------------------------------------------
# Signing helpers (ACS3-HMAC-SHA256)
# ---------------------------------------------------------------------------

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def percent_encode(s: str) -> str:
    return s.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")


def _flatten_params(result: dict[str, str], prefix: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, (list, tuple)):
        for i, item in enumerate(value, 1):
            _flatten_params(result, f"{prefix}.{i}", item)
    elif isinstance(value, dict):
        for k, v in value.items():
            _flatten_params(result, f"{prefix}.{k}", v)
    else:
        result[prefix.lstrip(".")] = value.decode() if isinstance(value, bytes) else str(value)


def canonicalize_query(query: Mapping[str, Any]) -> str:
    flat: dict[str, str] = {}
    _flatten_params(flat, "", dict(query))
    return "&".join(
        f"{percent_encode(quote_plus(k))}={percent_encode(quote_plus(flat[k]))}"
        for k in sorted(flat)
    )


def build_canonical_request(
    method: str, path: str, query: Mapping[str, Any],
    headers: Mapping[str, str], body: bytes,
) -> tuple[str, str]:
    signed: OrderedDict[str, str] = OrderedDict()
    for k in sorted(headers, key=str.lower):
        lk = k.lower()
        if lk == "authorization":
            continue
        if lk.startswith("x-acs-") or lk in ("host", "content-type"):
            signed[lk] = re.sub(r"\s+", " ", str(headers[k])).strip()
    canon_headers = "\n".join(f"{k}:{v}" for k, v in signed.items()) + "\n"
    canon_req = "\n".join([
        method.upper(), path, canonicalize_query(query),
        canon_headers, ";".join(signed.keys()), sha256_hex(body),
    ])
    return canon_req, ";".join(signed.keys())


# ---------------------------------------------------------------------------
# STAROps config resolution
# ---------------------------------------------------------------------------

def resolve_config(explicit_path: Optional[str] = None) -> dict[str, Any]:
    config: dict[str, Any] = {}
    candidate = Path(CONFIG_DIR) / CONFIG_FILE
    if candidate.is_file():
        with open(candidate) as f:
            config.update(json.load(f))
    if explicit_path:
        p = Path(explicit_path).expanduser()
        if p.is_file():
            with open(p) as f:
                config.update(json.load(f))
    return config


def select_account(config: Mapping[str, Any], uid: Optional[str] = None) -> dict[str, Any]:
    """Select an account from config, supporting both new and legacy formats.

    New format: ``{"accounts": [{"uid", "profile", "employeeId", "workspace"}]}``.
    Legacy format: top-level ``employeeId``/``workspace``/``uid`` = single account.

    Returns a normalized dict with keys ``uid``/``employeeId``/``workspace``/``profile``.
    Raises ``RuntimeError`` when no account matches ``uid`` or when the account is
    ambiguous (multiple accounts and no ``uid`` given).
    """
    accounts = config.get("accounts")
    if isinstance(accounts, list) and accounts:
        norm = [a for a in accounts if isinstance(a, dict)]
        if not norm:
            raise RuntimeError("No valid account entries in 'accounts'")
        if uid:
            matches = [a for a in norm if str(a.get("uid", "")) == str(uid)]
            if not matches:
                available = ", ".join(str(a.get("uid", "")) for a in norm) or "(none)"
                raise RuntimeError(
                    f"No account matching uid '{uid}' in config; available uids: {available}"
                )
            chosen = matches[0]
        elif len(norm) == 1:
            chosen = norm[0]
        else:
            available = ", ".join(str(a.get("uid", "")) for a in norm)
            raise RuntimeError(
                f"Multiple accounts configured ({available}); specify one via --uid"
            )
        return {
            "uid": str(chosen.get("uid", "")),
            "employeeId": chosen.get("employeeId", ""),
            "workspace": chosen.get("workspace", ""),
            "profile": chosen.get("profile") or None,
        }

    # Legacy single-account format.
    return {
        "uid": str(config.get("uid", "")),
        "employeeId": config.get("employeeId", ""),
        "workspace": config.get("workspace", ""),
        "profile": config.get("profile") or None,
    }


# ---------------------------------------------------------------------------
# Credential resolution (per-profile, read-only against aliyun CLI config)
# ---------------------------------------------------------------------------

# Maps aliyun CLI profile ``mode`` values to alibabacloud-credentials types.
_MODE_TO_CRED_TYPE = {
    "ak": "access_key",
    "sts": "sts",
    "ststoken": "sts",
}


def _load_aliyun_profile(profile_name: str) -> dict[str, Any]:
    """Read a single profile from ``~/.aliyun/config.json`` (read-only).

    Never modifies the file, in particular never touches the ``current`` field.
    """
    cfg_path = Path.home() / ".aliyun" / "config.json"
    if not cfg_path.is_file():
        raise RuntimeError(f"aliyun CLI config not found at {cfg_path}")
    with open(cfg_path) as f:
        data = json.load(f)
    for prof in (data.get("profiles") or []):
        if isinstance(prof, dict) and prof.get("name") == profile_name:
            return prof
    raise RuntimeError(f"Profile '{profile_name}' not found in {cfg_path}")


def _get_credentials(
    profile_name: Optional[str] = None,
) -> tuple[str, str, Optional[str]]:
    """Resolve (access_key_id, access_key_secret, security_token).

    SECURITY: Credentials are resolved locally and used exclusively for
    signing HTTPS requests to authenticated Alibaba Cloud endpoints
    (*.aliyuncs.com, enforced by ``_sign_request``). They are never logged,
    printed, or transmitted to any non-Alibaba host.

    When ``profile_name`` is falsy, use the default CredentialClient (relies on
    the aliyun CLI global ``current`` / standard credential chain) — preserving
    the original behaviour.

    When ``profile_name`` is given, read that profile from ``~/.aliyun/config.json``
    and construct credentials via alibabacloud-credentials without altering the
    aliyun CLI global ``current``. Supports at least AK and STS modes.
    """
    if not profile_name:
        # SECURITY: Credentials read from standard Alibaba Cloud env vars for
        # alibabacloud-credentials SDK compatibility. Values are used solely
        # for API authentication and are never logged, returned, or transmitted.
        env_ak = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "").strip()
        env_sk = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "").strip()
        if env_ak and env_sk:
            return env_ak, env_sk, None
        # Fall back to default CredentialClient (which also checks env vars)
        c = CredentialClient().get_credential()
        return c.get_access_key_id(), c.get_access_key_secret(), c.get_security_token()

    prof = _load_aliyun_profile(profile_name)
    mode = str(prof.get("mode", "AK")).strip()
    ak_id = prof.get("access_key_id", "")
    ak_secret = prof.get("access_key_secret", "")
    sts_token = prof.get("sts_token") or None

    cred_type = _MODE_TO_CRED_TYPE.get(mode.lower())
    if cred_type is None:
        # Unknown mode: fall back based on presence of an STS token.
        cred_type = "sts" if sts_token else "access_key"
    if not ak_id or not ak_secret:
        raise RuntimeError(
            f"Profile '{profile_name}' (mode={mode}) has no usable "
            f"access_key_id/access_key_secret; only AK/STS profiles are supported "
            f"for profile-based signing"
        )

    cfg = CredentialConfig(
        type=cred_type,
        access_key_id=ak_id,
        access_key_secret=ak_secret,
        security_token=sts_token,
    )
    c = CredentialClient(cfg).get_credential()
    return c.get_access_key_id(), c.get_access_key_secret(), c.get_security_token()


# ---------------------------------------------------------------------------
# SSE stream parser
# ---------------------------------------------------------------------------

def iter_sse_payloads(response: Any) -> Iterable[dict[str, Any]]:
    """Parse an SSE stream response into JSON payloads.

    Handles ``data:`` lines, multi-line accumulation, and blank-line flush.
    Comment lines (``:``) and field lines (``event:``, ``id:``, ``retry:``)
    are skipped per the SSE spec.
    """
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

    lines = response.iter_lines(decode_unicode=False)
    for raw_line in lines:
        line = (raw_line.decode("utf-8") if isinstance(raw_line, bytes) else str(raw_line)).rstrip("\r")
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
        if line.startswith(("event:", "id:", "retry:")):
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


# ---------------------------------------------------------------------------
# Message text extraction
# ---------------------------------------------------------------------------

_ASSISTANT_ROLES = {"assistant", "agent", "system", "ai"}
_TEXT_FIELDS = ("content", "text", "value", "answer")
_CONTAINER_FIELDS = ("contents", "items")


def extract_assistant_text(messages: list[Any]) -> str:
    """Extract and deduplicate assistant text from a messages list."""
    parts: list[str] = []
    for msg in (messages or []):
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "")).strip().lower()
        if role not in _ASSISTANT_ROLES:
            continue
        for field in _TEXT_FIELDS:
            v = msg.get(field)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
        for container_key in _CONTAINER_FIELDS:
            for item in (msg.get(container_key) or []):
                if isinstance(item, dict):
                    for field in _TEXT_FIELDS:
                        v = item.get(field)
                        if isinstance(v, str) and v.strip():
                            parts.append(v.strip())

    seen: set[str] = set()
    deduped: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return "\n".join(deduped).strip()


def extract_all_messages(messages: list[Any]) -> list[tuple[str, str]]:
    """Extract (role, text) pairs from all messages regardless of role."""
    results: list[tuple[str, str]] = []
    for msg in (messages or []):
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "unknown")).strip().lower()
        for field in _TEXT_FIELDS:
            v = msg.get(field)
            if isinstance(v, str) and v.strip():
                results.append((role, v.strip()))
        for container_key in _CONTAINER_FIELDS:
            for item in (msg.get(container_key) or []):
                if isinstance(item, dict):
                    for field in _TEXT_FIELDS:
                        v = item.get(field)
                        if isinstance(v, str) and v.strip():
                            results.append((role, v.strip()))
    return results


def _extract_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get("body", payload) if isinstance(payload, dict) else payload
    if not isinstance(body, dict):
        return []
    msgs = body.get("messages")
    if msgs is None and isinstance(body.get("data"), dict):
        msgs = body["data"].get("messages")
    return [m for m in (msgs or []) if isinstance(m, dict)]


# ---------------------------------------------------------------------------
# Signed HTTPS request
# ---------------------------------------------------------------------------

def _sign_request(
    method: str, path: str, action: str, endpoint: str,
    body_dict: Optional[dict] = None, session_id: Optional[str] = None,
    profile_name: Optional[str] = None, query_dict: Optional[dict] = None,
) -> tuple[dict[str, str], str, bytes]:
    """Build and sign an HTTPS request. Returns (headers, url, body_bytes).

    When ``profile_name`` is given, credentials are resolved for that specific
    aliyun CLI profile instead of the global ``current`` account.
    When ``query_dict`` is given, its entries are included in the canonical
    request and appended to the URL as query parameters.

    SECURITY: Credentials are only sent to authenticated Alibaba Cloud
    endpoints matching ``*.aliyuncs.com``. Non-matching endpoints are rejected
    before any credential resolution occurs.
    """
    if not _ALLOWED_ENDPOINT_RE.match(endpoint):
        raise ValueError(
            f"Refusing to send credentials to non-Alibaba endpoint: {endpoint!r}. "
            f"Only *.aliyuncs.com endpoints are permitted."
        )
    ak_id, ak_secret, security_token = _get_credentials(profile_name)

    body_bytes = json.dumps(body_dict or {}, ensure_ascii=False, separators=(",", ":")).encode()
    actual_body = body_bytes if method.upper() not in ("GET", "DELETE") else b""
    query = query_dict or {}
    ua_session = session_id or uuid.uuid4().hex
    headers = OrderedDict([
        ("host", endpoint),
        ("content-type", "application/json; charset=utf-8"),
        ("x-acs-action", action),
        ("x-acs-version", API_VERSION),
        ("x-acs-date", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("x-acs-signature-nonce", str(uuid.uuid4())),
        ("x-acs-content-sha256", sha256_hex(actual_body)),
        ("user-agent", f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{ua_session}"),
    ])
    if security_token:
        headers["x-acs-security-token"] = security_token

    canon_req, signed_headers = build_canonical_request(
        method, path, query, headers, actual_body,
    )
    string_to_sign = f"{ALGORITHM}\n{sha256_hex(canon_req.encode())}"
    sig = hmac.new(
        ak_secret.encode(), string_to_sign.encode(), hashlib.sha256,
    ).hexdigest().lower()
    headers["Authorization"] = (
        f"{ALGORITHM} Credential={ak_id},SignedHeaders={signed_headers},Signature={sig}"
    )

    query_str = canonicalize_query(query)
    url = f"https://{endpoint}{path}?{query_str}" if query_str else f"https://{endpoint}{path}"
    return dict(headers), url, actual_body


# ---------------------------------------------------------------------------
# Public API: CreateThread (JSON) + CreateChat (SSE stream)
# ---------------------------------------------------------------------------

def create_thread(
    employee_id: str, workspace: str = "", title: str = "",
    endpoint: str = DEFAULT_ENDPOINT, session_id: Optional[str] = None,
    uid: str = "", profile_name: Optional[str] = None,
) -> str:
    """Create a STAROps thread. Returns threadId.

    The idempotency key includes ``uid`` so threads from different accounts do
    not collide when other fields happen to match.
    """
    key_payload = {
        "uid": uid,
        "employeeId": employee_id,
        "workspace": workspace,
        "title": title,
    }
    idempotency_key = sha256_hex(
        json.dumps(key_payload, separators=(",", ":"), sort_keys=True).encode()
    )
    body = {
        "title": title[:80] or "STAROps question",
        "idempotencyKey": idempotency_key,
        "variables": {"workspace": workspace} if workspace else {},
        "attributes": {"source": SKILL_NAME},
    }
    headers, url, body_bytes = _sign_request(
        "POST", f"/digitalEmployee/{quote(employee_id, safe='')}/thread",
        "CreateThread", endpoint, body, session_id, profile_name=profile_name,
    )
    # Outbound: CreateThread API call to STAROps endpoint (trusted *.aliyuncs.com).
    # Payload: digitalEmployeeName, workspace variables, source attribute. No credentials in body.
    resp = requests.post(url, headers=headers, data=body_bytes, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"CreateThread HTTP {resp.status_code}: {resp.text[:500]}")
    payload = resp.json()
    body_data = payload.get("body", payload)
    thread_id = body_data.get("threadId") if isinstance(body_data, dict) else None
    if not thread_id:
        raise RuntimeError(f"CreateThread returned no threadId: {payload}")
    return str(thread_id)


def stream_chat(
    employee_id: str, workspace: str = "", thread_id: str = "", question: str = "",
    endpoint: str = DEFAULT_ENDPOINT, idle_timeout: int = DEFAULT_IDLE_TIMEOUT,
    session_id: Optional[str] = None, profile_name: Optional[str] = None,
    on_event: Optional[Callable[[dict[str, Any]], None]] = None,
) -> str:
    """Send a CreateChat request and consume the SSE stream.

    Returns the complete assistant answer text with deduplication.
    When ``on_event`` is provided, it is called for each raw SSE payload as it
    arrives, enabling real-time streaming / thinking-process capture.
    """
    body = {
        "action": "create",
        "digitalEmployeeName": employee_id,
        "threadId": thread_id,
        "messages": [{
            "messageId": str(uuid.uuid4()),
            "role": "user",
            "contents": [{"type": "text", "value": question}],
        }],
        "variables": {"workspace": workspace} if workspace else {},
    }
    headers, url, body_bytes = _sign_request(
        "POST", "/chat", "CreateChat", endpoint, body, session_id,
        profile_name=profile_name,
    )
    # Outbound: CreateChat API call to STAROps endpoint (trusted *.aliyuncs.com).
    # Payload: threadId, user question text, workspace variables. No credentials in body.
    resp = requests.post(
        url, headers=headers, data=body_bytes,
        stream=True, timeout=(30, idle_timeout),
    )
    if resp.status_code != 200:
        raise RuntimeError(f"CreateChat HTTP {resp.status_code}: {resp.text[:500]}")

    all_text: list[str] = []
    for payload in iter_sse_payloads(resp):
        if on_event:
            on_event(payload)
        text = extract_assistant_text(_extract_messages(payload))
        if text:
            all_text.append(text)

    return "\n\n".join(t for t in all_text if t.strip()).strip()


# ---------------------------------------------------------------------------
# Public API: ListDigitalEmployees + GetDigitalEmployee (standard JSON)
# ---------------------------------------------------------------------------

def list_digital_employees(
    profile_name: Optional[str] = None, endpoint: str = DEFAULT_ENDPOINT,
    max_results: int = 100, next_token: Optional[str] = None,
) -> dict:
    """List digital employees via GET /digital-employee. Returns parsed JSON."""
    query: dict[str, Any] = {"maxResults": max_results}
    if next_token:
        query["nextToken"] = next_token
    headers, url, _ = _sign_request(
        "GET", "/digital-employee", "ListDigitalEmployees", endpoint,
        None, None, profile_name=profile_name, query_dict=query,
    )
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"ListDigitalEmployees HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def get_digital_employee(
    name: str, profile_name: Optional[str] = None, endpoint: str = DEFAULT_ENDPOINT,
) -> dict:
    """Get digital employee details via GET /digital-employee/{name}. Returns parsed JSON."""
    path = f"/digital-employee/{quote(name, safe='')}"
    headers, url, _ = _sign_request(
        "GET", path, "GetDigitalEmployee", endpoint,
        None, None, profile_name=profile_name,
    )
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"GetDigitalEmployee HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()


# ---------------------------------------------------------------------------
# Public API: CreateDigitalEmployee + DeleteDigitalEmployee (standard JSON)
# ---------------------------------------------------------------------------

def create_digital_employee(
    display_name: str, description: str = "",
    endpoint: str = DEFAULT_ENDPOINT, profile_name: Optional[str] = None,
) -> dict:
    """Create a STAROps digital employee via POST /digital-employee."""
    body = {"displayName": display_name, "description": description}
    headers, url, body_bytes = _sign_request(
        "POST", "/digital-employee", "CreateDigitalEmployee", endpoint,
        body, None, profile_name=profile_name,
    )
    # Outbound: CreateDigitalEmployee API call to STAROps endpoint (trusted *.aliyuncs.com).
    # Payload: displayName, description only. No credentials or sensitive data.
    resp = requests.post(url, headers=headers, data=body_bytes, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"CreateDigitalEmployee HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def delete_digital_employee(
    name: str, endpoint: str = DEFAULT_ENDPOINT, profile_name: Optional[str] = None,
) -> dict:
    """Delete a STAROps digital employee via DELETE /digital-employee/{name}."""
    path = f"/digital-employee/{quote(name, safe='')}"
    headers, url, _ = _sign_request(
        "DELETE", path, "DeleteDigitalEmployee", endpoint,
        None, None, profile_name=profile_name,
    )
    resp = requests.delete(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"DeleteDigitalEmployee HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()


# ---------------------------------------------------------------------------
# CLI entry point (subcommand mode)
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="STAROps API CLI for alibabacloud-sre-toolkit. "
        "Subcommands: chat, list-employees, get-employee, create-thread, create-employee, delete-employee.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # chat — CreateChat (SSE stream)
    p_chat = subparsers.add_parser("chat", help="Send a CreateChat SSE query")
    p_chat.add_argument("thread_id", help="Existing STAROps thread ID")
    p_chat.add_argument("question", help="Natural language question to send")
    p_chat.add_argument("--config", help="Path to STAROps JSON config file")
    p_chat.add_argument("--uid", help="Account UID to select from multi-account config")
    p_chat.add_argument(
        "--idle-timeout", type=int, default=DEFAULT_IDLE_TIMEOUT,
        help=f"Max seconds to wait for next SSE event (default {DEFAULT_IDLE_TIMEOUT})",
    )
    p_chat.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="STAROps endpoint")
    p_chat.add_argument("--stream", action="store_true",
                        help="Print SSE events to stderr in real-time (shows thinking process)")
    p_chat.add_argument("--raw", action="store_true",
                        help="Print raw SSE payloads as JSON to stderr (for debugging)")
    p_chat.add_argument("--json", action="store_true",
                        help="Output structured JSON {thinking, answer} to stdout")

    # list-employees — ListDigitalEmployees (JSON)
    p_list = subparsers.add_parser("list-employees", help="List digital employees")
    p_list.add_argument("--profile", help="aliyun CLI profile name for credentials")
    p_list.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="STAROps endpoint")
    p_list.add_argument("--max-results", type=int, default=100, help="Page size (default 100)")

    # get-employee — GetDigitalEmployee (JSON)
    p_get = subparsers.add_parser("get-employee", help="Get digital employee details")
    p_get.add_argument("name", help="Digital employee name (= employeeId)")
    p_get.add_argument("--profile", help="aliyun CLI profile name for credentials")
    p_get.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="STAROps endpoint")

    # create-thread — CreateThread (JSON)
    p_create = subparsers.add_parser("create-thread", help="Create a STAROps thread")
    p_create.add_argument("--employee-id", required=True, help="STAROps Digital Employee ID")
    p_create.add_argument("--title", default="", help="Thread title")
    p_create.add_argument("--config", help="Path to STAROps JSON config file")
    p_create.add_argument("--uid", help="Account UID to select from multi-account config")
    p_create.add_argument("--profile", help="aliyun CLI profile name (overrides config)")
    p_create.add_argument("--workspace", default="", help="STAROps workspace (optional)")
    p_create.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="STAROps endpoint")

    # create-employee — CreateDigitalEmployee (JSON)
    p_create_emp = subparsers.add_parser("create-employee", help="Create a STAROps digital employee")
    p_create_emp.add_argument("--display-name", required=True, help="Display name")
    p_create_emp.add_argument("--description", default="", help="Description")
    p_create_emp.add_argument("--profile", help="aliyun CLI profile name for credentials")
    p_create_emp.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="STAROps endpoint")

    # delete-employee — DeleteDigitalEmployee (JSON)
    p_delete_emp = subparsers.add_parser("delete-employee", help="Delete a STAROps digital employee")
    p_delete_emp.add_argument("name", help="Digital employee name (= employeeId)")
    p_delete_emp.add_argument("--profile", help="aliyun CLI profile name for credentials")
    p_delete_emp.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="STAROps endpoint")

    return parser


def _append_trace(command: str, args_dict: dict, success: bool, exit_code: int, extra: dict | None = None) -> None:
    """Append an execution trace record to .aliyun-sre/execution-trace.jsonl."""
    sre_dir = os.path.join(os.getcwd(), ".aliyun-sre")
    if not os.path.isdir(sre_dir):
        os.makedirs(sre_dir, exist_ok=True)
    trace_path = os.path.join(sre_dir, "execution-trace.jsonl")
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script": "starops_manager.py",
        "command": command,
        "args": args_dict,
        "session": (extra or {}).get("session"),
        "thread_id": (extra or {}).get("thread_id"),
        "exit_code": exit_code,
        "success": success,
    }
    trace_flags = os.O_CREAT | os.O_WRONLY | os.O_APPEND
    trace_fd = os.open(str(trace_path), trace_flags, 0o600)
    with os.fdopen(trace_fd, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _main_inner(args) -> int:
    if args.command == "list-employees":
        try:
            result = list_digital_employees(
                profile_name=args.profile,
                endpoint=args.endpoint,
                max_results=args.max_results,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.command == "get-employee":
        try:
            result = get_digital_employee(
                name=args.name,
                profile_name=args.profile,
                endpoint=args.endpoint,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.command == "create-employee":
        try:
            result = create_digital_employee(
                display_name=args.display_name,
                description=args.description,
                endpoint=args.endpoint,
                profile_name=args.profile,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.command == "delete-employee":
        try:
            result = delete_digital_employee(
                name=args.name,
                endpoint=args.endpoint,
                profile_name=args.profile,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if args.command == "create-thread":
        profile_name = args.profile
        uid = ""
        workspace = args.workspace
        if args.config or not profile_name:
            config = resolve_config(args.config)
            try:
                account = select_account(config, args.uid)
                if not profile_name:
                    profile_name = account["profile"]
                uid = account["uid"]
                if not workspace:
                    workspace = account["workspace"]
            except Exception:
                if not profile_name:
                    print("ERROR: No --profile given and no config account found", file=sys.stderr)
                    return 1
        session_id = uuid.uuid4().hex
        try:
            thread_id = create_thread(
                employee_id=args.employee_id,
                workspace=workspace,
                title=args.title,
                endpoint=args.endpoint,
                session_id=session_id,
                uid=uid,
                profile_name=profile_name,
            )
            print(thread_id)
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    # chat (CreateChat SSE)
    config = resolve_config(args.config)
    try:
        account = select_account(config, args.uid)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    employee_id = account["employeeId"]
    workspace = account["workspace"]
    profile_name = account["profile"]
    if not employee_id:
        print("ERROR: Missing employeeId in STAROps config", file=sys.stderr)
        return 1

    collected_events: list[dict[str, Any]] = []
    need_events = args.stream or args.raw or args.json

    def on_event(payload: dict[str, Any]) -> None:
        collected_events.append(payload)
        if args.raw:
            print(json.dumps(payload, ensure_ascii=False), file=sys.stderr, flush=True)
        if args.stream:
            msgs = _extract_messages(payload)
            for role, text in extract_all_messages(msgs):
                print(f"[{role}] {text}", file=sys.stderr, flush=True)

    session_id = uuid.uuid4().hex
    try:
        result = stream_chat(
            employee_id=employee_id,
            workspace=workspace,
            thread_id=args.thread_id,
            question=args.question,
            endpoint=args.endpoint,
            idle_timeout=args.idle_timeout,
            session_id=session_id,
            profile_name=profile_name,
            on_event=on_event if need_events else None,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        thinking_parts: list[str] = []
        for event in collected_events:
            msgs = _extract_messages(event)
            for role, text in extract_all_messages(msgs):
                if role not in _ASSISTANT_ROLES:
                    thinking_parts.append(text)
        output = {"thinking": "\n".join(thinking_parts).strip(), "answer": result}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif result:
        print(result)
    else:
        print("(No assistant answer was returned.)")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    exit_code = _main_inner(args)
    extra = {}
    if args.command == "chat" and hasattr(args, "thread_id"):
        extra["thread_id"] = args.thread_id
    _append_trace(args.command, vars(args), exit_code == 0, exit_code, extra or None)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
