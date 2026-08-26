#!/usr/bin/env python3
"""
_cli.py -- Shared OpenAPI invocation helper for ActionTrail Diagnosis
=====================================================================
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

Both backends return the SAME raw API JSON, so all downstream code (the
business scripts, the pagination helpers) is backend-agnostic and unchanged.

Backend override: set env `ACTIONTRAIL_BACKEND=cli` or `ACTIONTRAIL_BACKEND=http`.

Public API:
    call(product, action, params=None, region=..., profile=None) -> dict
    call_with_retry(fn, ...) -> dict          # retries transient (429/5xx/network) failures
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
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from urllib.parse import quote

# Single source of truth for the skill version (kept in sync with SKILL.md /
# package metadata). Bump here only.
__version__ = "0.1.0"


class CliError(RuntimeError):
    """Raised when an OpenAPI invocation fails (either backend).

    Attributes:
        code:        Best-effort API error code (e.g. "NoPermission").
        stderr:      Raw stderr / response text (truncated) for diagnostics.
        http_status: HTTP status code when known or inferable (both backends;
                     the CLI backend infers 429/500 from the error code).
        network:     True when the failure is network-level (connect error,
                     DNS failure, timeout) rather than an API-level response.
    """

    def __init__(
        self,
        message: str,
        code: str = "",
        stderr: str = "",
        http_status: Optional[int] = None,
        network: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.stderr = stderr
        self.http_status = http_status
        self.network = network

    def is_retryable(self) -> bool:
        """Whether this failure is transient and worth retrying.

        Retryable: network-level errors, HTTP 429 (throttling), HTTP 5xx
        (server-side). NOT retryable: other 4xx (permission/parameter
        problems) -- retrying them cannot succeed.
        """
        if self.network:
            return True
        if self.http_status is not None:
            return self.http_status == 429 or self.http_status >= 500
        return False


# ---------------------------------------------------------------------------
# Per-product endpoint / version metadata
# ---------------------------------------------------------------------------
# `endpoint`      : region-less central endpoint (sts).
# `endpoint_tmpl` : region-templated endpoint.
# `version`       : OpenAPI version (required by the HTTP backend's V3 signature;
#                   ignored by the CLI backend, which knows versions internally).
PRODUCT_META: dict[str, dict[str, str]] = {
    "actiontrail": {"endpoint_tmpl": "actiontrail.{region}.aliyuncs.com", "version": "2020-07-06"},
    "sts": {"endpoint": "sts.aliyuncs.com", "version": "2015-04-01"},      # central, region-less
}

_DEFAULT_REGION = "cn-shanghai"

# Cached backend decision ("cli" | "http"). Resolved once per process.
_BACKEND: Optional[str] = None


# ---------------------------------------------------------------------------
# Observability: one session-id shared by EVERY API call in this process,
# emitted as a User-Agent on BOTH backends for server-side audit correlation.
# ---------------------------------------------------------------------------
_SKILL_NAME = "alibabacloud-actiontrail-diagnosis"
_SESSION_ID: Optional[str] = None


def session_id() -> str:
    """Return the 32-char lowercase-hex session-id for this diagnosis run.

    Generated once on first use and cached for the process lifetime, so every
    API call (CLI or HTTP) in one run shares the SAME id. Honors env
    `ACTIONTRAIL_SESSION_ID` (must be 32 hex chars) so a parent process and
    any child share one id; otherwise a fresh `uuid.uuid4().hex` is used.
    """
    global _SESSION_ID
    if _SESSION_ID is None:
        env = (os.environ.get("ACTIONTRAIL_SESSION_ID") or "").strip().lower()
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

    Honors the `ACTIONTRAIL_BACKEND` env var (`cli`/`http`) for explicit
    override. The result is cached for the lifetime of the process.
    """
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    forced = (os.environ.get("ACTIONTRAIL_BACKEND") or "").strip().lower()
    if forced in ("cli", "http"):
        _BACKEND = forced
    elif shutil.which("aliyun") is not None:
        _BACKEND = "cli"
    else:
        _BACKEND = "http"
    return _BACKEND


def _auto_install_enabled() -> bool:
    """Whether on-demand `pip install requests` is allowed (opt-in, default OFF)."""
    return (os.environ.get("ACTIONTRAIL_AUTO_INSTALL") or "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _import_requests():
    """Import `requests`, optionally auto-installing it first.

    Auto-install only runs when the HTTP fallback needs `requests`, the package
    is missing, AND env ACTIONTRAIL_AUTO_INSTALL is enabled. Returns the module,
    or None if unavailable (and not installable).
    """
    try:
        import requests
        return requests
    except ImportError:
        pass
    if not _auto_install_enabled():
        return None
    print(
        "[_cli] `requests` not found; ACTIONTRAIL_AUTO_INSTALL is set — installing "
        "`requests>=2.20.0` into the current interpreter ...",
        file=sys.stderr,
    )
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "requests>=2.20.0"],
            check=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print(
            "[_cli] auto-install of `requests` timed out after 120s. Install it "
            "manually instead: pip install 'requests>=2.20.0' (check network/proxy).",
            file=sys.stderr,
        )
        return None
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
                    auto-install is enabled (env ACTIONTRAIL_AUTO_INSTALL=1), it
                    is installed on demand.
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
            "     export ACTIONTRAIL_AUTO_INSTALL=1   (then re-run)\n"
            + "=" * 78,
            file=sys.stderr,
        )
        sys.exit(1)


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
        product:  Product code ("actiontrail" or "sts").
        action:   API action name (e.g. "LookupEvents", "GetCallerIdentity").
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


