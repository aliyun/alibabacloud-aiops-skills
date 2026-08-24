#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation helper for AK Leak Incident Response
=========================================================================
Internal module (prefixed with `_`). Do NOT run directly -- it is imported by the
query scripts so that all Alibaba Cloud OpenAPI access goes through ONE place.

Dual backend (CLI-first, HTTP-fallback)
---------------------------------------
Every API call is routed through `call()`, which selects a backend at runtime:

  1. CLI backend (preferred): if the `aliyun` binary is on PATH, the call is
     executed as
         aliyun <product> <Action> --region <r> [--endpoint <ep>] [--Param v ...]
     The CLI carries built-in API metadata, uses its own credential profile
     (~/.aliyun/config.json) for auth, and returns raw JSON on stdout.

  2. HTTP backend (fallback): if `aliyun` is NOT available, the call is signed
     with the Alibaba Cloud OpenAPI V3 signature (ACS3-HMAC-SHA256) and sent
     directly over HTTPS via `requests`. Credentials are resolved from
     environment variables or ~/.aliyun/config.json. No product SDKs needed.

Both backends return the SAME raw API JSON, so all downstream code (the four
business scripts, the pagination helpers) is backend-agnostic and unchanged.

Backend override: set env `AK_LEAK_BACKEND=cli` or `AK_LEAK_BACKEND=http`.

Public API:
    call(product, action, params=None, region=..., profile=None) -> dict
    paginate_next_token(product, action, params, region, ...) -> list[dict]   # ActionTrail
    paginate_marker(product, action, params, region, list_path, ...) -> list  # RAM/IMS
    get_time_window(days) -> (start_iso, end_iso)
    check_cli_available() -> None   # alias of check_backend_available()
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails (either backend)."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Per-product endpoint / version metadata
# ---------------------------------------------------------------------------
# `endpoint`      : region-less central endpoint (ram/ims).
# `endpoint_tmpl` : region-templated endpoint.
# `version`       : OpenAPI version (required by the HTTP backend's V3 signature;
#                   ignored by the CLI backend, which knows versions internally).
PRODUCT_META: dict[str, dict[str, str]] = {
    "actiontrail": {"endpoint_tmpl": "actiontrail.{region}.aliyuncs.com", "version": "2020-07-06"},
    "ram": {"endpoint": "ram.aliyuncs.com", "version": "2015-05-01"},          # central, region-less
    "ims": {"endpoint": "ims.aliyuncs.com", "version": "2019-08-15"},          # central, region-less
    "sas": {"endpoint_tmpl": "tds.{region}.aliyuncs.com", "version": "2018-12-03"},
    "cloudsso": {"endpoint_tmpl": "cloudsso.{region}.aliyuncs.com", "version": "2021-05-15"},
    "sts": {"endpoint": "sts.aliyuncs.com", "version": "2015-04-01"},      # central, region-less
}

_DEFAULT_REGION = "cn-shanghai"

# Cached backend decision ("cli" | "http"). Resolved once per process.
_BACKEND: Optional[str] = None


