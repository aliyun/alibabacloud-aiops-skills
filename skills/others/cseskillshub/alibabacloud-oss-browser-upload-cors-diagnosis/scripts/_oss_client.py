#!/usr/bin/env python3
"""
_oss_client.py -- Shared OSS control-plane client for browser-upload/CORS diagnosis
====================================================================================
SECURITY: This skill is strictly READ-ONLY. Credentials are resolved ONLY
from the standard Alibaba Cloud environment variables of the default
credential chain (ALIBABA_CLOUD_ACCESS_KEY_ID /
ALIBABA_CLOUD_ACCESS_KEY_SECRET / ALIBABA_CLOUD_SECURITY_TOKEN). This module
never hardcodes credentials, never prompts for them, and never prints their
values. Only the three metadata queries GetBucketInfo, GetBucketCors and
ListBuckets are ever issued against OSS; no mutating call exists anywhere in
this skill (PutBucketCors is ABSOLUTELY PROHIBITED -- the standard CORS
template is printed as text for the user to apply manually).

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the diagnosis scripts so that every OSS control-plane call goes through ONE
place carrying timeout, degradation and observability guarantees.

Channels (measured, finalized):
  * OSS control-plane metadata -> Python oss2 SDK (>= 2.19.0, < 3). The
    aliyun CLI carries no OSS control-plane metadata and ossutil is not
    assumed to be installed, so the SDK is the only viable channel.
  * Caller identity / UID derivation -> `aliyun sts get-caller-identity`
    (plugin mode, CLI default credential chain), argument-list subprocess.

Measured CORS behavior (oss2 2.19.1 against real buckets):
  * Bucket WITHOUT any CORS rule: bucket.get_bucket_cors() raises
    oss2.exceptions.NoSuchCors, HTTP 404, Code=NoSuchCORSConfiguration.
    This is a normal state ("CORS not configured"), NOT an operational
    error: get_bucket_cors() maps it to configured=False instead of
    raising, so the diagnosis entry reports the missing configuration and
    prints the standard template.
  * Non-existent bucket: NoSuchBucket (404) as usual.
  * Missing oss:GetBucketCors permission: AccessDenied (403), normalized to
    category=permission and degraded with [WARN] by the caller.

Observability:
  * User-Agent template: AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
  * session-id: 32-character hex string (uuid4().hex), generated once per
    run, attached to every OSS SDK request (User-Agent header) and every
    aliyun CLI call (--user-agent) of the same run.
  * skill-version: resolved at runtime from the SKILL_VERSION environment
    variable, else from the top-level 'version' of references/manifest.json;
    unresolvable version is a failure gate that stops the run before the
    first cloud call (never hardcoded, never guessed).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Optional

import oss2
from oss2.credentials import Credentials

_SKILL_NAME = "alibabacloud-oss-browser-upload-cors-diagnosis"
_SKILL_VERSION: Optional[str] = None  # resolved at runtime; see resolve_skill_version()
_STS_ENDPOINT = "sts.aliyuncs.com"
_DEFAULT_TIMEOUT = 30   # seconds, applied to every single OSS SDK call
_CLI_TIMEOUT = 60       # seconds, applied to every single aliyun CLI call
_SESSION_ID: Optional[str] = None


class OssClientError(RuntimeError):
    """Structured, normalized error for every OSS control-plane call.

    category values (stable contract consumed by the diagnosis entry):
      credentials      -- env credential chain not configured
      not_found        -- NoSuchBucket (bucket name does not exist)
      permission       -- 403 AccessDenied / bucket not owned by caller
      endpoint         -- wrong-region / must-use-specified-endpoint errors
      network          -- DNS failure ("no such host"), timeout, reset
      server           -- 5xx / service-side failures
      credentials        -- invalid/expired AK or STS token, signature mismatch
      invalid          -- invalid bucket name or request parameter
      unknown          -- anything else
    """

    def __init__(self, message: str, category: str = "unknown",
                 code: str = "", status: int = 0, hint: str = ""):
        super().__init__(message)
        self.category = category
        self.code = code
        self.status = status
        self.hint = hint

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "code": self.code,
            "status": self.status,
            "message": str(self),
            "hint": self.hint,
        }


class CliError(RuntimeError):
    """Raised when the aliyun CLI identity call fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------