# Backoff schedule (seconds) used by call_with_retry; one slot per retry.
_RETRY_BACKOFFS = (0.5, 1.0, 2.0)


def call_with_retry(
    fn: Callable[[], dict[str, Any]],
    max_retries: int = 3,
    label: str = "api-call",
) -> dict[str, Any]:
    """Invoke `fn` (a zero-arg callable wrapping `call(...)`), retrying transient failures.

    Retry policy:
      - Retries ONLY transient failures: network-level errors, HTTP 429
        (throttling) and HTTP 5xx (server-side). Up to `max_retries` retries
        (default 3) with a fixed backoff schedule of [0.5, 1.0, 2.0] seconds.
      - 4xx permission/parameter errors are NEVER retried -- raised immediately.
      - A WARNING line is written to stderr before every backoff sleep.

    Args:
        fn:          Zero-argument callable returning the parsed API response.
                     Typically `lambda: call("actiontrail", "LookupEvents", {...})`.
        max_retries: Maximum number of retries after the initial attempt.
        label:       Human-readable label for log lines (e.g. product/action).

    Returns:
        The parsed JSON response from the first successful attempt.

    Raises:
        CliError: The last error once retries are exhausted, or immediately for
                  non-retryable (4xx) failures.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except CliError as e:
            if attempt >= max_retries or not e.is_retryable():
                raise
            delay = _RETRY_BACKOFFS[min(attempt, len(_RETRY_BACKOFFS) - 1)]
            print(
                f"[WARNING] {label}: transient failure "
                f"({'network error' if e.network else f'HTTP {e.http_status}'}: {e}); "
                f"retrying in {delay}s (attempt {attempt + 1}/{max_retries}) ...",
                file=sys.stderr,
            )
            time.sleep(delay)
            attempt += 1


# ---------------------------------------------------------------------------
# Sensitive-data masking (output/display layer only)
# ---------------------------------------------------------------------------
# Masking is applied ONLY when rendering output (console logs, reports, JSON).
# Internal values used for API calls / comparisons / chain tracing are never
# altered. Set ACTIONTRAIL_NO_MASK=1 to emit raw values (e.g. for automation).

# Dict keys whose values are treated as sensitive identifiers.
_SENSITIVE_KEYS = {
    "ak", "account", "accountid", "uid", "userid",
    "accesskeyid", "accesskey", "useraccesskeyid",
}


def masking_enabled() -> bool:
    """Whether sensitive-data masking is active (default ON; opt out via env)."""
    return (os.environ.get("ACTIONTRAIL_NO_MASK") or "").strip().lower() not in (
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
    IPs, user names, timestamps) are preserved for diagnostic value.
    """
    if not masking_enabled():
        return obj
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in _SENSITIVE_KEYS:
                if v is None or isinstance(v, bool):
                    out[k] = v
                elif isinstance(v, (str, int, float)):
                    # Scalars (string OR number form, e.g. a numeric accountId)
                    # are all masked; str() normalizes numbers first.
                    out[k] = mask_sensitive(str(v))
                else:
                    out[k] = mask_obj(v)  # dict/list recursion
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

    Masks every AccessKey ID (any `LTAI...` token) plus any `extra` literal
    identifiers that are >= 5 chars (e.g. the account UID, including short
    5-7 digit uids). Shorter literals like "N/A" are skipped so they are not
    mangled. Digit-only literals (UIDs) are matched with non-digit boundary
    guards, so an unrelated short number (a port, a year) or a longer digit
    run that merely CONTAINS the literal is never corrupted. Longer extras
    are masked before shorter ones to avoid partial-preplacement collisions.
    This catches sensitive values sitting in arbitrary/unkeyed JSON fields
    that key-based `mask_obj` cannot reach.
    """
    if not text or not masking_enabled():
        return text
    out = _AK_RE.sub(lambda m: mask_sensitive(m.group(0)), text)
    seen: set[str] = set()
    literals: list[str] = []
    for lit in extra or ():
        s = str(lit)
        if s and len(s) >= 5 and s not in seen:
            seen.add(s)
            literals.append(s)
    for s in sorted(literals, key=len, reverse=True):
        masked = str(mask_sensitive(s))
        if s.isdigit():
            out = re.sub(rf"(?<!\d){re.escape(s)}(?!\d)", lambda _m: masked, out)
        else:
            out = out.replace(s, masked)
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
    else:
        # Mirror the HTTP backend's env-first credential resolution: when
        # ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET are exported, inject them
        # explicitly so the CLI subprocess authenticates with the SAME
        # credential (including STS sessions) instead of silently falling
        # back to ~/.aliyun/config.json's current profile.
        env_ak = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
        env_sk = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        if env_ak and env_sk:
            env_token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN")
            if env_token:
                cmd += ["--mode", "StsToken",
                        "--access-key-id", env_ak,
                        "--access-key-secret", env_sk,
                        "--sts-token", env_token]
            else:
                cmd += ["--mode", "AK",
                        "--access-key-id", env_ak,
                        "--access-key-secret", env_sk]

    for key, value in (params or {}).items():
        if value is None:
            continue
        cmd += [f"--{key}", str(value)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # A CLI-side timeout is treated as a network-level transient failure
        # so call_with_retry can back off and retry it.
        raise CliError(
            f"aliyun {product} {action} timed out after {timeout}s",
            network=True,
        )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        code = _extract_error_code(stderr)
        http_status, network = _classify_cli_failure(stderr, code)
        raise CliError(
            f"aliyun {product} {action} failed: {stderr[:300]}",
            code=code,
            stderr=stderr,
            http_status=http_status,
            network=network,
        )

    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun {product} {action} returned non-JSON output: {e}")


def _extract_error_code(stderr: str) -> str:
    """Best-effort extraction of an API error code from CLI stderr text.

    Prefers an explicit `ErrorCode:` line (it may follow a generic
    `ERROR: SDK.ServerError` header); falls back to the payload of an
    `ERROR:` line. Only the code token before the first ':' is kept, e.g.
    `ERROR: Throttling.User: Request was denied ...` -> `Throttling.User`.
    """
    fallback = ""
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("ErrorCode:"):
            return line.split(":", 1)[1].strip().split(":", 1)[0].strip()
        if not fallback and line.startswith("ERROR:") and "." in line:
            payload = line.split(":", 1)[1].strip()
            # Skip generic headers like `SDK.ServerError` whose real code sits
            # on a later ErrorCode: line.
            if not payload.startswith("SDK."):
                fallback = payload.split(":", 1)[0].strip()
    return fallback


def _extract_http_status(stderr: str) -> Optional[int]:
    """Extract an explicit `HttpStatus: NNN` from CLI stderr when present."""
    m = re.search(r"HttpStatus:\s*(\d{3})", stderr or "")
    return int(m.group(1)) if m else None


# Substrings in CLI stderr that indicate a network-level (transient) failure
# rather than an API-level rejection. Deliberately precise: bare "timeout" /
# "timed out" are NOT listed because real API error envelopes embed a
# `RespHeaders: map[... X-Acs-Request-Timeout:...]` dump, and a loose match
# would misclassify 4xx rejections (e.g. NoPermission) as transient and
# retry them. Genuine transport timeouts surface as "i/o timeout" (Go net)
# or "context deadline exceeded"; subprocess-level timeouts raise
# CliError(network=True) directly and never reach these markers.
_NETWORK_ERROR_MARKERS = (
    "connection refused", "connection reset", "connection aborted",
    "broken pipe", "dial tcp", "no such host",
    "name or service not known", "temporary failure in name resolution",
    "network is unreachable", "no route to host",
    "i/o timeout", "context deadline exceeded",
    "eof occurred", "tls handshake",
)


def _classify_cli_failure(stderr: str, code: str) -> tuple[Optional[int], bool]:
    """Map a CLI-backend failure onto (http_status, network) retryability hints.

    The CLI exposes no real HTTP status, so classify by the extracted error
    code / stderr text to keep `is_retryable()` honest on the CLI backend:
      - Throttling*                  -> http_status=429 (retryable)
      - ServiceUnavailable*/InternalError* -> http_status=500 (retryable)
      - connection/DNS/timeout text  -> network=True    (retryable)
      - anything else (e.g. NoPermission, InvalidParameter) -> (None, False),
        i.e. NOT retryable, matching the 4xx semantics of the HTTP backend.
    """
    c = (code or "").strip()
    if c.startswith("Throttling"):
        return 429, False
    if c.startswith("ServiceUnavailable") or c.startswith("InternalError"):
        return 500, False
    low = (stderr or "").lower()
    # The `RespHeaders: map[...]` dump appended to API error envelopes carries
    # header names (e.g. X-Acs-Request-Timeout) that can false-positive the
    # network markers, so only the envelope before it is scanned.
    low = low.split("respheaders", 1)[0]
    if any(marker in low for marker in _NETWORK_ERROR_MARKERS):
        return None, True
    # Last resort: an explicit HTTP status in the stderr envelope.
    status = _extract_http_status(stderr or "")
    if status is not None and (status == 429 or status >= 500):
        return status, False
    return None, False


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
    requests = _import_requests()  # lazy; may auto install if opted in
    if requests is None:
        raise CliError(
            "HTTP backend: `requests` is required but not installed. "
            "Run `pip install requests`, or set ACTIONTRAIL_AUTO_INSTALL=1 to "
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
        # Connection/DNS/timeout failures are network-level and transient.
        raise CliError(
            f"{product} {action} HTTP request failed: {e}",
            network=True,
        )

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
            http_status=resp.status_code,
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

    Both products used by this skill (actiontrail/sts) are RPC-style, so a
    single signing path suffices. Business parameters go in the query string;
    the request body is empty.

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