# ---------------------------------------------------------------------------
# Observability: one session-id shared by EVERY API call in this process,
# emitted as a User-Agent on BOTH backends for server-side audit correlation.
# ---------------------------------------------------------------------------
_SKILL_NAME = "alibabacloud-ak-leak-incident-response"
_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the 32-char lowercase-hex session-id for this investigation.

    Generated once on first use and cached for the process lifetime, so every
    API call (CLI or HTTP) in one run shares the SAME id. Honors env
    `AK_LEAK_SESSION_ID` (must be 32 hex chars) so a parent process and any
    child share one id; otherwise a fresh `uuid.uuid4().hex` is used.
    """
    global _SESSION_ID
    if _SESSION_ID is None:
        env = (os.environ.get("AK_LEAK_SESSION_ID") or "").strip().lower()
        if len(env) == 32 and all(c in "0123456789abcdef" for c in env):
            _SESSION_ID = env
        else:
            _SESSION_ID = uuid.uuid4().hex
    return _SESSION_ID


def user_agent() -> str:
    """User-Agent identifying this skill + invocation.

    Template: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id}`. The same
    string is attached to every CLI subprocess (`--user-agent`) and every HTTP
    fallback request (`User-Agent` header).
    """
    return f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{session_id()}"


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

def _select_backend() -> str:
    """Decide which backend to use: CLI if available, else HTTP.

    Honors the `AK_LEAK_BACKEND` env var (`cli`/`http`) for explicit override.
    The result is cached for the lifetime of the process.
    """
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    forced = (os.environ.get("AK_LEAK_BACKEND") or "").strip().lower()
    if forced in ("cli", "http"):
        _BACKEND = forced
    elif shutil.which("aliyun") is not None:
        _BACKEND = "cli"
    else:
        _BACKEND = "http"
    return _BACKEND


def _auto_install_enabled() -> bool:
    """Whether on-demand `pip install requests` is allowed (opt-in, default OFF)."""
    return (os.environ.get("AK_LEAK_AUTO_INSTALL") or "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _import_requests():
    """Import `requests`, optionally auto-installing it first.

    Auto-install only runs when the HTTP fallback needs `requests`, the package
    is missing, AND env AK_LEAK_AUTO_INSTALL is enabled. Returns the module, or
    None if unavailable (and not installable).
    """
    try:
        import requests
        return requests
    except ImportError:
        pass
    if not _auto_install_enabled():
        return None
    print(
        "[_cli] `requests` not found; AK_LEAK_AUTO_INSTALL is set — installing "
        "`requests>=2.20.0` into the current interpreter ...",
        file=sys.stderr,
    )
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "requests>=2.20.0"],
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"[_cli] auto-install of `requests` failed: {e}", file=sys.stderr)
        return None
    try:
        import requests
        return requests
    except ImportError:
        return None


def check_backend_available() -> None:
    """Ensure a usable backend exists; exit with guidance otherwise.

    CLI backend  -> requires the `aliyun` binary (auth handled by CLI profile).
    HTTP backend -> requires the `requests` package importable (credentials are
                    verified lazily on first call). If `requests` is missing and
                    auto-install is enabled (env AK_LEAK_AUTO_INSTALL=1), it is
                    installed on demand.
    """
    backend = _select_backend()
    if backend == "cli":
        return
    # HTTP fallback: verify (and optionally auto-install) the requests dependency.
    if _import_requests() is None:
        print(
            "\n" + "=" * 78 + "\n"
            " No usable OpenAPI backend\n"
            + "=" * 78 + "\n"
            "The `aliyun` CLI was not found, so this skill falls back to direct\n"
            "HTTPS calls, which require the `requests` package.\n\n"
            "  Option A (recommended): install the Alibaba Cloud CLI\n"
            "     https://help.aliyun.com/document_detail/121541.html\n"
            "     then: aliyun configure\n\n"
            "  Option B: install requests for the HTTP fallback\n"
            "     pip install requests\n"
            "     and provide credentials via env vars or ~/.aliyun/config.json\n\n"
            "  Option C: let this skill install requests automatically\n"
            "     export AK_LEAK_AUTO_INSTALL=1   (then re-run)\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


# Backwards-compatible alias used by the business scripts.
check_cli_available = check_backend_available


def _endpoint_for(product: str, region: str) -> Optional[str]:
    meta = PRODUCT_META.get(product, {})
    if "endpoint" in meta:
        return meta["endpoint"]
    if "endpoint_tmpl" in meta:
        return meta["endpoint_tmpl"].format(region=region)
    return None


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

def call(
    product: str,
    action: str,
    params: Optional[dict[str, Any]] = None,
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Invoke an Alibaba Cloud OpenAPI action, routing to the active backend.

    Args:
        product:  Product code (e.g. "ram", "ims", "actiontrail", "sas", "cloudsso").
        action:   API action name (e.g. "GetPasswordPolicy", "LookupEvents").
        params:   Dict of request parameters. Keys are used verbatim, so
                  nested/repeated params work too (e.g. "LookupAttribute.1.Key").
        region:   Region id.
        profile:  Optional credential profile name (CLI profile / config.json profile).
        timeout:  Per-call timeout in seconds.

    Returns:
        Parsed JSON response as a dict (identical shape for both backends).

    Raises:
        CliError: On failure (non-zero exit / HTTP error / unparseable output).
    """
    if _select_backend() == "cli":
        return _call_cli(product, action, params, region, profile, timeout)
    return _call_http(product, action, params, region, profile, timeout)


def resolve_account_id(
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
) -> str:
    """Return the Alibaba Cloud UID (AccountId) bound to the active credential.

    Uses STS GetCallerIdentity, which needs no input beyond the configured
    credential (CLI profile / env / config.json). Works for both the root
    account and RAM users -- it returns the primary account's UID either way.
    Returns "" if it cannot be resolved (e.g. the credential lacks STS access).
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
        return str(body.get("AccountId", "") or "")
    except CliError as e:
        print(f"[WARN] STS GetCallerIdentity failed: {e} — continuing with degradation (UID unresolvable)", file=sys.stderr)
        return ""


def resolve_caller_username(
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
) -> str:
    """Return the RAM user name of the active credential, or "" if not a RAM user.

    Parses the STS GetCallerIdentity Arn (`acs:ram::<uid>:user/<name>`). Returns
    "" for the root account, an assumed role, or when it cannot be resolved --
    callers should treat "" as "no user name available".
    """
    try:
        body = call("sts", "GetCallerIdentity", {}, region=region, profile=profile)
        arn = str(body.get("Arn", "") or "")
        m = re.search(r":user/(.+)$", arn)
        return m.group(1) if m else ""
    except CliError:
        return ""


# ---------------------------------------------------------------------------
# Sensitive-data masking (output/display layer only)
# ---------------------------------------------------------------------------
# Masking is applied ONLY when rendering output (console logs, reports, JSON).
# Internal values used for API calls / comparisons / chain tracing are never
# altered. Set AK_LEAK_NO_MASK=1 to emit raw values (e.g. for automation).

# Dict keys whose string values are treated as sensitive identifiers.
_SENSITIVE_KEYS = {
    "ak", "account", "accountid", "uid", "userid",
    "accesskeyid", "accesskey", "useraccesskeyid",
}
_SENSITIVE_LIST_KEYS = {"aks_found_in_alert"}


def masking_enabled() -> bool:
    """Whether sensitive-data masking is active (default ON; opt out via env)."""
    return (os.environ.get("AK_LEAK_NO_MASK") or "").strip().lower() not in (
        "1", "true", "yes", "on",
    )


def mask_sensitive(value: Any, keep_head: int = 6, keep_tail: int = 4) -> Any:
    """Mask the middle of a sensitive identifier (AccessKey ID, UID, ...).

    Keeps the first `keep_head` and last `keep_tail` characters; the middle is
    replaced with a fixed-width mask. Short values are fully masked. Returns the
    value unchanged if masking is disabled or the value is empty/non-str.
    """
    if value in (None, "") or not masking_enabled():
        return value
    s = str(value)
    if len(s) <= keep_head + keep_tail:
        return "*" * len(s)
    return f"{s[:keep_head]}{'*' * 8}{s[-keep_tail:]}"


def mask_obj(obj: Any) -> Any:
    """Return a deep copy of `obj` with values under sensitive keys masked.

    Used to sanitize structured (JSON) output. Non-sensitive fields (source
    IPs, user names, timestamps) are preserved for forensic value.
    """
    if not masking_enabled():
        return obj
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in _SENSITIVE_KEYS and isinstance(v, str):
                out[k] = mask_sensitive(v)
            elif kl in _SENSITIVE_LIST_KEYS and isinstance(v, list):
                out[k] = [mask_sensitive(x) if isinstance(x, str) else mask_obj(x) for x in v]
            else:
                out[k] = mask_obj(v)
        return out
    if isinstance(obj, list):
        return [mask_obj(x) for x in obj]
    return obj


# AccessKey IDs start with the fixed "LTAI" prefix followed by alphanumerics.
_AK_RE = re.compile(r"LTAI[0-9A-Za-z]{6,}")


def mask_text(text: str, extra: Any = ()) -> str:
    """Safety-net masking over an already-rendered string (report / JSON dump).

    Masks every AccessKey ID (any `LTAI...` token, including attacker-created
    ones) plus any `extra` literal identifiers that are >= 8 chars (e.g. the
    account UID). Short literals like "N/A" are skipped so they are not mangled.
    This catches sensitive values sitting in arbitrary/unkeyed JSON fields that
    key-based `mask_obj` cannot reach.
    """
    if not text or not masking_enabled():
        return text
    out = _AK_RE.sub(lambda m: mask_sensitive(m.group(0)), text)
    for lit in extra or ():
        s = str(lit)
        if s and len(s) >= 8:
            out = out.replace(s, str(mask_sensitive(s)))
    return out


# ---------------------------------------------------------------------------
# Backend 1: aliyun CLI (subprocess)
# ---------------------------------------------------------------------------

def _call_cli(
    product: str,
    action: str,
    params: Optional[dict[str, Any]],
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    cmd = ["aliyun", product, action, "--region", region,
           "--user-agent", user_agent()]

    endpoint = _endpoint_for(product, region)
    if endpoint:
        cmd += ["--endpoint", endpoint]
    if profile:
        cmd += ["--profile", profile]

    for key, value in (params or {}).items():
        if value is None:
            continue
        cmd += [f"--{key}", str(value)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun {product} {action} timed out after {timeout}s")

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        code = _extract_error_code(stderr)
        raise CliError(
            f"aliyun {product} {action} failed: {stderr[:300]}",
            code=code,
            stderr=stderr,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text."""
    # CLI prints e.g. `ERROR: SDK.ServerError\nErrorCode: NoPermission\n...`
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("ErrorCode:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("ERROR:") and "." in line:
            return line.split(":", 1)[1].strip()
    return ""


# ---------------------------------------------------------------------------
# Backend 2: direct signed HTTPS (OpenAPI V3, ACS3-HMAC-SHA256)
# ---------------------------------------------------------------------------

def _call_http(
    product: str,
    action: str,
    params: Optional[dict[str, Any]],
    region: str,
    profile: Optional[str],
    timeout: int,
) -> dict[str, Any]:
    requests = _import_requests()  # lazy; may auto-install if opted in
    if requests is None:
        raise CliError(
            "HTTP backend: `requests` is required but not installed. "
            "Run `pip install requests`, or set AK_LEAK_AUTO_INSTALL=1 to "
            "install it automatically."
        )

    meta = PRODUCT_META.get(product, {})
    version = meta.get("version")
    if not version:
        raise CliError(f"HTTP backend: unknown API version for product '{product}'")
    endpoint = _endpoint_for(product, region)
    if not endpoint:
        raise CliError(f"HTTP backend: no endpoint configured for product '{product}'")

    ak, sk, token = _resolve_credentials(profile)
    query = {k: str(v) for k, v in (params or {}).items() if v is not None}
    url, headers = _sign_v3_rpc(action, version, query, ak, sk, token, endpoint)

    # User-Agent is NOT part of the V3 signature (only x-acs-* headers are
    # signed), so it is added after signing -- sent on the wire, signature intact.
    headers["User-Agent"] = user_agent()

    try:
        resp = requests.post(url, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise CliError(f"{product} {action} HTTP request failed: {e}")

    text = (resp.text or "").strip()
    try:
        body = json.loads(text) if text else {}
    except json.JSONDecodeError as e:
        raise CliError(f"{product} {action} returned non-JSON output: {e}")

    # OpenAPI error envelope: HTTP >= 400 and/or a {"Code","Message"} body.
    if resp.status_code >= 400 or (isinstance(body, dict) and body.get("Code") and body.get("Message")):
        code = body.get("Code", "") if isinstance(body, dict) else ""
        message = body.get("Message", text[:300]) if isinstance(body, dict) else text[:300]
        raise CliError(
            f"{product} {action} failed (HTTP {resp.status_code}): {message}",
            code=code,
            stderr=text[:300],
        )
    return body if isinstance(body, dict) else {}


def _resolve_credentials(profile: Optional[str]) -> tuple[str, str, Optional[str]]:
    """Resolve AK/SK[/token] for the HTTP backend.

    Resolution order:
      1. Environment variables
         ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
         (+ optional ALIBABA_CLOUD_SECURITY_TOKEN)
      2. ~/.aliyun/config.json  (the same profile store the aliyun CLI uses)
         Uses `profile` if given, else the file's `current` profile.
    """
    env_ak = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    env_sk = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    if env_ak and env_sk:
        return env_ak, env_sk, os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN") or None

    config_path = os.path.expanduser("~/.aliyun/config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise CliError(f"HTTP backend: cannot read ~/.aliyun/config.json: {e}")
        target = profile or config.get("current")
        for prof in config.get("profiles", []):
            if prof.get("name") == target:
                ak = prof.get("access_key_id")
                sk = prof.get("access_key_secret")
                if ak and sk:
                    return ak, sk, prof.get("sts_token") or None
                raise CliError(
                    f"HTTP backend: profile '{target}' has no AK/SK "
                    f"(mode={prof.get('mode')}); provide AK/SK env vars instead"
                )

    raise CliError(
        "HTTP backend: no credentials found. Set ALIBABA_CLOUD_ACCESS_KEY_ID / "
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET, or configure ~/.aliyun/config.json "
        "(e.g. via `aliyun configure`)."
    )


def _percent_encode(value: str) -> str:
    """RFC 3986 percent-encoding used by the V3 signature (unreserved chars only)."""
    return quote(str(value), safe="-_.~")


def _sign_v3_rpc(
    action: str,
    version: str,
    query: dict[str, str],
    ak: str,
    sk: str,
    token: Optional[str],
    host: str,
) -> tuple[str, dict[str, str]]:
    """Sign an RPC-style request with ACS3-HMAC-SHA256 (OpenAPI V3).

    All five products used by this skill (actiontrail/ram/ims/sas/cloudsso) are
    RPC-style, so a single signing path suffices. Business parameters go in the
    query string; the request body is empty.

    Returns (url, headers) ready for an HTTPS POST.
    """
    method = "POST"
    canonical_uri = "/"

    # 1. Canonical query string: sorted, each key & value percent-encoded.
    canonical_query = "&".join(
        f"{_percent_encode(k)}={_percent_encode(query[k])}"
        for k in sorted(query.keys())
    )

    # 2. Hashed (empty) payload.
    hashed_payload = hashlib.sha256(b"").hexdigest()

    # 3. Required x-acs-* headers.
    headers: dict[str, str] = {
        "host": host,
        "x-acs-action": action,
        "x-acs-version": version,
        "x-acs-date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "x-acs-signature-nonce": uuid.uuid4().hex,
        "x-acs-content-sha256": hashed_payload,
    }
    if token:
        headers["x-acs-security-token"] = token

    # 4. Canonical headers + signed header list (sorted, lowercase).
    signed_header_keys = sorted(headers.keys())
    canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in signed_header_keys)
    signed_headers = ";".join(signed_header_keys)

    # 5. Canonical request -> string to sign -> signature.
    canonical_request = "\n".join([
        method,
        canonical_uri,
        canonical_query,
        canonical_headers,
        signed_headers,
        hashed_payload,
    ])
    hashed_canonical_request = hashlib.sha256(
        canonical_request.encode("utf-8")
    ).hexdigest()
    string_to_sign = "ACS3-HMAC-SHA256\n" + hashed_canonical_request
    signature = hmac.new(
        sk.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    headers["Authorization"] = (
        f"ACS3-HMAC-SHA256 Credential={ak},"
        f"SignedHeaders={signed_headers},Signature={signature}"
    )

    url = f"https://{host}{canonical_uri}"
    if canonical_query:
        url += "?" + canonical_query
    return url, headers


# ---------------------------------------------------------------------------
# Pagination helpers (backend-agnostic: they only call `call()`)
# ---------------------------------------------------------------------------

def paginate_next_token(
    product: str,
    action: str,
    params: dict[str, Any],
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    items_key: str = "Events",
    token_req_key: str = "NextToken",
    token_resp_key: str = "NextToken",
    max_pages: int = 200,
) -> list[Any]:
    """Follow NextToken-based pagination (ActionTrail LookupEvents style).

    Returns the concatenated list under `items_key` across all pages.
    """
    all_items: list[Any] = []
    next_token: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        if next_token:
            page_params[token_req_key] = next_token
        body = call(product, action, page_params, region=region, profile=profile)
        items = body.get(items_key) or []
        all_items.extend(items)
        next_token = body.get(token_resp_key)
        pages += 1
        if not next_token:
            break
    return all_items


def paginate_marker(
    product: str,
    action: str,
    params: dict[str, Any],
    region: str = _DEFAULT_REGION,
    profile: Optional[str] = None,
    list_path: Optional[list[str]] = None,
    max_pages: int = 200,
) -> list[Any]:
    """Follow Marker/IsTruncated pagination (RAM ListUsers/ListRoles style).

    Args:
        list_path: Nested keys to reach the item list, e.g. ["Users", "User"].

    Returns the concatenated item list across all pages.
    """
    all_items: list[Any] = []
    marker: Optional[str] = None
    pages = 0
    while pages < max_pages:
        page_params = dict(params)
        if marker:
            page_params["Marker"] = marker
        body = call(product, action, page_params, region=region, profile=profile)

        node: Any = body
        for key in (list_path or []):
            node = (node or {}).get(key) if isinstance(node, dict) else None
        if isinstance(node, list):
            all_items.extend(node)

        pages += 1
        if body.get("IsTruncated") and body.get("Marker"):
            marker = body.get("Marker")
        else:
            break
    return all_items


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def get_time_window(days: int) -> tuple[str, str]:
    """Return (start, end) as ISO-8601 UTC strings (ActionTrail max 90 days)."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return start.strftime(fmt), end.strftime(fmt)