def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_oss_client] session-id: {_SESSION_ID}", file=sys.stderr)
    return _SESSION_ID


def _manifest_path() -> str:
    """Absolute path to references/manifest.json (the skill version source)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "references", "manifest.json")


def resolve_skill_version() -> str:
    """Resolve the skill version carried in every User-Agent (rule UA-SKILL-VERSION).

    Resolution order: the SKILL_VERSION environment variable (non-empty), then
    the top-level 'version' string of references/manifest.json. The version is
    never invented or guessed. This doubles as the FAILURE GATE required before
    the first cloud call: user_agent() sits on the path of every Alibaba Cloud
    call (SDK header and CLI --user-agent), so an unresolvable version raises
    here and the run stops BEFORE any network call -- an unversioned call must
    never reach the cloud.
    """
    global _SKILL_VERSION
    if _SKILL_VERSION is not None:
        return _SKILL_VERSION
    env_version = (os.environ.get("SKILL_VERSION") or "").strip()
    if env_version:
        _SKILL_VERSION = env_version
        return _SKILL_VERSION
    path = _manifest_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise RuntimeError(
            "skill version unresolved: references/manifest.json is missing or "
            f"not valid JSON ({e}). Every Alibaba Cloud call must carry a "
            "versioned User-Agent, so this run stops before any cloud call. "
            "Restore references/manifest.json or export SKILL_VERSION."
        )
    version = data.get("version") if isinstance(data, dict) else None
    if not (isinstance(version, str) and version.strip()):
        raise RuntimeError(
            "skill version unresolved: references/manifest.json has no "
            "non-empty top-level 'version' string. Restore it or export "
            "SKILL_VERSION before any cloud call."
        )
    _SKILL_VERSION = version.strip()
    return _SKILL_VERSION


def user_agent() -> str:
    """User-Agent attached to every API call of this run.

    Template (rule UA-SKILL-VERSION):
      AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{version}
    """
    return (f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{session_id()} "
            f"skill-version/{resolve_skill_version()}")


# ---------------------------------------------------------------------------
# Credentials provider (env-var default chain only)
# ---------------------------------------------------------------------------

class EnvCredentialsProvider:
    """CredentialsProvider reading the ALIBABA_CLOUD_* environment variables.

    The oss2 built-in EnvironmentVariableCredentialsProvider reads OSS_*
    prefixed variables, which do not match the platform's default credential
    chain, so this provider reads:
      ALIBABA_CLOUD_ACCESS_KEY_ID
      ALIBABA_CLOUD_ACCESS_KEY_SECRET
      ALIBABA_CLOUD_SECURITY_TOKEN   (optional, present for STS sessions)
    Values are never printed or logged anywhere.
    """

    def get_credentials(self) -> Credentials:
        access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "").strip()
        access_key_secret = os.environ.get(
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET", "").strip()
        security_token = os.environ.get(
            "ALIBABA_CLOUD_SECURITY_TOKEN", "").strip()
        if not access_key_id or not access_key_secret:
            raise OssClientError(
                "no credentials found in the environment credential chain "
                "(ALIBABA_CLOUD_ACCESS_KEY_ID / "
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET are not set); configure the "
                "default credential chain first, never pass AK/SK manually",
                category="credentials", code="NoCredentials",
            )
        return Credentials(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=security_token,
        )


# ---------------------------------------------------------------------------
# Transient-failure retry (bounded, read-only, observable)
# ---------------------------------------------------------------------------

# Only service-side transient failures are retried: credential, permission,
# endpoint, not-found and invalid-input errors are deterministic, so retrying
# them would only add latency to an answer that is already final. The fixed
# delay list bounds the added latency to 4s on top of the per-call timeout.
_RETRY_DELAYS = (1.0, 3.0)
_RETRYABLE_CODES = frozenset({
    "InternalError", "ServiceUnavailable", "SlowDown", "RequestTimeout",
    "OperationTimeout", "TooManyRequests", "Throttling",
})


def _is_retryable(err: OssClientError) -> bool:
    """True when a normalized error looks transient (5xx or throttling)."""
    return err.category == "server" or err.code in _RETRYABLE_CODES


def _operation_label(method: str, bucket_name: str, endpoint: str) -> str:
    """Render an oss2 method name as the OSS operation name for [WARN] traces.

    SDK method names map 1:1 onto the CamelCase operation names
    (get_bucket_info -> GetBucketInfo), so a retry trace names the operation
    the customer would have to quote in a follow-up ticket.
    """
    op = "".join(part.capitalize() for part in str(method).split("_"))
    if bucket_name:
        return f"{op} bucket={bucket_name} endpoint={endpoint}"
    return f"{op} endpoint={endpoint}"


def _call_with_retry(operation: str, fn, *args, **kwargs):
    """Run one read-only OSS call, re-issuing it on transient 5xx/throttling.

    Classification goes through _normalize_oss_error, but the ORIGINAL
    exception is re-raised once the retries are used up, so every caller keeps
    producing its own operation-specific error message unchanged. Each retry
    leaves a [WARN] trace on stderr, keeping the degradation visible.
    """
    attempt = 0
    while True:
        try:
            return fn(*args, **kwargs)
        except OssClientError:
            raise
        except Exception as exc:
            err = _normalize_oss_error(exc, operation)
            if attempt >= len(_RETRY_DELAYS) or not _is_retryable(err):
                raise
            delay = _RETRY_DELAYS[attempt]
            attempt += 1
            print(f"[WARN] {operation}: transient {err.category} "
                  f"({err.code or 'HTTP ' + str(err.status)}) -- retry "
                  f"{attempt}/{len(_RETRY_DELAYS)} in {delay:.0f}s",
                  file=sys.stderr)
            time.sleep(delay)


class _RetryingHandle:
    """Read-only proxy around an oss2 handle, adding the bounded retry above.

    Every SDK call of this module goes through a handle built here, so
    wrapping the handle once keeps the transient-error policy in ONE place
    instead of duplicating a retry loop per operation. Non-callable attributes
    are forwarded untouched; callables are intercepted only to re-issue the
    very same read-only request.
    """

    def __init__(self, handle, bucket_name: str = "", endpoint: str = ""):
        self._handle = handle
        self._bucket_name = bucket_name
        self._endpoint = endpoint

    def __getattr__(self, name):
        handle = object.__getattribute__(self, "_handle")
        attr = getattr(handle, name)
        if name.startswith("_") or not callable(attr):
            return attr

        def _call(*args, **kwargs):
            label = _operation_label(
                name, object.__getattribute__(self, "_bucket_name"),
                object.__getattribute__(self, "_endpoint"))
            return _call_with_retry(label, attr, *args, **kwargs)

        return _call


def _build_bucket(bucket_name: str, endpoint: str,
                  timeout: int = _DEFAULT_TIMEOUT) -> "_RetryingHandle":
    """Build an oss2.Bucket handle carrying UA + per-call timeout.

    oss2.Bucket raises oss2.exceptions.ClientError for an illegal bucket
    name (uppercase / underscore / special character / wrong length); it
    is converted here to the unified OssClientError(category="invalid")
    so the entry script degrades with [WARN] + STATUS: DEGRADED instead
    of a bare Traceback.
    """
    auth = oss2.ProviderAuth(EnvCredentialsProvider())
    session = oss2.Session()
    # Inject the observability User-Agent into every SDK request of this run.
    session.session.headers["User-Agent"] = user_agent()
    try:
        return _RetryingHandle(
            oss2.Bucket(auth, endpoint, bucket_name, session=session,
                        connect_timeout=timeout),
            bucket_name, endpoint)
    except oss2.exceptions.ClientError as exc:
        raise OssClientError(
            f"the bucket name '{bucket_name}' is invalid: bucket names must "
            "be 3-63 characters of lowercase letters, digits and hyphens, "
            "starting and ending with a lowercase letter or digit",
            category="invalid", code="InvalidBucketName",
            hint="Fix the bucket name spelling; this is a client-side input "
                 "problem and no API call was issued.",
        ) from exc


def _action_hint_suffix(operation: str) -> str:
    """Name the RAM action the failing call most likely needs.

    OSS action names track the control-plane operation name, so pointing at
    the concrete action beats a generic "check your RAM policy" line -- the
    403 class is the single most common dead end for customer-run diagnosis.
    """
    m = re.match(r"([A-Z][A-Za-z0-9]+)", operation or "")
    if not m:
        return ""
    op = m.group(1)
    return (f" The failing call is {op}: the RAM action that must be granted "
            f"for this caller is oss:{op} (see references/ram-policies.md).")


_ENDPOINT_HINT_RE = re.compile(r"(oss-[a-z0-9-]+\.aliyuncs\.com)")


def _normalize_oss_error(exc: Exception, operation: str) -> OssClientError:
    """Map any oss2/requests/socket failure to a structured OssClientError."""
    msg = str(exc).strip() or exc.__class__.__name__
    low = msg.lower()
    # Carry the OSS RequestId into every normalized error so the customer can
    # cite it in a follow-up ticket instead of re-describing the failure.
    _rid = str(getattr(exc, "request_id", "") or "").strip()
    if _rid and _rid not in msg:
        msg = f"{msg} [request-id: {_rid}]"
        low = msg.lower()

    if isinstance(exc, oss2.exceptions.NoSuchBucket):
        return OssClientError(
            f"{operation}: the bucket does not exist ({msg})",
            category="not_found", code="NoSuchBucket", status=404,
            hint="Verify the bucket name spelling; bucket names are global "
                 "and case-sensitive lowercase.",
        )
    if isinstance(exc, oss2.exceptions.AccessDenied):
        category = "permission"
        hint = ("Check RAM permission (oss:GetBucketCors / oss:GetBucketInfo "
                "for this caller, see references/ram-policies.md), or confirm "
                "the bucket belongs to this account.")
        # G3-11: per the official doc, "does not belong to you" is a
        # client-side pre-check permission failure (the tool calls
        # ListObjects/GetBucketInfo before the real operation), NOT a bucket
        # ownership problem. Keep the error category as permission, but make
        # the hint lead with the missing bucket-level pre-check action.
        if "does not belong to you" in low:
            hint = ("Access denied (403) on a client-side pre-check: per the "
                    "official doc this message does NOT indicate a bucket-"
                    "ownership problem. The credential usually lacks "
                    "oss:ListObjects on the bucket-level resource "
                    "acs:oss:*:*:<bucket> (or oss:GetBucketInfo when the tool "
                    "pre-checks it) while holding only object-level actions. "
                    "Grant those bucket-level actions first; a wrong-account "
                    "credential or a wrong-region endpoint are secondary "
                    "hypotheses only.")
        elif "specified endpoint" in low or _ENDPOINT_HINT_RE.search(msg):
            category = "endpoint"
            hint = ("The request hit the wrong region's endpoint; use the "
                    "endpoint of the region where the bucket was created.")
        return OssClientError(
            f"{operation}: access denied ({msg})",
            category=category, code="AccessDenied", status=403,
            hint=hint + (_action_hint_suffix(operation)
                         if category == "permission" else ""),
        )
    if isinstance(exc, oss2.exceptions.OssError):
        status = getattr(exc, "status", 0) or 0
        code = getattr(exc, "code", "") or ""
        # Measured: oss2 wraps transport-layer failures (DNS "no such host",
        # connect timeout against an unreachable internal endpoint, reset)
        # into OssError/RequestError carrying status -2 and an empty code.
        if status <= 0 or "requesterror" in low:
            return OssClientError(
                f"{operation}: network/client failure: {msg}",
                category="network", code=code or "NetworkError",
                status=status,
                hint="Check DNS resolution of the endpoint host, local "
                     "network, and whether an internal endpoint is used "
                     "outside the Alibaba Cloud network of its region.",
            )
        hint = ""
        if status >= 500:
            category = "server"
        elif code in ("InvalidAccessKeyId", "SecurityTokenExpired",
                      "InvalidSecurityToken", "InvalidSecurityTokenVersion",
                      "SignatureDoesNotMatch"):
            # Measured: bad/expired STS credentials surface as HTTP 403 with
            # these codes, not as a RAM permission gap -- route to the
            # credential-chain guidance.
            category = "credentials"
            hint = ("The credential itself is invalid, expired or mismatched: "
                    "refresh the STS credential / re-export the "
                    "ALIBABA_CLOUD_* environment variables and retry. This is "
                    "NOT a missing RAM action, so granting more permissions "
                    "will not fix it.")
        elif code in ("InvalidBucketName", "InvalidArgument", "MalformedXML"):
            category = "invalid"
        else:
            category = "unknown"
        return OssClientError(
            f"{operation}: OSS error {code} (HTTP {status}): {msg}",
            category=category, code=code, status=status, hint=hint,
        )
    # Network-layer failures: DNS ("no such host" / "nodename nor servname"),
    # connect/read timeout, connection reset, TLS errors.
    if isinstance(exc, oss2.exceptions.ClientError) or not isinstance(
            exc, oss2.exceptions.OssError):
        return OssClientError(
            f"{operation}: network/client failure: {msg}",
            category="network", code=getattr(exc, "code", "") or "NetworkError",
            hint="Check DNS resolution of the endpoint host, local network, "
                 "and whether an internal endpoint is used outside the "
                 "Alibaba Cloud network.",
        )
    return OssClientError(f"{operation}: {msg}", category="unknown")


def get_bucket_info(bucket_name: str, endpoint: str,
                    timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Call OSS GetBucketInfo (read-only) and return normalized fields.

    Returns dict keys (measured against oss2 2.19.x):
      name, location (e.g. "oss-cn-hangzhou"), intranet_endpoint,
      extranet_endpoint, storage_class, acl, creation_date, owner_id.
    Raises OssClientError with a normalized category on any failure.
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    try:
        result = bucket.get_bucket_info()
    except OssClientError:
        raise
    except Exception as exc:  # oss2/requests/socket errors -> normalized
        raise _normalize_oss_error(
            exc, f"GetBucketInfo bucket={bucket_name} endpoint={endpoint}")
    info = result
    acl = getattr(info, "acl", None)
    owner = getattr(info, "owner", None)
    return {
        "name": getattr(info, "name", "") or bucket_name,
        "location": getattr(info, "location", "") or "",
        "intranet_endpoint": getattr(info, "intranet_endpoint", "") or "",
        "extranet_endpoint": getattr(info, "extranet_endpoint", "") or "",
        "storage_class": getattr(info, "storage_class", "") or "",
        "acl": getattr(acl, "grant", "") if acl is not None else "",
        "creation_date": getattr(info, "creation_date", "") or "",
        "owner_id": getattr(owner, "id", "") if owner is not None else "",
    }


def get_bucket_cors(bucket_name: str, endpoint: str,
                    timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Call OSS GetBucketCors (read-only) and return the normalized rules.

    Measured contract (oss2 2.19.1):
      * bucket with CORS rules -> returns {"configured": True, "rules": [...]}
      * bucket WITHOUT any CORS rule -> oss2 raises NoSuchCors (HTTP 404,
        Code=NoSuchCORSConfiguration). This is a NORMAL configuration state,
        not an operational error: it is mapped to
        {"configured": False, "rules": [], "code": "NoSuchCORSConfiguration"}
        so the diagnosis entry reports "CORS not configured" and outputs the
        standard template instead of surfacing an exception.
      * any other failure (NoSuchBucket / 403 / network / 5xx) -> raises
        OssClientError with the normalized category.
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    try:
        result = bucket.get_bucket_cors()
    except oss2.exceptions.ServerError as exc:
        # NoSuchCors is a ServerError subclass (404 NoSuchCORSConfiguration).
        code = getattr(exc, "code", "") or ""
        if code == "NoSuchCORSConfiguration" or type(exc).__name__ == "NoSuchCors":
            return {
                "configured": False,
                "rules": [],
                "code": "NoSuchCORSConfiguration",
                "note": "the bucket has no CORS rule configured; this is a "
                        "configuration state, not an API error",
            }
        raise _normalize_oss_error(
            exc, f"GetBucketCors bucket={bucket_name} endpoint={endpoint}")
    except OssClientError:
        raise
    except Exception as exc:  # oss2/requests/socket errors -> normalized
        raise _normalize_oss_error(
            exc, f"GetBucketCors bucket={bucket_name} endpoint={endpoint}")
    rules = []
    for rule in getattr(result, "rules", []) or []:
        rules.append({
            "allowed_origins": list(getattr(rule, "allowed_origins", []) or []),
            "allowed_methods": list(getattr(rule, "allowed_methods", []) or []),
            "allowed_headers": list(getattr(rule, "allowed_headers", []) or []),
            "expose_headers": list(getattr(rule, "expose_headers", []) or []),
            "max_age_seconds": getattr(rule, "max_age_seconds", None),
        })
    return {"configured": True, "rules": rules}


def list_buckets(prefix: str = "", timeout: int = _DEFAULT_TIMEOUT,
                 endpoint: str = "oss-cn-hangzhou.aliyuncs.com",
                 max_buckets: int = 200) -> list:
    """Call OSS ListBuckets (read-only) to locate buckets of this account.

    Used as the fallback path when GetBucketInfo cannot resolve the region
    (wrong endpoint, permission gap): the returned `location` of each bucket
    reveals the region the bucket was created in. Raises OssClientError.
    """
    try:
        auth = oss2.ProviderAuth(EnvCredentialsProvider())
        session = oss2.Session()
        session.session.headers["User-Agent"] = user_agent()
        service = _RetryingHandle(
            oss2.Service(auth, endpoint, session=session,
                         connect_timeout=timeout),
            "", endpoint)
        buckets = []
        marker = ""
        while len(buckets) < max_buckets:
            result = service.list_buckets(prefix=prefix, marker=marker,
                                          max_keys=100)
            for b in result.buckets:
                buckets.append({"name": b.name, "location": b.location,
                                "creation_date": b.creation_date})
            if not result.is_truncated:
                break
            marker = result.next_marker
        return buckets
    except OssClientError:
        raise
    except Exception as exc:
        raise _normalize_oss_error(exc, f"ListBuckets prefix={prefix or '*'}")


# ---------------------------------------------------------------------------
# Caller identity via aliyun CLI (argument-list subprocess, never shell=True)
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def get_caller_identity(timeout: int = _CLI_TIMEOUT) -> dict:
    """Run `aliyun sts get-caller-identity` and return the parsed response.

    Credentials come exclusively from the aliyun CLI default credential
    chain; the UA template and the per-run session-id are attached via
    --user-agent. Raises CliError on any failure.
    """
    if shutil.which("aliyun") is None:
        raise CliError(
            "aliyun CLI not found on PATH; install/configure it "
            "(`aliyun configure`) -- never pass AK/SK manually",
            code="CliMissing",
        )
    cmd = ["aliyun", "sts", "get-caller-identity",
           "--endpoint", _STS_ENDPOINT,
           "--user-agent", user_agent()]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun sts get-caller-identity timed out after "
                       f"{timeout}s", code="Timeout")
    stderr = _ANSI_ESCAPE_RE.sub("", result.stderr or "").strip()
    if result.returncode != 0:
        raise CliError(
            f"aliyun sts get-caller-identity failed: {stderr[:300]}",
            stderr=stderr,
        )
    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun sts get-caller-identity returned non-JSON "
                       f"output: {e}")


def resolve_uid() -> str:
    """Derive the caller UID (AccountId) via STS; return '' on failure.

    Callers degrade gracefully (log [WARN]) instead of aborting: UID is only
    a traceability label for this read-only skill.
    """
    try:
        identity = get_caller_identity()
    except CliError as e:
        print(f"[WARN] identity pre-check failed: {e}", file=sys.stderr)
        return ""
    return str(identity.get("AccountId") or "").strip()
